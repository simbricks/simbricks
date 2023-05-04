/*
 * SimBricks PCIe Adapter.
 *
 * Copyright (c) 2020-2023 Max Planck Institute for Software Systems
 * Copyright (c) 2020-2023 National University of Singapore
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */
#define VERBOSE_DEBUG_PRINTS 0
#define INTERRUPT_DISABLE_BIT 1 << 10
#define INTERRUPT_STATUS_BIT 1 << 3

#include <math.h>
#include <simics/device-api.h>
#include <simics/model-iface/transaction.h>

#include "simics/base/map-target.h"
#include "simics/devs/io-memory.h"
#include "simics/devs/pci.h"
#include "simics/host-info.h"
#include "simics/model-iface/cycle.h"
#include "simics/model-iface/register-view.h"
#include "simics/util/alloc.h"

// use simics-internal static assert for checks in proto header
#define SIMBRICKS_PROTO_MSG_SZCHECK(s) \
  STATIC_ASSERT(sizeof(s) == 64 && "SimBrick message size check failed")

#include <simbricks/pcie/if.h>

#include "simics/base-types.h"
#include "simics/base/attr-value.h"
#include "simics/base/conf-object.h"
#include "simics/base/event.h"
#include "simics/base/log.h"
#include "simics/base/memory.h"
#include "simics/base/time.h"
#include "simics/base/transaction.h"
#include "simics/base/types.h"
#include "simics/model-iface/components.h"
#include "simics/simulator-api.h"
#include "simics/simulator/processor.h"
#include "simics/util/help-macros.h"
#include "simics/util/vect.h"

typedef struct {
  /* Simics object */
  conf_object_t obj;
  conf_object_t *pci_bus;
  const pci_bus_interface_t *pci_bus_iface;
  map_target_t *memory_target;

  struct __attribute__((__packed__)) {
    /* this */
    uint16 vendor_id;
    uint16 device_id;
    uint16 command;
    uint16 status;
    uint8 revision_id;
    uint8 prog_if;
    uint8 subclass;
    uint8 class_code;
    uint8 cache_line_size;
    uint8 primary_latency_timer;
    uint8 header_type;
    uint8 bist;
    uint32 bars[6];
    uint32 cardbus_cis_ptr;
    uint16 subsystem_vendor_id;
    uint16 subsystem_id;
    uint32 expansion_rom_base_address;
    uint8 capabilities_ptr;
    uint8 reserved[7];
    uint8 interrupt_line;
    uint8 interrupt_pin;
    uint8 min_grant;
    uint8 max_latency;
    uint8 unused[192];
  } pci_config;

  /* config parameters */
  const char *socket_path; /* path to ux socket to connect to */
  uint64 pci_latency;
  uint64 sync_period;

  bool debug_prints;
  bool verbose;

  struct SimbricksPcieIf pcie_if;
  struct SimbricksProtoPcieDevIntro dev_intro;

  bool sync;
  cycles_t ts_base;
  conf_object_t *pico_second_clock;
} simbricks_pcie_t;

static event_class_t *sync_event;
static event_class_t *poll_event;

static inline uint64 ts_to_proto(simbricks_pcie_t *simbricks,
                                 cycles_t simics_ts) {
  return simics_ts - simbricks->ts_base;
}

static inline cycles_t ts_from_proto(simbricks_pcie_t *simbricks,
                                     uint64 proto_ts) {
  return (cycles_t)(proto_ts + simbricks->ts_base);
}

static inline cycles_t rel_to_current(simbricks_pcie_t *simbricks,
                                      cycles_t simics_ts) {
  cycles_t curr_ts = SIM_cycle_count(simbricks->pico_second_clock);
  return simics_ts - curr_ts;
}

static inline cycles_t rel_to_current_proto(simbricks_pcie_t *simbricks,
                                            uint64 proto_ts) {
  cycles_t curr_ts = SIM_cycle_count(simbricks->pico_second_clock);
  uint64 curr_proto_ts = ts_to_proto(simbricks, curr_ts);
  return (cycles_t)(proto_ts - curr_proto_ts);
}

static inline uint64_t ceil_power_of_2(uint64_t len) {
  long double log_len = ceill(log2l(len));
  ASSERT(log_len >= 4); /* makes masking easier */
  return (uint64_t)powl(2, log_len);
}

/* mask values in BAR registers to indicate size and set lower bit to indicate
 * correct type */
static void mask_bars(simbricks_pcie_t *simbricks) {
  ASSERT(sizeof(simbricks->dev_intro.bars) /
             sizeof(simbricks->dev_intro.bars[0]) ==
         sizeof(simbricks->pci_config.bars) /
             sizeof(simbricks->pci_config.bars[0]));

  simbricks->pci_bus_iface->remove_map(simbricks->pci_bus, &simbricks->obj,
                                       Sim_Addr_Space_IO, 0);
  simbricks->pci_bus_iface->remove_map(simbricks->pci_bus, &simbricks->obj,
                                       Sim_Addr_Space_Memory, 0);

  for (int i = 0; i < sizeof(simbricks->dev_intro.bars) /
                          sizeof(simbricks->dev_intro.bars[0]);
       ++i) {
    uint64_t len = simbricks->dev_intro.bars[i].len;
    /* len == 0 means BAR is unused */
    if (len == 0) {
      continue;
    }

    len = ceil_power_of_2(len);
    uint64 mask = ~(len - 1);

    ASSERT(!(simbricks->dev_intro.bars[0].flags &
             SIMBRICKS_PROTO_PCIE_BAR_DUMMY) &&
           "TODO");

    uint64 base_addr;
    if (simbricks->dev_intro.bars[i].flags & SIMBRICKS_PROTO_PCIE_BAR_64) {
      /* 64 bit memory space BAR */
      uint64 *bar_64 = (uint64 *)&simbricks->pci_config.bars[i];
      *bar_64 &= mask;

      /* BAR type bit */
      *bar_64 &= ~0b0001LL;

      /* indicate 64 bit */
      *bar_64 |= 0b0100LL;

      /* indicate prefetchable */
      if (simbricks->dev_intro.bars[i].flags & SIMBRICKS_PROTO_PCIE_BAR_PF) {
        *bar_64 |= 0b1000LL;
      }

      base_addr = *bar_64 & mask;
    } else {
      simbricks->pci_config.bars[i] &= mask;

      if (simbricks->dev_intro.bars[i].flags & SIMBRICKS_PROTO_PCIE_BAR_IO) {
        /* IO space BAR */
        simbricks->pci_config.bars[i] |= 0b01;
      } else if (simbricks->dev_intro.bars[i].flags &
                 SIMBRICKS_PROTO_PCIE_BAR_PF) {
        /* 32 bit memory BAR */
        simbricks->pci_config.bars[i] |= 0b1000;
      }

      base_addr = simbricks->pci_config.bars[i] & mask;
    }

    /* map BARs */
    if (base_addr > 0LL && base_addr < (~0LL & mask)) {
      SIM_LOG_INFO(3, &simbricks->obj, 1,
                   "mask_bars: mapping BAR bar=%u base_addr=0x%llx size=0x%lx",
                   i, base_addr, len);
      map_info_t info = {base_addr, base_addr, len, 0, 0, 0, Sim_Swap_None};
      if (!simbricks->pci_bus_iface->add_map(
              simbricks->pci_bus, &simbricks->obj,
              simbricks->dev_intro.bars[i].flags & SIMBRICKS_PROTO_PCIE_BAR_IO
                  ? Sim_Addr_Space_IO
                  : Sim_Addr_Space_Memory,
              NULL, info)) {
        SIM_LOG_ERROR(&simbricks->obj, 1,
                      "mask_bars: Could not add mapping for base_addr=0x%llx",
                      base_addr);
      }
    }

    if (simbricks->dev_intro.bars[i].flags & SIMBRICKS_PROTO_PCIE_BAR_64) {
      ++i;
    }
  }
}

/******************************************************************************/
/* Initialization */

static int simbricks_connect(simbricks_pcie_t *simbricks) {
  struct SimbricksProtoPcieDevIntro *d_i = &simbricks->dev_intro;
  struct SimbricksProtoPcieHostIntro host_intro;
  struct SimbricksBaseIfParams params;
  size_t len;
  uint64 first_sync_ts = 0, first_msg_ts = 0;
  volatile union SimbricksProtoPcieD2H *msg;
  struct SimbricksBaseIf *base_if = &simbricks->pcie_if.base;

  if (!simbricks->socket_path) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1, "socket path not set but required");
    return 0;
  }

  SimbricksPcieIfDefaultParams(&params);
  params.link_latency = simbricks->pci_latency * 1000;
  params.sync_interval = simbricks->sync_period * 1000;
  params.blocking_conn = true;
  params.sock_path = simbricks->socket_path;
  params.sync_mode = (simbricks->sync ? kSimbricksBaseIfSyncRequired
                                      : kSimbricksBaseIfSyncDisabled);

  if (SimbricksBaseIfInit(base_if, &params)) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1, "SimbricksBaseIfInit failed");
    return 0;
  }

  if (SimbricksBaseIfConnect(base_if)) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1, "SimbricksBaseIfConnect failed");
    return 0;
  }

  if (SimbricksBaseIfConnected(base_if)) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1,
                     "SimbricksBaseIfConnected indicates unconnected");
    return 0;
  }

  /* prepare & send host intro */
  memset(&host_intro, 0, sizeof(host_intro));
  if (SimbricksBaseIfIntroSend(base_if, &host_intro, sizeof(host_intro))) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1, "SimbricksBaseIfIntroSend failed");
    return 0;
  }

  /* receive device intro */
  len = sizeof(*d_i);
  if (SimbricksBaseIfIntroRecv(base_if, d_i, &len)) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1, "SimbricksBaseIfIntroRecv failed");
    return 0;
  }
  if (len != sizeof(*d_i)) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1,
                     "rx dev intro: length is not as expected");
    return 0;
  }

  /* copy pci config */
  simbricks->pci_config.vendor_id = d_i->pci_vendor_id;
  simbricks->pci_config.device_id = d_i->pci_device_id;
  simbricks->pci_config.revision_id = d_i->pci_revision;
  simbricks->pci_config.prog_if = d_i->pci_progif;
  simbricks->pci_config.subclass = d_i->pci_subclass;
  simbricks->pci_config.class_code = d_i->pci_class;
  mask_bars(simbricks);

  /* enable legacy interrupts */
  simbricks->pci_config.interrupt_pin = 1;

  if (simbricks->sync) {
    /* send a first sync */
    if (SimbricksPcieIfH2DOutSync(&simbricks->pcie_if, 0)) {
      SIM_LOG_CRITICAL(&simbricks->obj, 1, "sending initial sync failed");
      return 0;
    }
    first_sync_ts = SimbricksPcieIfH2DOutNextSync(&simbricks->pcie_if);

    SIM_LOG_INFO(4, &simbricks->obj, 1, "first_sync_ts: %llu", first_sync_ts);

    /* wait for first message so we know its timestamp */
    do {
      msg = SimbricksPcieIfD2HInPeek(&simbricks->pcie_if, 0);
      first_msg_ts = SimbricksPcieIfD2HInTimestamp(&simbricks->pcie_if);
    } while (!msg && !first_msg_ts);
  }

  /* schedule sync and poll events */
  if (simbricks->sync) {
    simbricks->ts_base = SIM_cycle_count(simbricks->pico_second_clock);
    SIM_LOG_INFO(4, &simbricks->obj, 1, "simbricks_connect: ts_base %lld",
                 simbricks->ts_base);
    SIM_event_post_cycle(simbricks->pico_second_clock, sync_event,
                         &simbricks->obj,
                         rel_to_current_proto(simbricks, first_sync_ts), NULL);
    SIM_event_post_cycle(simbricks->pico_second_clock, poll_event,
                         &simbricks->obj,
                         rel_to_current_proto(simbricks, first_sync_ts), NULL);
  } else {
    SIM_LOG_CRITICAL(&simbricks->obj, 1,
                     "Running unsynchronized not implemented");
  }

  return 1;
}

/******************************************************************************/
/* Message processing */

/* allocate host-to-device queue entry */
static inline volatile union SimbricksProtoPcieH2D *simbricks_comm_h2d_alloc(
    simbricks_pcie_t *simbricks, cycles_t cur_ts) {
  volatile union SimbricksProtoPcieH2D *msg;
  while (!(msg = SimbricksPcieIfH2DOutAlloc(&simbricks->pcie_if,
                                            ts_to_proto(simbricks, cur_ts)))) {
  }
  // performance optimization: reschedule sync timer since we are going to send
  // a message and an additional sync message is therefore not necessary for one
  // whole sync interal
  SIM_event_cancel_time(simbricks->pico_second_clock, sync_event,
                        &simbricks->obj, NULL, NULL);
  uint64 next_sync = SimbricksPcieIfH2DOutNextSync(&simbricks->pcie_if);
  cycles_t rel_next_sync = rel_to_current_proto(simbricks, next_sync);
  SIM_event_post_cycle(simbricks->pico_second_clock, sync_event,
                       &simbricks->obj, rel_next_sync, NULL);
  return msg;
}

/* process read completion from memory to host */
static void simbricks_comm_d2h_rcomp(simbricks_pcie_t *simbricks,
                                     uint64 cur_ts,  // NOLINT
                                     uint64 req_id, const void *data) {
  transaction_t *transaction = (transaction_t *)req_id;  // NOLINT
  unsigned size = SIM_transaction_size(transaction);

  bytes_t bytes = {data, size};
  SIM_set_transaction_bytes(transaction, bytes);
  SIM_LOG_INFO(
      3, &simbricks->obj, 1,
      "simbricks_comm_d2h_rcomp: completed transaction size=%u val=0x%llx",
      size, size <= 8 ? SIM_get_transaction_value_le(transaction) : -1);
  SIM_complete_transaction(transaction, Sim_PE_No_Exception);
}

#define ATOM_TYPE_req_id uint64_t
SIM_CUSTOM_ATOM(req_id); /* NOLINT */

exception_type_t rw_transaction_comp_callback(conf_object_t *obj,
                                              transaction_t *comp_transaction,
                                              exception_type_t exc);

static void simbricks_comm_d2h_rw(simbricks_pcie_t *simbricks,
                                  volatile union SimbricksProtoPcieD2H *msg,
                                  bool is_read) {
  volatile struct SimbricksProtoPcieD2HRead *read = &msg->read;
  volatile struct SimbricksProtoPcieD2HWrite *write = &msg->write;

  uint64_t offset = is_read ? read->offset : write->offset;
  unsigned size = is_read ? read->len : write->len;
  cycles_t cur_ts = SIM_cycle_count(simbricks->pico_second_clock);

  transaction_t *transaction = MM_ZALLOC(1, transaction_t);
  atom_t *atoms = MM_ZALLOC(8, atom_t);
  transaction->atoms = atoms;

  atoms[0] = ATOM_size(size);
  uint8 *data = MM_ZALLOC(size, uint8);
  atoms[1] = ATOM_data(data);

  if (is_read) {
    atoms[2] = ATOM_flags(0);
    atoms[3] = ATOM_req_id(read->req_id);
  } else {
    atoms[2] = ATOM_flags(Sim_Transaction_Write);
    memcpy(data, (uint8 *)write->data, write->len);
    atoms[3] = ATOM_req_id(write->req_id);
  }

  atoms[4] = ATOM_initiator(&simbricks->obj);
  atoms[5] = ATOM_completion(rw_transaction_comp_callback);
  atoms[6] = ATOM_owner(&simbricks->obj);
  atoms[7] = ATOM_LIST_END;

  SIM_LOG_INFO(3, &simbricks->obj, 1,
               "simbricks_comm_d2h_rw: issuing transaction to pci_bus "
               "cur_ts=%lli is_read=%u offset=0x%lx size=%u",
               cur_ts, is_read, offset, size);

  exception_type_t exc =
      SIM_issue_transaction(simbricks->memory_target, transaction, offset);
  SIM_monitor_transaction(transaction, exc);
}

/* send a read completion message to device */
exception_type_t rw_transaction_comp_callback(conf_object_t *obj,
                                              transaction_t *comp_transaction,
                                              exception_type_t exc) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  cycles_t cur_ts = SIM_cycle_count(simbricks->pico_second_clock);
  bool is_read = SIM_transaction_is_read(comp_transaction);
  unsigned size = SIM_transaction_size(comp_transaction);

  if (exc != Sim_PE_No_Exception) {
    SIM_LOG_CRITICAL(obj, 1,
                     "rw_transaction_comp_callback: transaction not successful "
                     "exc=%u is_read=%u",
                     exc, is_read);
  }

  volatile union SimbricksProtoPcieH2D *msg =
      simbricks_comm_h2d_alloc(simbricks, cur_ts);
  volatile struct SimbricksProtoPcieH2DReadcomp *readcomp = &msg->readcomp;
  volatile struct SimbricksProtoPcieH2DWritecomp *writecomp = &msg->writecomp;

  if (is_read) {
    readcomp->req_id = ATOM_get_transaction_req_id(comp_transaction);
    buffer_t bytes = {(uint8 *)readcomp->data, size};
    SIM_get_transaction_bytes(comp_transaction, bytes);
  } else {
    writecomp->req_id = ATOM_get_transaction_req_id(comp_transaction);
  }

  SIM_LOG_INFO(3, &simbricks->obj, 1,
               "simbricks_comm_h2d_rwcomp: sending message to device "
               "cur_ts=%lli is_read=%u size=%u val=0x%llx",
               cur_ts, is_read, size,
               size <= 8 ? SIM_get_transaction_value_le(comp_transaction) : -1);

  SimbricksPcieIfH2DOutSend(&simbricks->pcie_if, msg,
                            is_read ? SIMBRICKS_PROTO_PCIE_H2D_MSG_READCOMP
                                    : SIMBRICKS_PROTO_PCIE_H2D_MSG_WRITECOMP);

  MM_FREE(comp_transaction->atoms);
  MM_FREE(comp_transaction);

  return exc;
}

/* process incoming SimBricks protocol messages from memory simulator */
static void simbricks_comm_d2h_process(
    simbricks_pcie_t *simbricks, int64 cur_ts,
    volatile union SimbricksProtoPcieD2H *msg) {
  uint8_t type = SimbricksPcieIfD2HInType(&simbricks->pcie_if, msg);

#if VERBOSE_DEBUG_PRINTS
  SIM_LOG_INFO(4, &simbricks->obj, 1,
               "simbricks_comm_m2h_process: ts=%lld type=%u", cur_ts, type);
#endif

  switch (type) {
    case SIMBRICKS_PROTO_MSG_TYPE_SYNC: {
      /* nop */
      break;
    }
    case SIMBRICKS_PROTO_PCIE_D2H_MSG_READCOMP: {
      simbricks_comm_d2h_rcomp(simbricks, cur_ts, msg->readcomp.req_id,
                               (void *)msg->readcomp.data);
      break;
    }
    case SIMBRICKS_PROTO_PCIE_D2H_MSG_WRITECOMP: {
      SIM_LOG_ERROR(&simbricks->obj, 1,
                    "simbricks_comm_d2h_process: We are using posted writes, "
                    "so there shouldn't be a completion message here.");
      break;
    }
    case SIMBRICKS_PROTO_PCIE_D2H_MSG_READ:
    case SIMBRICKS_PROTO_PCIE_D2H_MSG_WRITE: {
      simbricks_comm_d2h_rw(simbricks, msg,
                            type == SIMBRICKS_PROTO_PCIE_D2H_MSG_READ);
      break;
    }
    case SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT: {
      switch (msg->interrupt.inttype) {
        case SIMBRICKS_PROTO_PCIE_INT_LEGACY_HI:
          if (simbricks->pci_config.status & INTERRUPT_STATUS_BIT) {
            SIM_LOG_INFO(
                1, &simbricks->obj, 1,
                "(WARNING) simbricks_comm_d2h_process: interrupt is already "
                "raised. Not raising again. cur_ts=%lli line=%u",
                cur_ts, simbricks->pci_config.interrupt_line);
            break;
          }

          simbricks->pci_config.status |= INTERRUPT_STATUS_BIT;

          if (simbricks->pci_config.command & INTERRUPT_DISABLE_BIT) {
            SIM_LOG_INFO(
                3, &simbricks->obj, 1,
                "simbricks_comm_d2h_process: delaying interrupt due to "
                "Interrupt Disable bit being set. cur_ts=%lli line=%u",
                cur_ts, simbricks->pci_config.interrupt_line);
            break;
          }
          SIM_LOG_INFO(3, &simbricks->obj, 1,
                       "simbricks_comm_d2h_process: raising interrupt "
                       "cur_ts=%lli line=%u",
                       cur_ts, simbricks->pci_config.interrupt_line);
          simbricks->pci_bus_iface->raise_interrupt(simbricks->pci_bus,
                                                    &simbricks->obj, 0);
          break;
        case SIMBRICKS_PROTO_PCIE_INT_LEGACY_LO:
          if (!(simbricks->pci_config.status & INTERRUPT_STATUS_BIT)) {
            SIM_LOG_INFO(
                1, &simbricks->obj, 1,
                "(WARNING) simbricks_comm_d2h_process: interrupt is already "
                "lowered. Not lowering again. cur_ts=%lli line=%u",
                cur_ts, simbricks->pci_config.interrupt_line);
            break;
          }

          simbricks->pci_config.status &= ~(INTERRUPT_STATUS_BIT);

          SIM_LOG_INFO(3, &simbricks->obj, 1,
                       "simbricks_comm_d2h_process: lowering interrupt "
                       "cur_ts=%lli line=%u",
                       cur_ts, simbricks->pci_config.interrupt_line);
          simbricks->pci_bus_iface->lower_interrupt(simbricks->pci_bus,
                                                    &simbricks->obj, 0);
          break;
        default:
          SIM_LOG_CRITICAL(
              &simbricks->obj, 1,
              "simbricks_comm_m2h_process: inttype %u not implemented",
              msg->interrupt.inttype);
          break;
      }
      break;
    }
    default: {
      SIM_LOG_CRITICAL(&simbricks->obj, 1,
                       "simbricks_comm_m2h_process: unhandled message type %u",
                       type);
    }
  }

  SimbricksPcieIfD2HInDone(&simbricks->pcie_if, msg);
}

/* sync event callback for sending synchronization messages to memory */
static void sync_event_callback(conf_object_t *obj, lang_void *data) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  cycles_t cur_ts = SIM_cycle_count(simbricks->pico_second_clock);
  uint64 proto_ts = ts_to_proto(simbricks, cur_ts);

  uint64 sync_ts = SimbricksPcieIfH2DOutNextSync(&simbricks->pcie_if);
  if (proto_ts > sync_ts + 1) {
    SIM_LOG_INFO(1, obj, 1,
                 "(WARNING) simbricks_timer_sync: expected_ts=%llu cur_ts=%llu",
                 sync_ts, proto_ts);
  }

#if VERBOSE_DEBUG_PRINTS
  SIM_LOG_INFO(4, obj, 1, "simbricks_timer_sync: ts=%lld pts=%llu npts=%llu",
               cur_ts, proto_ts, sync_ts);
#endif

  while (SimbricksPcieIfH2DOutSync(&simbricks->pcie_if, proto_ts)) {
  }

  uint64 next_sync_pts = SimbricksPcieIfH2DOutNextSync(&simbricks->pcie_if);
  cycles_t next_sync_ts = ts_from_proto(simbricks, next_sync_pts);
#if VERBOSE_DEBUG_PRINTS
  SIM_LOG_INFO(4, obj, 1, "simbricks_timer_sync: next pts=%llu pts=%lld",
               next_sync_pts, next_sync_ts);
#endif
  SIM_event_post_cycle(simbricks->pico_second_clock, sync_event,
                       &simbricks->obj, rel_to_current(simbricks, next_sync_ts),
                       NULL);
}

/* poll event callback for processing incoming messages from memory to host */
static void poll_event_callback(conf_object_t *obj, lang_void *data) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  int64 cur_ts = SIM_cycle_count(simbricks->pico_second_clock);
  uint64 proto_ts = ts_to_proto(simbricks, cur_ts);
  uint64 next_ts;

  volatile union SimbricksProtoPcieD2H *msg;
  volatile union SimbricksProtoPcieD2H *next_msg;

  uint64 poll_ts = SimbricksPcieIfD2HInTimestamp(&simbricks->pcie_if);
  if (proto_ts > poll_ts + 1 || proto_ts < poll_ts) {
    SIM_LOG_INFO(
        1, obj, 1,
        "(WARNING) simbricks_timer_poll: expected_pts=%llu cur_pts=%llu",
        poll_ts, proto_ts);
  }

#if VERBOSE_DEBUG_PRINTS
  SIM_LOG_INFO(4, obj, 1, "simbricks_timer_poll: ts=%lld sync_ts=%lld", cur_ts,
               SIM_event_find_next_cycle(simbricks->pico_second_clock,
                                         sync_event, obj, NULL, NULL));
#endif

  /* poll until we have a message (should not usually spin) */
  do {
    msg = SimbricksPcieIfD2HInPoll(&simbricks->pcie_if, proto_ts);
  } while (msg == NULL);

  simbricks_comm_d2h_process(simbricks, cur_ts, msg);

  /* process additional available messages */
  for (;;) {
    msg = SimbricksPcieIfD2HInPoll(&simbricks->pcie_if, proto_ts);
    if (msg == NULL) {
      break;
    }
    simbricks_comm_d2h_process(simbricks, cur_ts, msg);
  }

  /* Wait for next message so we know its timestamp and when to schedule the
   * timer. */
  do {
    next_msg = SimbricksPcieIfD2HInPeek(&simbricks->pcie_if, proto_ts);
    next_ts = SimbricksPcieIfD2HInTimestamp(&simbricks->pcie_if);
  } while (!next_msg && next_ts <= proto_ts);

  /* set timer for next message */
  SIM_event_post_cycle(simbricks->pico_second_clock, poll_event,
                       &simbricks->obj,
                       rel_to_current_proto(simbricks, next_ts), NULL);
}

static exception_type_t handle_config_transaction(conf_object_t *obj,
                                                  transaction_t *transaction,
                                                  uint64 addr) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  unsigned int size = SIM_transaction_size(transaction);
  bool is_read = SIM_transaction_is_read(transaction);
  cycles_t cur_ts = SIM_cycle_count(simbricks->pico_second_clock);
  bool interrupt_disable_before =
      simbricks->pci_config.command & INTERRUPT_DISABLE_BIT;

  if (addr + size > sizeof(simbricks->pci_config)) {
    SIM_LOG_CRITICAL(obj, 1,
                     "handle_config_transaction: access past pci_config bounds "
                     "cur_ts=%lli addr=%llu size=%u",
                     cur_ts, addr, size);
    return Sim_PE_IO_Error;
  }

  if (is_read) {
    bytes_t bytes = {((uint8 *)&simbricks->pci_config) + addr, size};
    SIM_set_transaction_bytes(transaction, bytes);
  } else if (SIM_transaction_is_write(transaction)) {
    buffer_t buffer = {((uint8 *)&simbricks->pci_config) + addr, size};
    SIM_get_transaction_bytes(transaction, buffer);
    if (0x10 <= addr && addr < 0x28) {
      mask_bars(simbricks);
    }
  } else {
    SIM_LOG_CRITICAL(
        obj, 1,
        "mem_handle_transaction: unsupported access to pci_config cur_ts=%lli",
        cur_ts);
    return Sim_PE_IO_Error;
  }

  SIM_LOG_INFO(3, obj, 1,
               "handle_config_transaction: cur_ts=%lli addr=0x%llx size=%u "
               "is_read=%u val=0x%llx",
               cur_ts, addr, size, is_read,
               size <= 8 ? SIM_get_transaction_value_le(transaction) : -1);

  if (interrupt_disable_before &&
      (simbricks->pci_config.command & INTERRUPT_DISABLE_BIT) == 0 &&
      (simbricks->pci_config.command & INTERRUPT_STATUS_BIT)) {
    SIM_LOG_INFO(
        3, &simbricks->obj, 1,
        "simbricks_comm_d2h_process: Interrupt Disable bit changed to 0, "
        "raising delayed interrupt. cur_ts=%lli ",
        cur_ts);
    simbricks->pci_bus_iface->raise_interrupt(simbricks->pci_bus,
                                              &simbricks->obj, 0);
  }

  return Sim_PE_No_Exception;
}

static exception_type_t handle_bar_transaction(conf_object_t *obj,
                                               transaction_t *transaction,
                                               uint64 addr) {
  volatile union SimbricksProtoPcieH2D *msg;
  volatile struct SimbricksProtoPcieH2DRead *read;
  volatile struct SimbricksProtoPcieH2DWrite *write;
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  unsigned size = SIM_transaction_size(transaction);
  cycles_t cur_ts = SIM_cycle_count(simbricks->pico_second_clock);
  bool is_write = SIM_transaction_is_write(transaction);

  /* determine BAR number being accessed */
  for (unsigned bar = 0; bar < sizeof(simbricks->dev_intro.bars) /
                                   sizeof(simbricks->dev_intro.bars[0]);
       (simbricks->dev_intro.bars[bar].flags & SIMBRICKS_PROTO_PCIE_BAR_64)
           ? bar += 2
           : ++bar) {
    /* determine base address */
    uint64_t len = ceil_power_of_2(simbricks->dev_intro.bars[0].len);
    uint64 mask = ~(len - 1);
    uint64 base_addr = simbricks->pci_config.bars[bar];
    if (simbricks->dev_intro.bars[bar].flags & SIMBRICKS_PROTO_PCIE_BAR_64) {
      uint64 *base_addr_ptr = (uint64 *)&simbricks->pci_config.bars[bar];
      base_addr = *base_addr_ptr;
    }
    base_addr &= mask;

    /* check whether access belongs to current BAR */
    if (!(base_addr <= addr && addr < base_addr + len)) {
      continue;
    }

    /* handle write transaction */
    if (is_write) {
      msg = simbricks_comm_h2d_alloc(simbricks, cur_ts);
      write = &msg->write;
      write->bar = bar;
      write->offset = addr - base_addr;
      write->len = size;

      unsigned int max_size =
          SimbricksPcieIfH2DOutMsgLen(&simbricks->pcie_if) - sizeof(*write);
      if (size > max_size) {
        SIM_LOG_CRITICAL(&simbricks->obj, 1,
                         "Message size in out queue of %u bytes does not "
                         "suffice. Requiring %u bytes.",
                         max_size, size);
        return Sim_PE_IO_Error;
      }

      buffer_t data = {(uint8 *)write->data, size};
      SIM_get_transaction_bytes(transaction, data);

      SIM_LOG_INFO(
          3, &simbricks->obj, 1,
          "handle_bar_transaction: Sending posted write to device. ts=%llu "
          "bar=%u offset=0x%lx len=%u val=0x%llx",
          cur_ts, write->bar, write->offset, write->len,
          size <= 8 ? SIM_get_transaction_value_le(transaction) : -1);

      SimbricksPcieIfH2DOutSend(&simbricks->pcie_if, msg,
                                SIMBRICKS_PROTO_PCIE_H2D_MSG_WRITE_POSTED);

      /* we don't wait for the completion of writes so we are done here */
      return Sim_PE_No_Exception;
    }

    if (!SIM_transaction_is_read(transaction)) {
      SIM_LOG_CRITICAL(
          obj, 1,
          "handle_bar_transaction: access is neither write nor read. ts=%llu "
          "addr=0x%llx size=%u",
          cur_ts, addr, size);
      return Sim_PE_IO_Error;
    }

    /* handle read transaction */
    msg = simbricks_comm_h2d_alloc(simbricks, cur_ts);
    read = &msg->read;
    read->bar = bar;
    read->offset = addr - base_addr;
    read->len = size;
    read->req_id = (uint64_t)SIM_defer_transaction(obj, transaction);

    if (!read->req_id) {
      SIM_LOG_ERROR(obj, 1,
                    "handle_bar_transaction: Cannot defer transaction. ts=%llu "
                    "bar=%u offset=0x%lx len=%u",
                    cur_ts, read->bar, read->offset, read->len);
      return Sim_PE_Async_Required;
    }

    SIM_LOG_INFO(3, &simbricks->obj, 1,
                 "handle_bar_transaction: Sending read to device. ts=%llu "
                 "bar=%u offset=0x%lx len=%u",
                 cur_ts, read->bar, read->offset, read->len);

    SimbricksPcieIfH2DOutSend(&simbricks->pcie_if, msg,
                              SIMBRICKS_PROTO_PCIE_H2D_MSG_READ);

    return Sim_PE_Deferred;
  }

  /* no BAR matched */
  SIM_LOG_ERROR(
      obj, 1,
      "handle_bar_transaction: no BAR matched access ts=%lli addr=0x%llx "
      "size=0x%x is_write=%u",
      cur_ts, addr, size, SIM_transaction_is_write(transaction));
  return Sim_PE_IO_Error;
}

static exception_type_t handle_transaction(conf_object_t *obj,
                                           transaction_t *transaction,
                                           uint64 addr) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  if (addr < sizeof(simbricks->pci_config)) {
    return handle_config_transaction(obj, transaction, addr);
  }
  return handle_bar_transaction(obj, transaction, addr);
}

static void pci_bus_reset(conf_object_t *obj) {
  SIM_LOG_INFO(3, obj, 1, "pci_bus_reset: unimplemented. obj=%s",
               SIM_object_name(obj));
}

static void pci_system_error(conf_object_t *obj) {
  SIM_LOG_INFO(3, obj, 1, "pci_system_error: unimplemented. obj=%s",
               SIM_object_name(obj));
}

static void pci_interrupt_raised(conf_object_t *obj, int pin) {
  SIM_LOG_ERROR(obj, 1, "pci_interrupt_raised: unimplemented. pin=0x%i", pin);
}

static void pci_interrupt_lowered(conf_object_t *obj, int pin) {
  SIM_LOG_ERROR(obj, 1, "interrupt_lowered: unimplemented. pin=0x%i", pin);
}

/******************************************************************************/
/* Device Attribute Getters and Setters */

static attr_value_t get_pci_bus_attr(conf_object_t *obj) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  return SIM_make_attr_object(simbricks->pci_bus);
}
static set_error_t set_pci_bus_attr(conf_object_t *obj,
                                    attr_value_t *attr_val) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  if (!SIM_attr_is_object(*attr_val)) {
    return Sim_Set_Illegal_Value;
  }
  simbricks->pci_bus = SIM_attr_object(*attr_val);
  return Sim_Set_Ok;
}

static attr_value_t get_socket_attr(conf_object_t *obj) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  return SIM_make_attr_string(simbricks->socket_path);
}
static set_error_t set_socket_attr(conf_object_t *obj, attr_value_t *attr_val) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  if (!SIM_attr_is_string(*attr_val)) {
    return Sim_Set_Illegal_Value;
  }
  simbricks->socket_path = SIM_attr_string(*attr_val);
  return Sim_Set_Ok;
}

static attr_value_t get_pci_latency_attr(conf_object_t *obj) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  return SIM_make_attr_uint64(simbricks->pci_latency);
}
static set_error_t set_pci_latency_attr(conf_object_t *obj,
                                        attr_value_t *attr_val) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  if (!SIM_attr_is_uint64(*attr_val)) {
    return Sim_Set_Illegal_Value;
  }
  simbricks->pci_latency = SIM_attr_integer(*attr_val);
  return Sim_Set_Ok;
}

static attr_value_t get_sync_period_attr(conf_object_t *obj) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  return SIM_make_attr_uint64(simbricks->sync_period);
}
static set_error_t set_sync_period_attr(conf_object_t *obj,
                                        attr_value_t *attr_val) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  if (!SIM_attr_is_uint64(*attr_val)) {
    return Sim_Set_Illegal_Value;
  }
  simbricks->sync_period = SIM_attr_integer(*attr_val);
  return Sim_Set_Ok;
}

/******************************************************************************/
/* Simics Initialization */

/* Allocate memory for the object. */
static conf_object_t *alloc_object(conf_class_t *cls) {
  simbricks_pcie_t *empty = MM_ZALLOC(1, simbricks_pcie_t);
  return &empty->obj;
}

/* Initialize the object before any attributes are set. */
static void *init_object(conf_object_t *obj) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;
  simbricks->sync = true;
  return obj;
}

/* Initialization once all objects have been finalized, if needed. */
static void objects_finalized(conf_object_t *obj) {
  simbricks_pcie_t *simbricks = (simbricks_pcie_t *)obj;

  /* obtain picosecond clock */
  conf_object_t *clock = SIM_object_clock(obj);
  if (!clock) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1,
                     "objects_finalized: cannot obtain object clock");
    return;
  }
  simbricks->pico_second_clock = SIM_picosecond_clock(clock);
  if (!simbricks->pico_second_clock) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1,
                     "objects_finalized: cannot obtain picosecond clock");
  }

  ASSERT(simbricks->pci_bus != NULL);
  simbricks->pci_bus_iface = SIM_get_interface(simbricks->pci_bus, "pci_bus");
  ASSERT(simbricks->pci_bus_iface != NULL);

  simbricks->memory_target = SIM_new_map_target(
      simbricks->pci_bus_iface->memory_space(simbricks->pci_bus), NULL, NULL);

  if (!simbricks_connect(simbricks)) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1, "simbricks_connect failed");
  }
}

/* Free memory allocated for the object. */
static void dealloc_object(conf_object_t *obj) {
  simbricks_pcie_t *empty = (simbricks_pcie_t *)obj;
  SIM_free_map_target(empty->memory_target);
  MM_FREE(empty);
}

/* Called once when the device module is loaded into Simics. */
void init_local(void) {
  /* Define and register the device class. */
  const class_info_t class_info = {.alloc = alloc_object,
                                   .init = init_object,
                                   .objects_finalized = objects_finalized,
                                   .dealloc = dealloc_object,
                                   .description = "SimBricks PCIe Adapter",
                                   .short_desc = "SimBricks PCIe Adapter",
                                   .kind = Sim_Class_Kind_Vanilla};
  conf_class_t *pcie_cls = SIM_create_class("simbricks_pcie", &class_info);

  /* register interfaces */
  static const transaction_interface_t kTransactionIface = {
      .issue = handle_transaction};
  SIM_REGISTER_INTERFACE(pcie_cls, transaction, &kTransactionIface);
  static const pci_device_interface_t kPciDevIface = {
      pci_bus_reset,        NULL, NULL, pci_system_error, pci_interrupt_raised,
      pci_interrupt_lowered};
  SIM_REGISTER_INTERFACE(pcie_cls, pci_device, &kPciDevIface);

  /* register events we later want to insert into event queues */
  sync_event = SIM_register_event("simbricks-sync", pcie_cls, 0,
                                  sync_event_callback, NULL, NULL, NULL, NULL);
  poll_event = SIM_register_event("simbricks-poll", pcie_cls, 0,
                                  poll_event_callback, NULL, NULL, NULL, NULL);

  // add device attributes
  SIM_register_attribute(pcie_cls, "pci_bus", get_pci_bus_attr,
                         set_pci_bus_attr, Sim_Attr_Required, "o",
                         "PCI bus device is connected to.");
  SIM_register_attribute(pcie_cls, "socket", get_socket_attr, set_socket_attr,
                         Sim_Attr_Required, "s",
                         "Socket Path for SimBricks messages");
  SIM_register_attribute(pcie_cls, "pci_latency", get_pci_latency_attr,
                         set_pci_latency_attr, Sim_Attr_Required, "i",
                         "PCI Latency in ns from host to device");
  SIM_register_attribute(
      pcie_cls, "sync_period", get_sync_period_attr, set_sync_period_attr,
      Sim_Attr_Optional, "i",
      "Period for sending SimBricks synchronization messages in nanoseconds.");
}

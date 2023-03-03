/*
 * SimBricks Memory Adapter Device
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

#include <simics/device-api.h>
#include <simics/model-iface/transaction.h>

#include "simics/model-iface/cycle.h"
#include "simics/simulator/conf-object.h"
#include "simics/util/alloc.h"

// use simics-internal static assert for checks in proto header
#define SIMBRICKS_PROTO_MSG_SZCHECK(s) \
  STATIC_ASSERT(sizeof(s) == 64 && "SimBrick message size check failed")

#include <simbricks/mem/if.h>

#include "simics/base-types.h"
#include "simics/base/attr-value.h"
#include "simics/base/conf-object.h"
#include "simics/base/event.h"
#include "simics/base/log.h"
#include "simics/base/memory.h"
#include "simics/base/time.h"
#include "simics/base/transaction.h"
#include "simics/base/types.h"
#include "simics/simulator-api.h"
#include "simics/simulator/processor.h"
#include "simics/util/help-macros.h"
#include "simics/util/vect.h"

typedef struct mem_request mem_request_t;

typedef struct {
  uint64 addr;
  mem_request_t *waiters;
  conf_object_t *owner; /* allowed to do updates even if there are waiters */
  uint64 last_access_ts;
  bool valid;
  uint8 data[];
} cache_entry_t;

struct mem_request {
  transaction_t *transaction;
  uint64 addr;
  cache_entry_t *cache_entry;
  mem_request_t *next_waiter;
};

typedef struct {
  /* Simics object */
  conf_object_t obj;

  /* config parameters */
  const char *socket_path; /* path to ux socket to connect to */
  uint64 mem_latency;
  uint64 sync_period;
  uint64 cache_size;
  uint64 cache_line_size;

  bool debug_prints;
  bool verbose;

  struct SimbricksMemIf memif;
  struct SimbricksProtoMemMemIntro dev_intro;

  bool sync;
  cycles_t ts_base;
  conf_object_t *pico_second_clock;
  cache_entry_t **cache;
} simbricks_mem_t;

static event_class_t *sync_event;
static event_class_t *poll_event;
static event_class_t *comp_waiter_event;

static inline uint64 ts_to_proto(simbricks_mem_t *simbricks,
                                 cycles_t simics_ts) {
  return simics_ts - simbricks->ts_base;
}

static inline cycles_t ts_from_proto(simbricks_mem_t *simbricks,
                                     uint64 proto_ts) {
  return (cycles_t)(proto_ts + simbricks->ts_base);
}

static inline cycles_t rel_to_current(simbricks_mem_t *simbricks,
                                      cycles_t simics_ts) {
  cycles_t curr_ts = SIM_cycle_count(simbricks->pico_second_clock);
  return simics_ts - curr_ts;
}

static inline cycles_t rel_to_current_proto(simbricks_mem_t *simbricks,
                                            uint64 proto_ts) {
  cycles_t curr_ts = SIM_cycle_count(simbricks->pico_second_clock);
  uint64 curr_proto_ts = ts_to_proto(simbricks, curr_ts);
  return (cycles_t)(proto_ts - curr_proto_ts);
}

/******************************************************************************/
/* Initialization */

/* setup connection to memory */
static int simbricks_connect(simbricks_mem_t *simbricks) {
  struct SimbricksProtoMemMemIntro *d_i = &simbricks->dev_intro;
  struct SimbricksProtoMemHostIntro host_intro;
  struct SimbricksBaseIfParams params;
  size_t len;
  uint64 first_sync_ts = 0, first_msg_ts = 0;
  volatile union SimbricksProtoMemM2H *msg;
  struct SimbricksBaseIf *base_if = &simbricks->memif.base;

  if (!simbricks->socket_path) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1, "socket path not set but required");
    return 0;
  }

  SimbricksMemIfDefaultParams(&params);
  params.link_latency = simbricks->mem_latency * 1000;
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

  if (simbricks->sync) {
    /* send a first sync */
    if (SimbricksMemIfH2MOutSync(&simbricks->memif, 0)) {
      SIM_LOG_CRITICAL(&simbricks->obj, 1, "sending initial sync failed");
      return 0;
    }
    first_sync_ts = SimbricksMemIfH2MOutNextSync(&simbricks->memif);

    SIM_LOG_INFO(3, &simbricks->obj, 1, "first_sync_ts: %llu", first_sync_ts);

    /* wait for first message so we know its timestamp */
    do {
      msg = SimbricksMemIfM2HInPeek(&simbricks->memif, 0);
      first_msg_ts = SimbricksMemIfM2HInTimestamp(&simbricks->memif);
    } while (!msg && !first_msg_ts);
  }

  /* initialize cache */
  simbricks->cache = MM_ZALLOC(simbricks->cache_size, cache_entry_t *);
  for (uint64 i = 0; i < simbricks->cache_size; i++) {
    simbricks->cache[i] = MM_ZALLOC_SZ(
        sizeof(cache_entry_t) + simbricks->cache_line_size, cache_entry_t);
  }

  /* schedule sync and poll events */
  if (simbricks->sync) {
    simbricks->ts_base = SIM_cycle_count(simbricks->pico_second_clock);
    SIM_LOG_INFO(3, &simbricks->obj, 1, "simbricks_connect: ts_base %lld",
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
/* Cache management */

static cache_entry_t *cache_get_entry(simbricks_mem_t *simbricks, uint64 addr,
                                      bool alloc, uint64 cur_ts, bool logging) {
  uint64 cl_num = addr / simbricks->cache_line_size;
  uint64_t key = cl_num;
  cache_entry_t *cache_entry, *min_cache_entry = NULL;

  addr &= ~((uint64_t)simbricks->cache_line_size - 1);

  // very simple hash mixer
  key ^= key >> 33;
  key *= 0xff51afd7ed558ccd;
  key ^= key >> 33;
  key *= 0xc4ceb9fe1a85ec53;
  key ^= key >> 33;

  for (unsigned i = 0; i < 8; i++) {
    cache_entry = simbricks->cache[(key + i) % simbricks->cache_size];
    if (cache_entry->addr == addr) {
      if (logging) {
        SIM_LOG_INFO(3, &simbricks->obj, 1,
                     "cache_get_entry: addr=0x%llx found. ts=%llu entry=%p",
                     addr, cur_ts, cache_entry);
      }

      cache_entry->last_access_ts = cur_ts;
      return cache_entry;
    }

    if (cache_entry->waiters == NULL && cache_entry->owner == NULL) {
      if (min_cache_entry == NULL ||
          cache_entry->last_access_ts < min_cache_entry->last_access_ts)
        min_cache_entry = cache_entry;
    }
  }

  if (!alloc) {
    if (logging) {
      SIM_LOG_INFO(3, &simbricks->obj, 1,
                   "cache_get_entry: addr=0x%llx not found. ts=%llu", addr,
                   cur_ts);
    }
    return NULL;
  }

  if (!min_cache_entry) {
    SIM_LOG_CRITICAL(
        &simbricks->obj, 1,
        "cache_get_entry: found no cache slot to allocate. addr=0x%llx ts=%llu",
        addr, cur_ts);
    return NULL;
  }

  if (logging) {
    SIM_LOG_INFO(3, &simbricks->obj, 1,
                 "cache_get_entry: allocated a slot. addr=0x%llx ts=%llu", addr,
                 cur_ts);
  }
  min_cache_entry->last_access_ts = cur_ts;
  min_cache_entry->valid = false;
  min_cache_entry->addr = addr;
  return min_cache_entry;
}

/* set the result of a read transaction transaction from a cache_entry */
static inline void cache_read_transaction_bytes(simbricks_mem_t *simbricks,
                                                cache_entry_t *cache_entry,
                                                transaction_t *transaction,
                                                uint64 addr, uint64 cur_ts) {
  cache_entry->last_access_ts = cur_ts;
  uint64 cache_line_off = addr % simbricks->cache_line_size;
  unsigned int size = SIM_transaction_size(transaction);
  bytes_t buffer = {cache_entry->data + cache_line_off, size};
  SIM_set_transaction_bytes(transaction, buffer);

  SIM_LOG_INFO(3, &simbricks->obj, 1,
               "cache_read_transaction_bytes: ts=%llu addr=0x%llx "
               "size=%u value=0x%llx initiator=%s",
               cur_ts, addr, size,
               size <= 8 ? SIM_get_transaction_value_le(transaction) : 0,
               SIM_object_name(SIM_transaction_initiator(transaction)));
}

/* update cache_entry with value in write transaction */
static inline void cache_write_transaction_bytes(simbricks_mem_t *simbricks,
                                                 cache_entry_t *cache_entry,
                                                 transaction_t *transaction,
                                                 uint64 addr, uint64 cur_ts) {
  cache_entry->last_access_ts = cur_ts;
  uint64 cache_line_off = addr % simbricks->cache_line_size;
  unsigned int size = SIM_transaction_size(transaction);
  buffer_t buffer = {cache_entry->data + cache_line_off, size};
  SIM_get_transaction_bytes(transaction, buffer);

  SIM_LOG_INFO(3, &simbricks->obj, 1,
               "cache_write_transaction_bytes: ts=%llu addr=0x%llx size=%u "
               "value=0x%llx initiator=%s",
               cur_ts, addr, size,
               size <= 8 ? SIM_get_transaction_value_le(transaction) : 0,
               SIM_object_name(SIM_transaction_initiator(transaction)));
}

/******************************************************************************/
/* Message processing */

static void comp_waiter_event_callback(conf_object_t *obj, lang_void *data) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  cache_entry_t *cache_entry = (cache_entry_t *)data;
  ASSERT(cache_entry != NULL && cache_entry->waiters != NULL);
  mem_request_t *req = cache_entry->waiters;
  cycles_t cur_ts = SIM_cycle_count(simbricks->pico_second_clock);
  conf_object_t *initiator = SIM_transaction_initiator(req->transaction);
  bool is_write = SIM_transaction_is_write(req->transaction);

  SIM_LOG_INFO(
      3, obj, 1,
      "comp_waiter_event_callback: cur_ts=%lli is_write=%u addr=0x%llx size=%u "
      "cache_entry->addr=0x%llx  initiator=%s",
      cur_ts, is_write, req->addr, SIM_transaction_size(req->transaction),
      cache_entry->addr, SIM_object_name(initiator));

  /* Complete only first wating transaction and schedule an event 1 picosecond
   * later to complete the next transaction. This is necessary for atomic
   * instructions to work correctly. Simics assumes that all updates to the
   * memory are immediately visible to other cores. In the case of test-and-set,
   * the CPU will issue a write after a completed read operation in the same
   * cycle. We need to give this CPU the chance to do this write before
   * completing waiting transactions of any other CPUs. This ensures that the
   * other CPUs waiting for this cache line are able to see this write.
   * */
  cache_entry->last_access_ts = cur_ts;
  if (is_write) {
    cache_write_transaction_bytes(simbricks, cache_entry, req->transaction,
                                  req->addr, cur_ts);
  } else {
    cache_read_transaction_bytes(simbricks, cache_entry, req->transaction,
                                 req->addr, cur_ts);
  }

  if (req->next_waiter != NULL) {
    cache_entry->owner = initiator;
    ASSERT(cache_entry->owner != NULL);
    cache_entry->waiters = req->next_waiter;
    SIM_event_post_cycle(SIM_picosecond_clock(initiator), comp_waiter_event,
                         &simbricks->obj, 1, cache_entry);
  } else {
    cache_entry->waiters = NULL;
    cache_entry->owner = NULL;
  }

  SIM_complete_transaction(req->transaction, Sim_PE_No_Exception);
  MM_FREE(req);
}

/* process read completion from memory to host */
static void simbricks_comm_m2h_rcomp(simbricks_mem_t *simbricks,
                                     uint64 cur_ts,  // NOLINT
                                     uint64 req_id, const void *data) {
  mem_request_t *req = (mem_request_t *)req_id;  // NOLINT
  ASSERT(req != NULL && req->cache_entry);
  cache_entry_t *cache_entry = req->cache_entry;
  memcpy(&cache_entry->data, data, simbricks->cache_line_size);
  cache_entry->valid = true;
  comp_waiter_event_callback(&simbricks->obj, cache_entry);
}

/* process incoming SimBricks protocol messages from memory simulator */
static void simbricks_comm_m2h_process(
    simbricks_mem_t *simbricks, int64 cur_ts,
    volatile union SimbricksProtoMemM2H *msg) {
  uint8_t type;

  type = SimbricksMemIfM2HInType(&simbricks->memif, msg);

#if VERBOSE_DEBUG_PRINTS
  SIM_LOG_INFO(4, &simbricks->obj, 1,
               "simbricks_comm_m2h_process: ts=%lld type=%u", cur_ts, type);
#endif

  switch (type) {
    case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
      /* nop */
      break;
    case SIMBRICKS_PROTO_MEM_M2H_MSG_READCOMP:
      simbricks_comm_m2h_rcomp(simbricks, cur_ts, msg->readcomp.req_id,
                               (void *)msg->readcomp.data);
      break;
    case SIMBRICKS_PROTO_MEM_M2H_MSG_WRITECOMP:
      SIM_LOG_CRITICAL(
          &simbricks->obj, 1,
          "simbricks_comm_m2h_process: writes are treated as "
          "posted, so there shouldn't be a completion message here.");
      break;
    default:
      SIM_LOG_CRITICAL(&simbricks->obj, 1,
                       "simbricks_comm_m2h_process: unhandled type");
  }

  SimbricksMemIfM2HInDone(&simbricks->memif, msg);
}

/* sync event callback for sending synchronization messages to memory */
static void sync_event_callback(conf_object_t *obj, lang_void *data) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  cycles_t cur_ts = SIM_cycle_count(simbricks->pico_second_clock);
  uint64 proto_ts = ts_to_proto(simbricks, cur_ts);

  uint64 sync_ts = SimbricksMemIfH2MOutNextSync(&simbricks->memif);
  if (proto_ts > sync_ts + 1) {
    SIM_LOG_INFO(1, obj, 1,
                 "(WARNING) simbricks_timer_sync: expected_ts=%llu cur_ts=%llu",
                 sync_ts, proto_ts);
  }

#if VERBOSE_DEBUG_PRINTS
  SIM_LOG_INFO(4, obj, 1, "simbricks_timer_sync: ts=%lld pts=%llu npts=%llu",
               cur_ts, proto_ts, sync_ts);
#endif

  while (SimbricksMemIfH2MOutSync(&simbricks->memif, proto_ts)) {
  }

  uint64 next_sync_pts = SimbricksMemIfH2MOutNextSync(&simbricks->memif);
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
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  int64 cur_ts = SIM_cycle_count(simbricks->pico_second_clock);
  uint64 proto_ts = ts_to_proto(simbricks, cur_ts);
  uint64 next_ts;

  volatile union SimbricksProtoMemM2H *msg;
  volatile union SimbricksProtoMemM2H *next_msg;

  uint64 poll_ts = SimbricksMemIfM2HInTimestamp(&simbricks->memif);
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
    msg = SimbricksMemIfM2HInPoll(&simbricks->memif, proto_ts);
  } while (msg == NULL);

  simbricks_comm_m2h_process(simbricks, cur_ts, msg);

  /* process additional available messages */
  for (;;) {
    msg = SimbricksMemIfM2HInPoll(&simbricks->memif, proto_ts);
    if (msg == NULL) {
      break;
    }
    simbricks_comm_m2h_process(simbricks, cur_ts, msg);
  }

  /* Wait for next message so we know its timestamp and when to schedule the
   * timer. */
  do {
    next_msg = SimbricksMemIfM2HInPeek(&simbricks->memif, proto_ts);
    next_ts = SimbricksMemIfM2HInTimestamp(&simbricks->memif);
  } while (!next_msg && next_ts <= proto_ts);

  /* set timer for next message */
  SIM_event_post_cycle(simbricks->pico_second_clock, poll_event,
                       &simbricks->obj,
                       rel_to_current_proto(simbricks, next_ts), NULL);
}

/* allocate host-to-device queue entry */
static inline volatile union SimbricksProtoMemH2M *simbricks_comm_h2m_alloc(
    simbricks_mem_t *simbricks, cycles_t cur_ts) {
  volatile union SimbricksProtoMemH2M *msg;
  while (!(msg = SimbricksMemIfH2MOutAlloc(&simbricks->memif,
                                           ts_to_proto(simbricks, cur_ts)))) {
  }
  // performance optimization: reschedule sync timer since we are going to send
  // a message and an additional sync message is therefore not necessary for one
  // whole sync interal
  SIM_event_cancel_time(simbricks->pico_second_clock, sync_event,
                        &simbricks->obj, NULL, NULL);
  uint64 next_sync = SimbricksMemIfH2MOutNextSync(&simbricks->memif);
  cycles_t rel_next_sync = rel_to_current_proto(simbricks, next_sync);
  SIM_event_post_cycle(simbricks->pico_second_clock, sync_event,
                       &simbricks->obj, rel_next_sync, NULL);
  return msg;
}

/* process incoming Simics memory transaction */
static exception_type_t mem_handle_transaction(simbricks_mem_t *simbricks,
                                               transaction_t *transaction,
                                               uint64 addr) {
  volatile union SimbricksProtoMemH2M *msg;
  volatile struct SimbricksProtoMemH2MRead *read;
  volatile struct SimbricksProtoMemH2MWrite *write;
  cycles_t cur_ts = SIM_cycle_count(simbricks->pico_second_clock);
  unsigned int size = SIM_transaction_size(transaction);
  conf_object_t *initiator = SIM_transaction_initiator(transaction);

  if (size == 0) {
    return Sim_PE_No_Exception;
  }

  /* no split cache line transactions */
  ASSERT(addr / simbricks->cache_line_size ==
         (addr + size - 1) / simbricks->cache_line_size);

  /* handle write operation */
  if (SIM_transaction_is_write(transaction)) {
    msg = simbricks_comm_h2m_alloc(simbricks, cur_ts);
    write = &msg->write;
    write->addr = addr;
    write->len = size;

    unsigned int max_size =
        SimbricksMemIfH2MOutMsgLen(&simbricks->memif) - sizeof(*write);
    if (size > max_size) {
      SIM_LOG_CRITICAL(
          &simbricks->obj, 1,
          "Message size in out queue of %u does not suffice. Requiring %u.",
          max_size, size);
      return Sim_PE_IO_Error;
    }
    buffer_t data = {(uint8 *)write->data, size};
    SIM_get_transaction_bytes(transaction, data);

    SIM_LOG_INFO(3, &simbricks->obj, 1,
                 "mem_handle_transaction: Sending posted write to mem. ts=%llu "
                 "addr=0x%llx size=%u val=0x%llx",
                 cur_ts, addr, size,
                 size <= 8 ? SIM_get_transaction_value_le(transaction) : 0);

    SimbricksMemIfH2MOutSend(&simbricks->memif, msg,
                             SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE_POSTED);

    /* update cache line if one exists */
    cache_entry_t *cache_entry =
        cache_get_entry(simbricks, addr, false, cur_ts, true);

    if (cache_entry != NULL) {
      if (cache_entry->valid &&
          (cache_entry->waiters == NULL || cache_entry->owner == initiator)) {
        cache_write_transaction_bytes(simbricks, cache_entry, transaction, addr,
                                      cur_ts);
      } else if (cache_entry->waiters != NULL) {
        /* Cache entry is currently being fetched from memory. We therefore
        add an entry to the waiters list. Since this list is later handled
        from front to back, ordering of all transactions will be preserved. */

        /* defer transaction since we have to wait */
        mem_request_t *req = MM_ZALLOC(1, mem_request_t);
        req->cache_entry = cache_entry;
        req->addr = addr;
        req->transaction = SIM_defer_transaction(&simbricks->obj, transaction);
        if (!req->transaction) {
          MM_FREE(req);
          SIM_LOG_CRITICAL(&simbricks->obj, 1,
                           "mem_handle_transaction: cannot defer transaction "
                           "ts=%llu addr=0x%llx size=%u",
                           cur_ts, addr, size);
          return Sim_PE_Async_Required;
        }

        /* add to list of waiters */
        mem_request_t *waiters_end = cache_entry->waiters;
        for (; waiters_end->next_waiter != NULL;
             waiters_end = waiters_end->next_waiter) {
        }
        waiters_end->next_waiter = req;
        return Sim_PE_Deferred;
      }
    }

    /* we don't wait for the completion of writes so we are done here */
    return Sim_PE_No_Exception;
  }

  if (!SIM_transaction_is_read(transaction)) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1, "unsupported transaction type");
  }

  /* handle read transaction */
  /* check whether read cache contains the entry */
  cache_entry_t *cache_entry =
      cache_get_entry(simbricks, addr, true, cur_ts, true);
  if (cache_entry->valid &&
      (cache_entry->waiters == NULL || cache_entry->owner == initiator)) {
    cache_read_transaction_bytes(simbricks, cache_entry, transaction, addr,
                                 cur_ts);
    return Sim_PE_No_Exception;
  }

  /* cache entry needs to be requested first, so defer transaction */
  mem_request_t *req = MM_ZALLOC(1, mem_request_t);
  req->cache_entry = cache_entry;
  req->addr = addr;
  req->transaction = SIM_defer_transaction(&simbricks->obj, transaction);
  if (req->transaction == NULL) {
    MM_FREE(req);
    SIM_LOG_CRITICAL(&simbricks->obj, 1,
                     "mem_handle_transaction: cannot defer transaction "
                     "ts=%llu addr=0x%llx size=%u",
                     cur_ts, addr, size);
    return Sim_PE_Async_Required;
  }

  /* if already requested, add to list of waiters */
  if (cache_entry->waiters != NULL) {
    mem_request_t *waiters_end = cache_entry->waiters;
    for (; waiters_end->next_waiter != NULL;
         waiters_end = waiters_end->next_waiter) {
    }
    waiters_end->next_waiter = req;
    return Sim_PE_Deferred;
  }

  /* send read request */
  ASSERT(cache_entry->waiters == NULL);
  cache_entry->waiters = req;

  msg = simbricks_comm_h2m_alloc(simbricks, cur_ts);
  read = &msg->read;
  read->addr = cache_entry->addr;
  read->len = simbricks->cache_line_size;
  read->req_id = (uint64_t)req;

  SIM_LOG_INFO(
      3, &simbricks->obj, 1,
      "mem_handle_transaction: started wait for read (%llu) addr=0x%lx "
      "size=%u",
      cur_ts, read->addr, read->len);

  SimbricksMemIfH2MOutSend(&simbricks->memif, msg,
                           SIMBRICKS_PROTO_MEM_H2M_MSG_READ);

  return Sim_PE_Deferred;
}

/* define data structures for adding information about the split to a
transaction */
typedef struct {
  uint8 *data;
  unsigned num_splits;
  bool async;
  transaction_t *parent_transaction;
  transaction_t split_transactions[];
} split_transaction_info_t;

#define ATOM_TYPE_split_info split_transaction_info_t *
SIM_CUSTOM_ATOM(split_info);  // NOLINT

/* process results of split transactions and free resources */
exception_type_t split_transaction_comp_callback(
    conf_object_t *obj, transaction_t *comp_transaction, exception_type_t exc) {
  split_transaction_info_t *split_info =
      ATOM_get_transaction_split_info(comp_transaction);
  simbricks_mem_t *simbricks = (void *)obj;
  ASSERT(split_info);

  if (exc != Sim_PE_No_Exception) {
    SIM_LOG_CRITICAL(
        &simbricks->obj, 1,
        "split_transaction_comp_callback: transaction unsuccessful.");
    return exc;
  }

  /* copy read values */
  assert(split_info->parent_transaction);
  if (SIM_transaction_is_read(split_info->parent_transaction)) {
    bytes_t bytes = {split_info->data,
                     SIM_transaction_size(split_info->parent_transaction)};
    SIM_set_transaction_bytes(split_info->parent_transaction, bytes);
  }

  /* free resources */
  MM_FREE(split_info->data);
  for (unsigned i = 0; i < split_info->num_splits; ++i) {
    MM_FREE(split_info->split_transactions[i].atoms);
  }

  /* complete parent transaction */
  if (split_info->async) {
    SIM_complete_transaction(split_info->parent_transaction,
                             Sim_PE_No_Exception);
  }
  MM_FREE(split_info);
  return Sim_PE_No_Exception;
}

/* Implementation of Simics transaction interface: handles incoming memory
transactions. Incoming transactions are not aligned to cache lines, therefore
split them if necessary.*/
static exception_type_t mem_split_transaction(conf_object_t *obj,
                                              transaction_t *transaction,
                                              uint64 addr) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  conf_object_t *initiator = SIM_transaction_initiator(transaction);
  unsigned int size = SIM_transaction_size(transaction);

  /* calculate how many split transactions are necessary */
  unsigned split_size =
      MIN(size, simbricks->cache_line_size - addr % simbricks->cache_line_size);
  uint64 split_addr = addr;
  unsigned num_splits = 0;
  do {
    ++num_splits;
    split_addr += split_size;
    split_size = MIN(simbricks->cache_line_size, addr + size - split_addr);
  } while (split_addr < addr + size);

  SIM_LOG_INFO(3, obj, 1,
               "mem_split_transaction: splitting transaction. addr=0x%llx "
               "size=%u is_write=%u num_splits=%u initiator=%s",
               addr, size, SIM_transaction_is_write(transaction), num_splits,
               SIM_object_name(initiator));

  /* create and issue split transactions*/
  split_transaction_info_t *split_info = MM_ZALLOC_SZ(
      sizeof(split_transaction_info_t) + num_splits * sizeof(transaction_t),
      split_transaction_info_t);
  split_info->num_splits = num_splits;
  split_info->parent_transaction = transaction;

  split_info->data = MM_ZALLOC(size, uint8);
  if (SIM_transaction_is_write(transaction)) {
    buffer_t buffer = {split_info->data, size};
    SIM_get_transaction_bytes(transaction, buffer);
  }

  transaction_t *last_deferred_split_transaction = NULL;

  split_size =
      MIN(size, simbricks->cache_line_size - addr % simbricks->cache_line_size);
  split_addr = addr;
  for (unsigned i = 0; i < num_splits; ++i) {
    atom_t *atoms = MM_ZALLOC(8, atom_t);
    atoms[0] = ATOM_flags(SIM_transaction_flags(transaction));
    atoms[1] = ATOM_data(split_info->data + (split_addr - addr));
    atoms[2] = ATOM_size(split_size);
    atoms[3] = ATOM_initiator(initiator);
    atoms[4] = ATOM_split_info(split_info);
    /* Completion callback will only be invoked for transactions, which are
     * monitored by a call to SIM_monitor_transaction. We will do so on the last
     * deferred split transaction. The SimBricks protocol uses a FIFO queue to
     * exchange messages so this guarantees that all previously issued split
     * transaction will already be complete, when the last one completes.*/
    atoms[5] = ATOM_completion(split_transaction_comp_callback);
    atoms[6] = ATOM_owner(&simbricks->obj);
    atoms[7] = ATOM_LIST_END;
    split_info->split_transactions[i].atoms = atoms;

    exception_type_t split_exc = mem_handle_transaction(
        simbricks, &split_info->split_transactions[i], split_addr);
    if (split_exc != Sim_PE_No_Exception && split_exc != Sim_PE_Deferred) {
      SIM_LOG_CRITICAL(obj, 1,
                       "mem_split_transaction: split transaction not "
                       "successful. split_exc=%u",
                       split_exc);
      return split_exc;
    }

    if (split_exc == Sim_PE_Deferred) {
      last_deferred_split_transaction = &split_info->split_transactions[i];
    }

    split_addr += split_size;
    split_size = MIN(simbricks->cache_line_size, addr + size - split_addr);
  }

  /* defer transaction if not all split transactions could be completed
   * immediately */
  if (last_deferred_split_transaction != NULL) {
    split_info->async = true;
    split_info->parent_transaction = SIM_defer_transaction(obj, transaction);
    if (split_info->parent_transaction == NULL) {
      SIM_LOG_CRITICAL(&simbricks->obj, 1,
                       "mem_split_transaction: transaction cannot be deferred");
      return Sim_PE_Async_Required;
    }
    return SIM_monitor_transaction(last_deferred_split_transaction,
                                   Sim_PE_Deferred);
  }

  /* otherwise, we need to synchronously invoke the completion callback to copy
   * over read values */
  return split_transaction_comp_callback(
      &simbricks->obj, &split_info->split_transactions[num_splits - 1],
      Sim_PE_No_Exception);
}

/******************************************************************************/
/* Device Attribute Getters and Setters */

static attr_value_t get_socket_attr(conf_object_t *obj) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  return SIM_make_attr_string(simbricks->socket_path);
}
static set_error_t set_socket_attr(conf_object_t *obj, attr_value_t *attr_val) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  if (!SIM_attr_is_string(*attr_val)) {
    return Sim_Set_Illegal_Value;
  }
  simbricks->socket_path = SIM_attr_string(*attr_val);
  return Sim_Set_Ok;
}

static attr_value_t get_mem_latency_attr(conf_object_t *obj) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  return SIM_make_attr_uint64(simbricks->mem_latency);
}
static set_error_t set_mem_latency_attr(conf_object_t *obj,
                                        attr_value_t *attr_val) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  if (!SIM_attr_is_uint64(*attr_val)) {
    return Sim_Set_Illegal_Value;
  }
  simbricks->mem_latency = SIM_attr_integer(*attr_val);
  return Sim_Set_Ok;
}

static attr_value_t get_sync_period_attr(conf_object_t *obj) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  return SIM_make_attr_uint64(simbricks->sync_period);
}
static set_error_t set_sync_period_attr(conf_object_t *obj,
                                        attr_value_t *attr_val) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  if (!SIM_attr_is_uint64(*attr_val)) {
    return Sim_Set_Illegal_Value;
  }
  simbricks->sync_period = SIM_attr_integer(*attr_val);
  return Sim_Set_Ok;
}

static attr_value_t get_cache_size_attr(conf_object_t *obj) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  return SIM_make_attr_uint64(simbricks->cache_size);
}
static set_error_t set_cache_size_attr(conf_object_t *obj,
                                       attr_value_t *attr_val) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  if (!SIM_attr_is_uint64(*attr_val)) {
    return Sim_Set_Illegal_Value;
  }
  simbricks->cache_size = SIM_attr_integer(*attr_val);
  return Sim_Set_Ok;
}

static attr_value_t get_cache_line_size_attr(conf_object_t *obj) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  return SIM_make_attr_uint64(simbricks->cache_line_size);
}
static set_error_t set_cache_line_size_attr(conf_object_t *obj,
                                            attr_value_t *attr_val) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  if (!SIM_attr_is_uint64(*attr_val)) {
    return Sim_Set_Illegal_Value;
  }
  simbricks->cache_line_size = SIM_attr_integer(*attr_val);
  return Sim_Set_Ok;
}

/******************************************************************************/
/* Simics Initialization */

/* Allocate memory for the object. */
static conf_object_t *alloc_object(conf_class_t *cls) {
  simbricks_mem_t *empty = MM_ZALLOC(1, simbricks_mem_t);
  return &empty->obj;
}

/* Initialize the object before any attributes are set. */
static void *init_object(conf_object_t *obj) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;
  simbricks->sync = true;
  simbricks->cache_line_size = 64;
  simbricks->cache_size =
      128ul * 1024 * 1024 / simbricks->cache_line_size; /* 128 MiB*/
  return obj;
}

/* Initialization once all objects have been finalized, if needed. */
static void objects_finalized(conf_object_t *obj) {
  simbricks_mem_t *simbricks = (simbricks_mem_t *)obj;

  /* obtain picosecond clock */
  simbricks->pico_second_clock = SIM_picosecond_clock(obj);
  if (!simbricks->pico_second_clock) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1,
                     "objects_finalized: cannot obtain picosecond clock");
  }
  SIM_LOG_INFO(1, &simbricks->obj, 1,
               "objects_finalized: using picosecond clock name=%s",
               SIM_object_name(simbricks->pico_second_clock));
  if (!simbricks_connect(simbricks)) {
    SIM_LOG_CRITICAL(&simbricks->obj, 1, "simbricks_connect failed");
  }
}

/* Free memory allocated for the object. */
static void dealloc_object(conf_object_t *obj) {
  simbricks_mem_t *empty = (simbricks_mem_t *)obj;
  for (uint64 i = 0; i < empty->cache_size; ++i) {
    MM_FREE(empty->cache[i]);
  }
  MM_FREE(empty->cache);
  MM_FREE(empty);
}

/* Called once when the device module is loaded into Simics. */
void init_local(void) {
  /* Define and register the device class. */
  const class_info_t class_info = {.alloc = alloc_object,
                                   .init = init_object,
                                   .objects_finalized = objects_finalized,
                                   .dealloc = dealloc_object,
                                   .description = "SimBricks Memory Adapter",
                                   .short_desc = "SimBricks Memory Adapter",
                                   .kind = Sim_Class_Kind_Vanilla};
  conf_class_t *class = SIM_create_class("simbricks_mem", &class_info);

  /* register events we later want to insert into event queues */
  sync_event = SIM_register_event("simbricks-sync", class, Sim_EC_No_Flags,
                                  sync_event_callback, NULL, NULL, NULL, NULL);
  poll_event = SIM_register_event("simbricks-poll", class, Sim_EC_No_Flags,
                                  poll_event_callback, NULL, NULL, NULL, NULL);
  comp_waiter_event =
      SIM_register_event("simbricks-complete-waiter", class, Sim_EC_No_Flags,
                         comp_waiter_event_callback, NULL, NULL, NULL, NULL);

  /* Register the 'transaction' interface, which is the
     interface that is implemented by memory mapped devices. */
  static const transaction_interface_t kTransactionIface = {
      .issue = mem_split_transaction};
  SIM_REGISTER_INTERFACE(class, transaction, &kTransactionIface);

  // add device attributes
  SIM_register_attribute(class, "socket", get_socket_attr, set_socket_attr,
                         Sim_Attr_Required, "s",
                         "Socket Path for SimBricks messages");
  SIM_register_attribute(class, "mem_latency", get_mem_latency_attr,
                         set_mem_latency_attr, Sim_Attr_Required, "i",
                         "Latency host to memory");
  SIM_register_attribute(
      class, "sync_period", get_sync_period_attr, set_sync_period_attr,
      Sim_Attr_Required, "i",
      "Time between SimBricks synchronization messages in nanoseconds.");
  SIM_register_attribute(class, "cache_size", get_cache_size_attr,
                         set_cache_size_attr, Sim_Attr_Optional, "i",
                         "Number of cache lines.");
  SIM_register_attribute(class, "cache_line_size", get_cache_line_size_attr,
                         set_cache_line_size_attr, Sim_Attr_Optional, "i",
                         "Size of each cache line in bytes.");
}

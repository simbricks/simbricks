/*
 * Copyright 2021 Max Planck Institute for Software Systems, and
 * National University of Singapore
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 * CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

#include "lib/simbricks/nicbm/nicbm.h"

#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cassert>
#include <ctime>
#include <iostream>
#include <vector>

extern "C" {
#include <simbricks/base/proto.h>
}

#define ENABLE_PROFILING 1
// #define DEBUG_NICBM 1
#define DMA_MAX_PENDING 64

namespace nicbm {

static volatile int exiting = 0;

static std::vector<Runner *> runners;

static inline uint64_t Rdtsc(void) {
  uint32_t eax, edx;
  asm volatile ("rdtsc" : "=a" (eax), "=d" (edx));
  return ((uint64_t) edx << 32) | eax;
}

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
  std::cout << "STATS: tsc=" << Rdtsc() << std::endl;
  for (Runner *r : runners)
    r->DumpStats();
}

void Runner::DumpStats() const {
  std::cout << "  " << pcieParams_.sock_path << ": main_time=" << main_time_ <<
#ifdef ENABLE_PROFILING
      " tx_comm_cycles=" << statsPcie.cycles_tx_comm <<
      " tx_block_cycles=" << statsPcie.cycles_tx_block <<
      " tx_sync_cycles=" << statsPcie.cycles_tx_sync <<
      " rx_comm_cycles=" << statsPcie.cycles_rx_comm <<
      " rx_block_cycles=" << statsPcie.cycles_rx_block <<
      " tx_msgs=" << statsPcie.num_tx_msg <<
      " rx_msgs=" << statsPcie.num_rx_msg <<
      " rx_syncs=" << statsPcie.num_rx_sync <<
#endif
      std::endl;

  std::cout << "  " << netParams_.sock_path << ": main_time=" << main_time_ <<
#ifdef ENABLE_PROFILING
      " tx_comm_cycles=" << statsEth.cycles_tx_comm <<
      " tx_block_cycles=" << statsEth.cycles_tx_block <<
      " tx_sync_cycles=" << statsEth.cycles_tx_sync <<
      " rx_comm_cycles=" << statsEth.cycles_rx_comm <<
      " rx_block_cycles=" << statsEth.cycles_rx_block <<
      " tx_msgs=" << statsEth.num_tx_msg <<
      " rx_msgs=" << statsEth.num_rx_msg <<
      " rx_syncs=" << statsEth.num_rx_sync <<
#endif
      std::endl;
}

volatile union SimbricksProtoPcieD2H *Runner::D2HAlloc() {
  if (SimbricksBaseIfInTerminated(&nicif_.pcie.base)) {
    fprintf(stderr, "Runner::D2HAlloc: peer already terminated\n");
    abort();
  }

#ifdef ENABLE_PROFILING
  statsPcie.cycles_tx_start_tsc = Rdtsc();
#endif
  volatile union SimbricksProtoPcieD2H *msg;
  bool first = true;
  while ((msg = SimbricksPcieIfD2HOutAlloc(&nicif_.pcie, main_time_)) == NULL) {
    if (first) {
      fprintf(stderr, "D2HAlloc: warning waiting for entry (%zu)\n",
              nicif_.pcie.base.out_pos);
      first = false;
    }
#ifdef ENABLE_PROFILING
    statsPcie.cycles_tx_block += Rdtsc() - statsPcie.cycles_tx_start_tsc;
#endif
    YieldPoll();
#ifdef ENABLE_PROFILING
    statsPcie.cycles_tx_start_tsc = Rdtsc();
#endif
  }

  if (!first)
    fprintf(stderr, "D2HAlloc: entry successfully allocated\n");

  return msg;
}

void Runner::D2HOutSend(volatile union SimbricksProtoPcieD2H *msg, uint8_t ty) {
  SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg, ty);
#ifdef ENABLE_PROFILING
  statsPcie.cycles_tx_comm += Rdtsc() - statsPcie.cycles_tx_start_tsc;
  statsPcie.num_tx_msg++;
#endif
}

volatile union SimbricksProtoNetMsg *Runner::D2NAlloc() {
  volatile union SimbricksProtoNetMsg *msg;
  bool first = true;
#ifdef ENABLE_PROFILING
  statsEth.cycles_tx_start_tsc = Rdtsc();
#endif
  while ((msg = SimbricksNetIfOutAlloc(&nicif_.net, main_time_)) == NULL) {
    if (first) {
      fprintf(stderr, "D2NAlloc: warning waiting for entry (%zu)\n",
              nicif_.pcie.base.out_pos);
      first = false;
    }
#ifdef ENABLE_PROFILING
    statsEth.cycles_tx_block += Rdtsc() - statsEth.cycles_tx_start_tsc;
#endif
    YieldPoll();
#ifdef ENABLE_PROFILING
    statsEth.cycles_tx_start_tsc = Rdtsc();
#endif
  }


  if (!first)
    fprintf(stderr, "D2NAlloc: entry successfully allocated\n");

  return msg;
}

void Runner::D2NOutSend(volatile union SimbricksProtoNetMsg *msg, uint8_t ty) {
  SimbricksNetIfOutSend(&nicif_.net, msg, ty);
#ifdef ENABLE_PROFILING
  statsEth.cycles_tx_comm += Rdtsc() - statsEth.cycles_tx_start_tsc;
  statsEth.num_tx_msg++;
#endif
}

void Runner::IssueDma(DMAOp &op) {
  if (dma_pending_ < DMA_MAX_PENDING) {
    // can directly issue
#ifdef DEBUG_NICBM
    printf(
        "main_time = %lu: nicbm: issuing dma op %p addr %lx len %zu pending "
        "%zu\n",
        main_time_, &op, op.dma_addr_, op.len_, dma_pending_);
#endif
    DmaDo(op);
  } else {
#ifdef DEBUG_NICBM
    printf(
        "main_time = %lu: nicbm: enqueuing dma op %p addr %lx len %zu pending "
        "%zu\n",
        main_time_, &op, op.dma_addr_, op.len_, dma_pending_);
#endif
    dma_queue_.push_back(&op);
  }
}

void Runner::DmaTrigger() {
  if (dma_queue_.empty() || dma_pending_ == DMA_MAX_PENDING)
    return;

  DMAOp *op = dma_queue_.front();
  dma_queue_.pop_front();

  DmaDo(*op);
}

void Runner::DmaDo(DMAOp &op) {
  if (SimbricksBaseIfInTerminated(&nicif_.pcie.base))
    return;

  volatile union SimbricksProtoPcieD2H *msg = D2HAlloc();
  dma_pending_++;
#ifdef DEBUG_NICBM
  printf(
      "main_time = %lu: nicbm: executing dma op %p addr %lx len %zu pending "
      "%zu\n",
      main_time_, &op, op.dma_addr_, op.len_, dma_pending_);
#endif

  size_t maxlen = SimbricksBaseIfOutMsgLen(&nicif_.pcie.base);
  if (op.write_) {
    volatile struct SimbricksProtoPcieD2HWrite *write = &msg->write;
    if (maxlen < sizeof(*write) + op.len_) {
      fprintf(stderr,
              "issue_dma: write too big (%zu), can only fit up "
              "to (%zu)\n",
              op.len_, maxlen - sizeof(*write));
      abort();
    }

    write->req_id = (uintptr_t)&op;
    write->offset = op.dma_addr_;
    write->len = op.len_;
    memcpy((void *)write->data, (void *)op.data_, op.len_);

#ifdef DEBUG_NICBM
    uint8_t *tmp = (uint8_t *)op.data_;
    int d;
    printf("main_time = %lu: nicbm: dma write data: \n", main_time_);
    for (d = 0; d < op.len_; d++) {
      printf("%02X ", *tmp);
      tmp++;
    }
#endif
    D2HOutSend(msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_WRITE);
  } else {
    volatile struct SimbricksProtoPcieD2HRead *read = &msg->read;
    if (maxlen < sizeof(struct SimbricksProtoPcieH2DReadcomp) + op.len_) {
      fprintf(stderr,
              "issue_dma: write too big (%zu), can only fit up "
              "to (%zu)\n",
              op.len_, maxlen - sizeof(struct SimbricksProtoPcieH2DReadcomp));
      abort();
    }

    read->req_id = (uintptr_t)&op;
    read->offset = op.dma_addr_;
    read->len = op.len_;
    D2HOutSend(msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_READ);
  }
}

void Runner::MsiIssue(uint8_t vec) {
  if (SimbricksBaseIfInTerminated(&nicif_.pcie.base))
    return;

  volatile union SimbricksProtoPcieD2H *msg = D2HAlloc();
#ifdef DEBUG_NICBM
  printf("main_time = %lu: nicbm: issue MSI interrupt vec %u\n", main_time_,
         vec);
#endif
  volatile struct SimbricksProtoPcieD2HInterrupt *intr = &msg->interrupt;
  intr->vector = vec;
  intr->inttype = SIMBRICKS_PROTO_PCIE_INT_MSI;

  D2HOutSend(msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT);
}

void Runner::MsiXIssue(uint8_t vec) {
  if (SimbricksBaseIfInTerminated(&nicif_.pcie.base))
    return;

  volatile union SimbricksProtoPcieD2H *msg = D2HAlloc();
#ifdef DEBUG_NICBM
  printf("main_time = %lu: nicbm: issue MSI-X interrupt vec %u\n", main_time_,
         vec);
#endif
  volatile struct SimbricksProtoPcieD2HInterrupt *intr = &msg->interrupt;
  intr->vector = vec;
  intr->inttype = SIMBRICKS_PROTO_PCIE_INT_MSIX;

  D2HOutSend(msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT);
}

void Runner::IntXIssue(bool level) {
  if (SimbricksBaseIfInTerminated(&nicif_.pcie.base))
    return;

  volatile union SimbricksProtoPcieD2H *msg = D2HAlloc();
#ifdef DEBUG_NICBM
  printf("main_time = %lu: nicbm: set intx interrupt %u\n", main_time_, level);
#endif
  volatile struct SimbricksProtoPcieD2HInterrupt *intr = &msg->interrupt;
  intr->vector = 0;
  intr->inttype = (level ? SIMBRICKS_PROTO_PCIE_INT_LEGACY_HI
                         : SIMBRICKS_PROTO_PCIE_INT_LEGACY_LO);

  D2HOutSend(msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT);
}

void Runner::EventSchedule(TimedEvent &evt) {
  events_.insert(&evt);
}

void Runner::EventCancel(TimedEvent &evt) {
  events_.erase(&evt);
}

void Runner::H2DRead(volatile struct SimbricksProtoPcieH2DRead *read) {
  volatile union SimbricksProtoPcieD2H *msg;
  volatile struct SimbricksProtoPcieD2HReadcomp *rc;

  msg = D2HAlloc();
  rc = &msg->readcomp;

  dev_.RegRead(read->bar, read->offset, (void *)rc->data, read->len);
  rc->req_id = read->req_id;

#ifdef DEBUG_NICBM
  uint64_t dbg_val = 0;
  memcpy(&dbg_val, (const void *)rc->data, read->len <= 8 ? read->len : 8);
  printf("main_time = %lu: nicbm: read(off=0x%lx, len=%u, val=0x%lx)\n",
         main_time_, read->offset, read->len, dbg_val);
#endif

  D2HOutSend(msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_READCOMP);
}

void Runner::H2DWrite(volatile struct SimbricksProtoPcieH2DWrite *write,
                      bool posted) {
  volatile union SimbricksProtoPcieD2H *msg;
  volatile struct SimbricksProtoPcieD2HWritecomp *wc;

#ifdef DEBUG_NICBM
  uint64_t dbg_val = 0;
  memcpy(&dbg_val, (const void *)write->data, write->len <= 8 ? write->len : 8);
  printf(
      "main_time = %lu: nicbm: write(off=0x%lx, len=%u, val=0x%lx, "
      "posted=%u)\n",
      main_time_, write->offset, write->len, dbg_val, posted);
#endif
  dev_.RegWrite(write->bar, write->offset, (void *)write->data, write->len);

  if (!posted) {
    msg = D2HAlloc();
    wc = &msg->writecomp;
    wc->req_id = write->req_id;

    D2HOutSend(msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_WRITECOMP);
  }
}

void Runner::H2DReadcomp(volatile struct SimbricksProtoPcieH2DReadcomp *rc) {
  DMAOp *op = (DMAOp *)(uintptr_t)rc->req_id;

#ifdef DEBUG_NICBM
  printf("main_time = %lu: nicbm: completed dma read op %p addr %lx len %zu\n",
         main_time_, op, op->dma_addr_, op->len_);
#endif

  memcpy(op->data_, (void *)rc->data, op->len_);
  dev_.DmaComplete(*op);

  dma_pending_--;
  DmaTrigger();
}

void Runner::H2DWritecomp(volatile struct SimbricksProtoPcieH2DWritecomp *wc) {
  DMAOp *op = (DMAOp *)(uintptr_t)wc->req_id;

#ifdef DEBUG_NICBM
  printf("main_time = %lu: nicbm: completed dma write op %p addr %lx len %zu\n",
         main_time_, op, op->dma_addr_, op->len_);
#endif

  dev_.DmaComplete(*op);

  dma_pending_--;
  DmaTrigger();
}

void Runner::H2DDevctrl(volatile struct SimbricksProtoPcieH2DDevctrl *dc) {
  dev_.DevctrlUpdate(*(struct SimbricksProtoPcieH2DDevctrl *)dc);
}

void Runner::EthRecv(volatile struct SimbricksProtoNetMsgPacket *packet) {
#ifdef DEBUG_NICBM
  printf("main_time = %lu: nicbm: eth rx: port %u len %u\n", main_time_,
         packet->port, packet->len);
#endif

  dev_.EthRx(packet->port, (void *)packet->data, packet->len);
}

void Runner::EthSend(const void *data, size_t len) {
#ifdef DEBUG_NICBM
  printf("main_time = %lu: nicbm: eth tx: len %zu\n", main_time_, len);
#endif

  volatile union SimbricksProtoNetMsg *msg = D2NAlloc();
  volatile struct SimbricksProtoNetMsgPacket *packet = &msg->packet;
  packet->port = 0;  // single port
  packet->len = len;
  memcpy((void *)packet->data, data, len);
  D2NOutSend(msg, SIMBRICKS_PROTO_NET_MSG_PACKET);
}

void Runner::PollH2D() {
  volatile union SimbricksProtoPcieH2D *msg =
      SimbricksPcieIfH2DInPoll(&nicif_.pcie, main_time_);
  uint8_t type;

  if (msg == NULL)
    return;

  type = SimbricksPcieIfH2DInType(&nicif_.pcie, msg);
#ifdef ENABLE_PROFILING
  if (type == SIMBRICKS_PROTO_MSG_TYPE_SYNC)
    statsPcie.num_rx_sync++;
  else
    statsPcie.num_rx_msg++;
  statsPcie.cycles_rx_comm += Rdtsc() - statsPcie.cycles_rx_start_tsc;
#endif
  switch (type) {
    case SIMBRICKS_PROTO_PCIE_H2D_MSG_READ:
      H2DRead(&msg->read);
      break;

    case SIMBRICKS_PROTO_PCIE_H2D_MSG_WRITE:
      H2DWrite(&msg->write, false);
      break;

    case SIMBRICKS_PROTO_PCIE_H2D_MSG_WRITE_POSTED:
      H2DWrite(&msg->write, true);
      break;

    case SIMBRICKS_PROTO_PCIE_H2D_MSG_READCOMP:
      H2DReadcomp(&msg->readcomp);
      break;

    case SIMBRICKS_PROTO_PCIE_H2D_MSG_WRITECOMP:
      H2DWritecomp(&msg->writecomp);
      break;

    case SIMBRICKS_PROTO_PCIE_H2D_MSG_DEVCTRL:
      H2DDevctrl(&msg->devctrl);
      break;

    case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
      break;

    case SIMBRICKS_PROTO_MSG_TYPE_TERMINATE:
      fprintf(stderr, "poll_h2d: peer terminated\n");
      break;

    default:
      fprintf(stderr, "poll_h2d: unsupported type=%u\n", type);
  }
#ifdef ENABLE_PROFILING
  statsPcie.cycles_rx_start_tsc = Rdtsc();
#endif
  SimbricksPcieIfH2DInDone(&nicif_.pcie, msg);
}

void Runner::PollN2D() {
  volatile union SimbricksProtoNetMsg *msg =
      SimbricksNetIfInPoll(&nicif_.net, main_time_);
  uint8_t t;

  if (msg == NULL)
    return;

  t = SimbricksNetIfInType(&nicif_.net, msg);
#ifdef ENABLE_PROFILING
  if (t == SIMBRICKS_PROTO_MSG_TYPE_SYNC)
    statsEth.num_rx_sync++;
  else
    statsEth.num_rx_msg++;
  statsEth.cycles_rx_comm += Rdtsc() - statsEth.cycles_rx_start_tsc;
#endif
  switch (t) {
    case SIMBRICKS_PROTO_NET_MSG_PACKET:
      EthRecv(&msg->packet);
      break;

    case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
      break;

    default:
      fprintf(stderr, "poll_n2d: unsupported type=%u", t);
  }
#ifdef ENABLE_PROFILING
  statsEth.cycles_rx_start_tsc = Rdtsc();
#endif
  SimbricksNetIfInDone(&nicif_.net, msg);
}

uint64_t Runner::TimePs() const {
  return main_time_;
}

uint64_t Runner::GetMacAddr() const {
  return mac_addr_;
}

bool Runner::EventNext(uint64_t &retval) {
  if (events_.empty())
    return false;

  retval = (*events_.begin())->time_;
  return true;
}

void Runner::EventTrigger() {
  auto it = events_.begin();
  if (it == events_.end())
    return;

  TimedEvent *ev = *it;

  // event is in the future
  if (ev->time_ > main_time_)
    return;

  events_.erase(it);
  dev_.Timed(*ev);
}

void Runner::YieldPoll() {
}

int Runner::NicIfInit() {
  return SimbricksNicIfInit(&nicif_, shmPath_, &netParams_, &pcieParams_,
                            &dintro_);
}

Runner::Runner(Device &dev) : main_time_(0), dev_(dev), events_(EventCmp()) {
  // mac_addr = lrand48() & ~(3ULL << 46);
  runners.push_back(this);
  dma_pending_ = 0;
  dev_.runner_ = this;

  int rfd;
  if ((rfd = open("/dev/urandom", O_RDONLY)) < 0) {
    perror("Runner::Runner: opening urandom failed");
    abort();
  }
  if (read(rfd, &mac_addr_, 6) != 6) {
    perror("Runner::Runner: reading urandom failed");
  }
  close(rfd);
  mac_addr_ &= ~3ULL;

  SimbricksNetIfDefaultParams(&netParams_);
  SimbricksPcieIfDefaultParams(&pcieParams_);
}

int Runner::ParseArgs(int argc, char *argv[]) {
  if (argc < 4 || argc > 10) {
    fprintf(stderr,
            "Usage: corundum_bm PCI-SOCKET ETH-SOCKET "
            "SHM [SYNC-MODE] [START-TICK] [SYNC-PERIOD] [PCI-LATENCY] "
            "[ETH-LATENCY] [MAC-ADDR]\n");
    return -1;
  }
  if (argc >= 6)
    main_time_ = strtoull(argv[5], NULL, 0);
  if (argc >= 7)
    netParams_.sync_interval = pcieParams_.sync_interval =
        strtoull(argv[6], NULL, 0) * 1000ULL;
  if (argc >= 8)
    pcieParams_.link_latency = strtoull(argv[7], NULL, 0) * 1000ULL;
  if (argc >= 9)
    netParams_.link_latency = strtoull(argv[8], NULL, 0) * 1000ULL;
  if (argc >= 10)
    mac_addr_ = strtoull(argv[9], NULL, 16);

  pcieParams_.sock_path = argv[1];
  netParams_.sock_path = argv[2];
  shmPath_ = argv[3];
  return 0;
}

int Runner::RunMain() {
  uint64_t next_ts;
  uint64_t max_step = 10000;

  signal(SIGINT, sigint_handler);
  signal(SIGUSR1, sigusr1_handler);

  memset(&dintro_, 0, sizeof(dintro_));
  dev_.SetupIntro(dintro_);

  if (NicIfInit()) {
    return EXIT_FAILURE;
  }
  bool sync_pcie = SimbricksBaseIfSyncEnabled(&nicif_.pcie.base);
  bool sync_net = SimbricksBaseIfSyncEnabled(&nicif_.net.base);

  fprintf(stderr, "mac_addr=%lx\n", mac_addr_);
  fprintf(stderr, "sync_pci=%d sync_eth=%d\n", sync_pcie, sync_net);

  bool is_sync = sync_pcie || sync_net;

  while (!exiting) {
#ifdef ENABLE_PROFILING
    uint64_t tsc = Rdtsc();
    uint64_t sync_start_tsc = tsc;
#endif
    while (SimbricksNicIfSync(&nicif_, main_time_)) {
      fprintf(stderr, "warn: SimbricksNicIfSync failed (t=%lu)\n", main_time_);
      YieldPoll();
    }
#ifdef ENABLE_PROFILING
    tsc = Rdtsc();
    statsPcie.cycles_tx_sync += (tsc - sync_start_tsc) / 2;
    statsEth.cycles_tx_sync += (tsc - sync_start_tsc) / 2;
    statsPcie.cycles_rx_start_tsc = tsc;
    statsEth.cycles_rx_start_tsc = tsc;
#endif
    bool first = true;
    do {
      if (!first) {
#ifdef ENABLE_PROFILING
        tsc = Rdtsc();
        statsPcie.cycles_rx_block += tsc - statsPcie.cycles_rx_start_tsc;
        statsEth.cycles_rx_block += tsc - statsEth.cycles_rx_start_tsc;
#endif
        YieldPoll();
#ifdef ENABLE_PROFILING
        tsc = Rdtsc();
        statsPcie.cycles_rx_start_tsc = tsc;
        statsEth.cycles_rx_start_tsc = tsc;
#endif
      }
      first = false;

      PollH2D();
      PollN2D();
      EventTrigger();

      if (is_sync) {
        next_ts = SimbricksNicIfNextTimestamp(&nicif_);
        if (next_ts > main_time_ + max_step)
          next_ts = main_time_ + max_step;
      } else {
        next_ts = main_time_ + max_step;
      }

      uint64_t ev_ts;
      if (EventNext(ev_ts) && ev_ts < next_ts)
        next_ts = ev_ts;
    } while (next_ts <= main_time_ && !exiting);
    main_time_ = next_ts;

    YieldPoll();
  }

  fprintf(stderr, "exit main_time: %lu\n", main_time_);
  SimbricksNicIfCleanup(&nicif_);
  return 0;
}

void Runner::Device::Timed(TimedEvent &te) {
}

void Runner::Device::DevctrlUpdate(
    struct SimbricksProtoPcieH2DDevctrl &devctrl) {
  int_intx_en_ = devctrl.flags & SIMBRICKS_PROTO_PCIE_CTRL_INTX_EN;
  int_msi_en_ = devctrl.flags & SIMBRICKS_PROTO_PCIE_CTRL_MSI_EN;
  int_msix_en_ = devctrl.flags & SIMBRICKS_PROTO_PCIE_CTRL_MSIX_EN;
}

}  // namespace nicbm

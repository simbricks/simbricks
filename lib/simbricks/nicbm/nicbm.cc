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

// #define DEBUG_NICBM 1
#define STAT_NICBM 1
#define DMA_MAX_PENDING 64

namespace nicbm {

static volatile int exiting = 0;

static std::vector<Runner *> runners;

#ifdef STAT_NICBM
static uint64_t h2d_poll_total = 0;
static uint64_t h2d_poll_suc = 0;
static uint64_t h2d_poll_sync = 0;
// count from signal USR2
static uint64_t s_h2d_poll_total = 0;
static uint64_t s_h2d_poll_suc = 0;
static uint64_t s_h2d_poll_sync = 0;

static uint64_t n2d_poll_total = 0;
static uint64_t n2d_poll_suc = 0;
static uint64_t n2d_poll_sync = 0;
// count from signal USR2
static uint64_t s_n2d_poll_total = 0;
static uint64_t s_n2d_poll_suc = 0;
static uint64_t s_n2d_poll_sync = 0;
static int stat_flag = 0;
#endif

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
  for (Runner *r : runners)
    fprintf(stderr, "[%p] main_time = %lu\n", r, r->TimePs());
}

#ifdef STAT_NICBM
static void sigusr2_handler(int dummy) {
  stat_flag = 1;
}
#endif

volatile union SimbricksProtoPcieD2H *Runner::D2HAlloc() {
  if (SimbricksBaseIfInTerminated(&nicif_.pcie.base)) {
    fprintf(stderr, "Runner::D2HAlloc: peer already terminated\n");
    abort();
  }

  volatile union SimbricksProtoPcieD2H *msg;
  bool first = true;
  while ((msg = SimbricksPcieIfD2HOutAlloc(&nicif_.pcie, main_time_)) == NULL) {
    if (first) {
      fprintf(stderr, "D2HAlloc: warning waiting for entry (%zu)\n",
              nicif_.pcie.base.out_pos);
      first = false;
    }
    YieldPoll();
  }

  if (!first)
    fprintf(stderr, "D2HAlloc: entry successfully allocated\n");

  return msg;
}

volatile union SimbricksProtoNetMsg *Runner::D2NAlloc() {
  volatile union SimbricksProtoNetMsg *msg;
  bool first = true;
  while ((msg = SimbricksNetIfOutAlloc(&nicif_.net, main_time_)) == NULL) {
    if (first) {
      fprintf(stderr, "D2NAlloc: warning waiting for entry (%zu)\n",
              nicif_.pcie.base.out_pos);
      first = false;
    }
    YieldPoll();
  }

  if (!first)
    fprintf(stderr, "D2NAlloc: entry successfully allocated\n");

  return msg;
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
    SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg,
                              SIMBRICKS_PROTO_PCIE_D2H_MSG_WRITE);
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
    SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg,
                              SIMBRICKS_PROTO_PCIE_D2H_MSG_READ);
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

  SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg,
                            SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT);
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

  SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg,
                            SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT);
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

  SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg,
                            SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT);
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

  SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg,
                            SIMBRICKS_PROTO_PCIE_D2H_MSG_READCOMP);
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

    SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg,
                              SIMBRICKS_PROTO_PCIE_D2H_MSG_WRITECOMP);
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
  SimbricksNetIfOutSend(&nicif_.net, msg, SIMBRICKS_PROTO_NET_MSG_PACKET);
}

void Runner::PollH2D() {
  volatile union SimbricksProtoPcieH2D *msg =
      SimbricksPcieIfH2DInPoll(&nicif_.pcie, main_time_);
  uint8_t type;

#ifdef STAT_NICBM
  h2d_poll_total += 1;
  if (stat_flag) {
    s_h2d_poll_total += 1;
  }
#endif

  if (msg == NULL)
    return;

#ifdef STAT_NICBM
  h2d_poll_suc += 1;
  if (stat_flag) {
    s_h2d_poll_suc += 1;
  }
#endif

  type = SimbricksPcieIfH2DInType(&nicif_.pcie, msg);
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
#ifdef STAT_NICBM
      h2d_poll_sync += 1;
      if (stat_flag) {
        s_h2d_poll_sync += 1;
      }
#endif
      break;

    case SIMBRICKS_PROTO_MSG_TYPE_TERMINATE:
      fprintf(stderr, "poll_h2d: peer terminated\n");
      break;

    default:
      fprintf(stderr, "poll_h2d: unsupported type=%u\n", type);
  }

  SimbricksPcieIfH2DInDone(&nicif_.pcie, msg);
}

void Runner::PollN2D() {
  volatile union SimbricksProtoNetMsg *msg =
      SimbricksNetIfInPoll(&nicif_.net, main_time_);
  uint8_t t;

#ifdef STAT_NICBM
  n2d_poll_total += 1;
  if (stat_flag) {
    s_n2d_poll_total += 1;
  }
#endif

  if (msg == NULL)
    return;

#ifdef STAT_NICBM
  n2d_poll_suc += 1;
  if (stat_flag) {
    s_n2d_poll_suc += 1;
  }
#endif

  t = SimbricksNetIfInType(&nicif_.net, msg);
  switch (t) {
    case SIMBRICKS_PROTO_NET_MSG_PACKET:
      EthRecv(&msg->packet);
      break;

    case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
#ifdef STAT_NICBM
      n2d_poll_sync += 1;
      if (stat_flag) {
        s_n2d_poll_sync += 1;
      }
#endif
      break;

    default:
      fprintf(stderr, "poll_n2d: unsupported type=%u", t);
  }

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
#ifdef STAT_NICBM
  signal(SIGUSR2, sigusr2_handler);
#endif

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
    while (SimbricksNicIfSync(&nicif_, main_time_)) {
      fprintf(stderr, "warn: SimbricksNicIfSync failed (t=%lu)\n", main_time_);
      YieldPoll();
    }

    bool first = true;
    do {
      if (!first)
        YieldPoll();
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
#ifdef STAT_NICBM
  fprintf(stderr, "%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n",
          "h2d_poll_total", h2d_poll_total, "h2d_poll_suc", h2d_poll_suc,
          (double)h2d_poll_suc / h2d_poll_total);

  fprintf(stderr, "%65s: %22lu  sync_rate: %f\n", "h2d_poll_sync",
          h2d_poll_sync, (double)h2d_poll_sync / h2d_poll_suc);

  fprintf(stderr, "%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n",
          "n2d_poll_total", n2d_poll_total, "n2d_poll_suc", n2d_poll_suc,
          (double)n2d_poll_suc / n2d_poll_total);

  fprintf(stderr, "%65s: %22lu  sync_rate: %f\n", "n2d_poll_sync",
          n2d_poll_sync, (double)n2d_poll_sync / n2d_poll_suc);

  fprintf(
      stderr, "%20s: %22lu %20s: %22lu  sync_rate: %f\n", "recv_total",
      h2d_poll_suc + n2d_poll_suc, "recv_sync", h2d_poll_sync + n2d_poll_sync,
      (double)(h2d_poll_sync + n2d_poll_sync) / (h2d_poll_suc + n2d_poll_suc));

  fprintf(stderr, "%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n",
          "s_h2d_poll_total", s_h2d_poll_total, "s_h2d_poll_suc",
          s_h2d_poll_suc, (double)s_h2d_poll_suc / s_h2d_poll_total);

  fprintf(stderr, "%65s: %22lu  sync_rate: %f\n", "s_h2d_poll_sync",
          s_h2d_poll_sync, (double)s_h2d_poll_sync / s_h2d_poll_suc);

  fprintf(stderr, "%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n",
          "s_n2d_poll_total", s_n2d_poll_total, "s_n2d_poll_suc",
          s_n2d_poll_suc, (double)s_n2d_poll_suc / s_n2d_poll_total);

  fprintf(stderr, "%65s: %22lu  sync_rate: %f\n", "s_n2d_poll_sync",
          s_n2d_poll_sync, (double)s_n2d_poll_sync / s_n2d_poll_suc);

  fprintf(stderr, "%20s: %22lu %20s: %22lu  sync_rate: %f\n", "s_recv_total",
          s_h2d_poll_suc + s_n2d_poll_suc, "s_recv_sync",
          s_h2d_poll_sync + s_n2d_poll_sync,
          (double)(s_h2d_poll_sync + s_n2d_poll_sync) /
              (s_h2d_poll_suc + s_n2d_poll_suc));
#endif

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

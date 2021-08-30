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

extern "C" {
#include <simbricks/proto/base.h>
}

//#define DEBUG_NICBM 1
#define STAT_NICBM 1
#define DMA_MAX_PENDING 64

namespace nicbm {

static volatile int exiting = 0;

static uint64_t main_time = 0;

#ifdef  STAT_NICBM
static uint64_t h2d_poll_total = 0;
static uint64_t h2d_poll_suc = 0;
static uint64_t h2d_poll_sync = 0;
//count from signal USR2
static uint64_t s_h2d_poll_total = 0;
static uint64_t s_h2d_poll_suc = 0;
static uint64_t s_h2d_poll_sync = 0;

static uint64_t n2d_poll_total = 0;
static uint64_t n2d_poll_suc = 0;
static uint64_t n2d_poll_sync = 0;
//count from signal USR2
static uint64_t s_n2d_poll_total = 0;
static uint64_t s_n2d_poll_suc = 0;
static uint64_t s_n2d_poll_sync = 0;
static int stat_flag = 0;
#endif

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
  fprintf(stderr, "main_time = %lu\n", main_time);
}

#ifdef STAT_NICBM
static void sigusr2_handler(int dummy) {
  stat_flag = 1;
}
#endif

volatile union SimbricksProtoPcieD2H *Runner::D2HAlloc() {
  volatile union SimbricksProtoPcieD2H *msg;
  bool first = true;
  while ((msg = SimbricksNicIfD2HAlloc(&nicif_, main_time)) == NULL) {
    if (first) {
      fprintf(stderr, "D2HAlloc: warning waiting for entry (%zu)\n",
              nicif_.d2h_pos);
      first = false;
    }
  }

  if (!first)
    fprintf(stderr, "D2HAlloc: entry successfully allocated\n");

  return msg;
}

volatile union SimbricksProtoNetD2N *Runner::D2NAlloc() {
  volatile union SimbricksProtoNetD2N *msg;
  bool first = true;
  while ((msg = SimbricksNicIfD2NAlloc(&nicif_, main_time)) == NULL) {
    if (first) {
      fprintf(stderr, "D2NAlloc: warning waiting for entry (%zu)\n",
              nicif_.d2n_pos);
      first = false;
    }
  }

  if (!first)
    fprintf(stderr, "D2NAlloc: entry successfully allocated\n");

  return msg;
}

void Runner::IssueDma(DMAOp &op) {
  if (dma_pending_ < DMA_MAX_PENDING) {
    // can directly issue
#ifdef DEBUG_NICBM
    printf("nicbm: issuing dma op %p addr %lx len %zu pending %zu\n", &op,
           op.dma_addr_, op.len_, dma_pending_);
#endif
    DmaDo(op);
  } else {
#ifdef DEBUG_NICBM
    printf("nicbm: enqueuing dma op %p addr %lx len %zu pending %zu\n", &op,
           op.dma_addr_, op.len_, dma_pending_);
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
  volatile union SimbricksProtoPcieD2H *msg = D2HAlloc();
  dma_pending_++;
#ifdef DEBUG_NICBM
  printf("nicbm: executing dma op %p addr %lx len %zu pending %zu\n", &op,
         op.dma_addr_, op.len_, dma_pending_);
#endif

  if (op.write_) {
    volatile struct SimbricksProtoPcieD2HWrite *write = &msg->write;
    if (dintro_.d2h_elen < sizeof(*write) + op.len_) {
      fprintf(stderr,
              "issue_dma: write too big (%zu), can only fit up "
              "to (%zu)\n",
              op.len_, dintro_.d2h_elen - sizeof(*write));
      abort();
    }

    write->req_id = (uintptr_t)&op;
    write->offset = op.dma_addr_;
    write->len = op.len_;
    memcpy((void *)write->data, (void *)op.data_, op.len_);
    
#ifdef DEBUG_NICBM
    uint8_t *tmp = (uint8_t*)op.data_;
    int d;
    printf("nicbm: dma write data: \n");
    for (d = 0; d < op.len_; d++){
      printf("%02X ", *tmp);
      tmp++;

    }
#endif
    // WMB();
    write->own_type =
        SIMBRICKS_PROTO_PCIE_D2H_MSG_WRITE | SIMBRICKS_PROTO_PCIE_D2H_OWN_HOST;
  } else {
    volatile struct SimbricksProtoPcieD2HRead *read = &msg->read;
    if (dintro_.h2d_elen <
        sizeof(struct SimbricksProtoPcieH2DReadcomp) + op.len_) {
      fprintf(stderr,
              "issue_dma: write too big (%zu), can only fit up "
              "to (%zu)\n",
              op.len_,
              dintro_.h2d_elen - sizeof(struct SimbricksProtoPcieH2DReadcomp));
      abort();
    }

    read->req_id = (uintptr_t)&op;
    read->offset = op.dma_addr_;
    read->len = op.len_;
    // WMB();
    read->own_type =
        SIMBRICKS_PROTO_PCIE_D2H_MSG_READ | SIMBRICKS_PROTO_PCIE_D2H_OWN_HOST;
  }
}

void Runner::MsiIssue(uint8_t vec) {
  volatile union SimbricksProtoPcieD2H *msg = D2HAlloc();
#ifdef DEBUG_NICBM
  printf("nicbm: issue MSI interrupt vec %u\n", vec);
#endif
  volatile struct SimbricksProtoPcieD2HInterrupt *intr = &msg->interrupt;
  intr->vector = vec;
  intr->inttype = SIMBRICKS_PROTO_PCIE_INT_MSI;

  // WMB();
  intr->own_type = SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT |
                   SIMBRICKS_PROTO_PCIE_D2H_OWN_HOST;
}

void Runner::MsiXIssue(uint8_t vec) {
  volatile union SimbricksProtoPcieD2H *msg = D2HAlloc();
#ifdef DEBUG_NICBM
  printf("nicbm: issue MSI-X interrupt vec %u\n", vec);
#endif
  volatile struct SimbricksProtoPcieD2HInterrupt *intr = &msg->interrupt;
  intr->vector = vec;
  intr->inttype = SIMBRICKS_PROTO_PCIE_INT_MSIX;

  // WMB();
  intr->own_type = SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT |
                   SIMBRICKS_PROTO_PCIE_D2H_OWN_HOST;
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
  printf("nicbm: read(off=0x%lx, len=%u, val=0x%lx)\n", read->offset, read->len,
         dbg_val);
#endif

  // WMB();
  rc->own_type =
      SIMBRICKS_PROTO_PCIE_D2H_MSG_READCOMP | SIMBRICKS_PROTO_PCIE_D2H_OWN_HOST;
}

void Runner::H2DWrite(volatile struct SimbricksProtoPcieH2DWrite *write) {
  volatile union SimbricksProtoPcieD2H *msg;
  volatile struct SimbricksProtoPcieD2HWritecomp *wc;

  msg = D2HAlloc();
  wc = &msg->writecomp;

#ifdef DEBUG_NICBM
  uint64_t dbg_val = 0;
  memcpy(&dbg_val, (const void *)write->data, write->len <= 8 ? write->len : 8);
  printf("nicbm: write(off=0x%lx, len=%u, val=0x%lx)\n", write->offset,
         write->len, dbg_val);
#endif
  dev_.RegWrite(write->bar, write->offset, (void *)write->data, write->len);
  wc->req_id = write->req_id;

  // WMB();
  wc->own_type = SIMBRICKS_PROTO_PCIE_D2H_MSG_WRITECOMP |
                 SIMBRICKS_PROTO_PCIE_D2H_OWN_HOST;
}

void Runner::H2DReadcomp(volatile struct SimbricksProtoPcieH2DReadcomp *rc) {
  DMAOp *op = (DMAOp *)(uintptr_t)rc->req_id;

#ifdef DEBUG_NICBM
  printf("nicbm: completed dma read op %p addr %lx len %zu\n", op, op->dma_addr_,
         op->len_);
#endif

  memcpy(op->data_, (void *)rc->data, op->len_);
  dev_.DmaComplete(*op);

  dma_pending_--;
  DmaTrigger();
}

void Runner::H2DWritecomp(volatile struct SimbricksProtoPcieH2DWritecomp *wc) {
  DMAOp *op = (DMAOp *)(uintptr_t)wc->req_id;

#ifdef DEBUG_NICBM
  printf("nicbm: completed dma write op %p addr %lx len %zu\n", op,
         op->dma_addr_, op->len_);
#endif

  dev_.DmaComplete(*op);

  dma_pending_--;
  DmaTrigger();
}

void Runner::H2DDevctrl(volatile struct SimbricksProtoPcieH2DDevctrl *dc) {
  dev_.DevctrlUpdate(*(struct SimbricksProtoPcieH2DDevctrl *)dc);
}

void Runner::EthRecv(volatile struct SimbricksProtoNetN2DRecv *recv) {
#ifdef DEBUG_NICBM
  printf("nicbm: eth rx: port %u len %u\n", recv->port, recv->len);
#endif

  dev_.EthRx(recv->port, (void *)recv->data, recv->len);
}

void Runner::EthSend(const void *data, size_t len) {
#ifdef DEBUG_NICBM
  printf("nicbm: eth tx: len %zu\n", len);
#endif

  volatile union SimbricksProtoNetD2N *msg = D2NAlloc();
  volatile struct SimbricksProtoNetD2NSend *send = &msg->send;
  send->port = 0;  // single port
  send->len = len;
  memcpy((void *)send->data, data, len);
  send->own_type =
      SIMBRICKS_PROTO_NET_D2N_MSG_SEND | SIMBRICKS_PROTO_NET_D2N_OWN_NET;
}

void Runner::PollH2D() {
  volatile union SimbricksProtoPcieH2D *msg =
      SimbricksNicIfH2DPoll(&nicif_, main_time);
  uint8_t type;

#ifdef STAT_NICBM
  h2d_poll_total += 1;
  if (stat_flag){
    s_h2d_poll_total += 1;
  }
#endif

  if (msg == NULL)
    return;

#ifdef STAT_NICBM
  h2d_poll_suc += 1;
  if (stat_flag){
    s_h2d_poll_suc += 1;
  }
#endif

  type = msg->dummy.own_type & SIMBRICKS_PROTO_PCIE_H2D_MSG_MASK;
  switch (type) {
    case SIMBRICKS_PROTO_PCIE_H2D_MSG_READ:
      H2DRead(&msg->read);
      break;

    case SIMBRICKS_PROTO_PCIE_H2D_MSG_WRITE:
      H2DWrite(&msg->write);
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

    case SIMBRICKS_PROTO_PCIE_H2D_MSG_SYNC:
#ifdef STAT_NICBM
      h2d_poll_sync += 1;
      if (stat_flag){
        s_h2d_poll_sync += 1;
      }
#endif
      break;

    default:
      fprintf(stderr, "poll_h2d: unsupported type=%u\n", type);
  }

  SimbricksNicIfH2DDone(&nicif_, msg);
  SimbricksNicIfH2DNext(&nicif_);
}

void Runner::PollN2D() {
  volatile union SimbricksProtoNetN2D *msg =
      SimbricksNicIfN2DPoll(&nicif_, main_time);
  uint8_t t;

#ifdef STAT_NICBM
  n2d_poll_total += 1;
  if (stat_flag){
    s_n2d_poll_total += 1;
  }
#endif

  if (msg == NULL)
    return;

#ifdef STAT_NICBM
  n2d_poll_suc += 1;
  if (stat_flag){
    s_n2d_poll_suc += 1;
  }
#endif

  t = msg->dummy.own_type & SIMBRICKS_PROTO_NET_N2D_MSG_MASK;
  switch (t) {
    case SIMBRICKS_PROTO_NET_N2D_MSG_RECV:
      EthRecv(&msg->recv);
      break;

    case SIMBRICKS_PROTO_NET_N2D_MSG_SYNC:
#ifdef STAT_NICBM
      n2d_poll_sync += 1;
      if (stat_flag){
        s_n2d_poll_sync += 1;
      }
#endif    
      break;

    default:
      fprintf(stderr, "poll_n2d: unsupported type=%u", t);
  }

  SimbricksNicIfN2DDone(&nicif_, msg);
  SimbricksNicIfN2DNext(&nicif_);
}

uint64_t Runner::TimePs() const {
  return main_time;
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
  if (ev->time_ > main_time)
    return;

  events_.erase(it);
  dev_.Timed(*ev);
}

Runner::Runner(Device &dev) : dev_(dev), events_(EventCmp()) {
  // mac_addr = lrand48() & ~(3ULL << 46);
  dma_pending_ = 0;

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

  std::cerr << std::hex << mac_addr_ << std::endl;
}

int Runner::RunMain(int argc, char *argv[]) {
  uint64_t next_ts;
  uint64_t max_step = 10000;
  uint64_t sync_period = 100 * 1000ULL;
  uint64_t pci_latency = 500 * 1000ULL;
  uint64_t eth_latency = 500 * 1000ULL;
  int sync_mode = SIMBRICKS_PROTO_SYNC_SIMBRICKS;

  if (argc < 4 || argc > 9) {
    fprintf(stderr,
            "Usage: corundum_bm PCI-SOCKET ETH-SOCKET "
            "SHM [SYNC-MODE] [START-TICK] [SYNC-PERIOD] [PCI-LATENCY] "
            "[ETH-LATENCY]\n");
    return EXIT_FAILURE;
  }
  if (argc >= 5)
    sync_mode = strtol(argv[4], NULL, 0);
  if (argc >= 6)
    main_time = strtoull(argv[5], NULL, 0);
  if (argc >= 7)
    sync_period = strtoull(argv[6], NULL, 0) * 1000ULL;
  if (argc >= 8)
    pci_latency = strtoull(argv[7], NULL, 0) * 1000ULL;
  if (argc >= 9)
    eth_latency = strtoull(argv[8], NULL, 0) * 1000ULL;

  signal(SIGINT, sigint_handler);
  signal(SIGUSR1, sigusr1_handler);
#ifdef STAT_NICBM
  signal(SIGUSR2, sigusr2_handler);
#endif

  memset(&dintro_, 0, sizeof(dintro_));
  dev_.SetupIntro(dintro_);

  struct SimbricksNicIfParams nsparams;
  nsparams.sync_pci = 1;
  nsparams.sync_eth = 1;
  nsparams.pci_socket_path = argv[1];
  nsparams.eth_socket_path = argv[2];
  nsparams.shm_path = argv[3];
  nsparams.pci_latency = pci_latency;
  nsparams.eth_latency = eth_latency;
  nsparams.sync_delay = sync_period;
  assert(sync_mode == SIMBRICKS_PROTO_SYNC_SIMBRICKS ||
         sync_mode == SIMBRICKS_PROTO_SYNC_BARRIER);
  nsparams.sync_mode = sync_mode;

  if (SimbricksNicIfInit(&nicif_, &nsparams, &dintro_)) {
    return EXIT_FAILURE;
  }
  fprintf(stderr, "sync_pci=%d sync_eth=%d\n", nsparams.sync_pci,
          nsparams.sync_eth);

  bool is_sync = nsparams.sync_pci || nsparams.sync_eth;

  while (!exiting) {
    while (SimbricksNicIfSync(&nicif_, main_time)) {
      fprintf(stderr, "warn: SimbricksNicIfSync failed (t=%lu)\n", main_time);
    }
    SimbricksNicIfAdvanceEpoch(&nicif_, main_time);

    do {
      PollH2D();
      PollN2D();
      EventTrigger();

      if (is_sync) {
        next_ts = SimbricksNicIfNextTimestamp(&nicif_);
        if (next_ts > main_time + max_step)
          next_ts = main_time + max_step;
      } else {
        next_ts = main_time + max_step;
      }

      uint64_t ev_ts;
      if (EventNext(ev_ts) && ev_ts < next_ts)
        next_ts = ev_ts;
    } while (next_ts <= main_time && !exiting);
    main_time = SimbricksNicIfAdvanceTime(&nicif_, next_ts);
  }

  fprintf(stderr, "exit main_time: %lu\n", main_time);
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
          "s_h2d_poll_total", s_h2d_poll_total, "s_h2d_poll_suc", s_h2d_poll_suc,
          (double)s_h2d_poll_suc / s_h2d_poll_total);

  fprintf(stderr, "%65s: %22lu  sync_rate: %f\n", "s_h2d_poll_sync",
          s_h2d_poll_sync, (double)s_h2d_poll_sync / s_h2d_poll_suc);

  fprintf(stderr, "%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n",
          "s_n2d_poll_total", s_n2d_poll_total, "s_n2d_poll_suc", s_n2d_poll_suc,
          (double)s_n2d_poll_suc / s_n2d_poll_total);

  fprintf(stderr, "%65s: %22lu  sync_rate: %f\n", "s_n2d_poll_sync",
          s_n2d_poll_sync, (double)s_n2d_poll_sync / s_n2d_poll_suc);

  fprintf(
      stderr, "%20s: %22lu %20s: %22lu  sync_rate: %f\n", "s_recv_total",
      s_h2d_poll_suc + s_n2d_poll_suc, "s_recv_sync", s_h2d_poll_sync + s_n2d_poll_sync,
      (double)(s_h2d_poll_sync + s_n2d_poll_sync) / (s_h2d_poll_suc + s_n2d_poll_suc));
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

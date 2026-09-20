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

#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cassert>
#include <cstdarg>
#include <ctime>
#include <iostream>
#include <vector>

#include <simbricks/nicbm/nicbm.h>

extern "C" {
#include <simbricks/base/proto.h>
}

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

void Runner::PrintBaseIfInfo() {
  sim_log::LogError("net_in_timestamp = %lu\n", nicif_.net.base.in_timestamp);
  sim_log::LogError("net_out_timestamp = %lu\n", nicif_.net.base.out_timestamp);

  sim_log::LogError("pci_in_timestamp = %lu\n", nicif_.pcie.base.in_timestamp);
  sim_log::LogError("pci_out_timestamp = %lu\n", nicif_.pcie.base.out_timestamp);
}

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
  for (Runner *r : runners) {
    sim_log::LogError("[Runner %p] main_time = %lu\n", r, r->TimePs());
    r->PrintBaseIfInfo();
    r->FlushDebugLog();
  }
}

#ifdef STAT_NICBM
static void sigusr2_handler(int dummy) {
  stat_flag = 1;
}
#endif

volatile union SimbricksProtoPcieD2H *Runner::D2HAlloc() {
  if (SimbricksBaseIfInTerminated(&nicif_.pcie.base)) {
    sim_log::LogError("Runner::D2HAlloc: peer already terminated\n");
    sim_log::FlushLog();
    abort();
  }

  volatile union SimbricksProtoPcieD2H *msg;
  bool first = true;
  while ((msg = SimbricksPcieIfD2HOutAlloc(&nicif_.pcie, main_time_)) == NULL) {
    if (first) {
      sim_log::LogError("D2HAlloc: warning waiting for entry (%zu)\n", nicif_.pcie.base.out_pos);
      first = false;
    }
    YieldPoll();
  }

  if (!first)
    sim_log::LogError("D2HAlloc: entry successfully allocated\n");

  return msg;
}

volatile union SimbricksProtoNetMsg *Runner::D2NAlloc() {
  volatile union SimbricksProtoNetMsg *msg;
  bool first = true;
  while ((msg = SimbricksNetIfOutAlloc(&nicif_.net, main_time_)) == NULL) {
    if (first) {
      sim_log::LogError("D2NAlloc: warning waiting for entry (%zu)\n", nicif_.pcie.base.out_pos);
      first = false;
    }
    YieldPoll();
  }

  if (!first)
    sim_log::LogError("D2NAlloc: entry successfully allocated\n");

  return msg;
}

DebugLog *DebugLog::Open(const char *path) {
  // the path may be a FIFO whose reader (the trace collector) is up already
  FILE *f = fopen(path, "w");
  if (!f) {
    perror("DebugLog: opening debug log failed");
    return nullptr;
  }
  setvbuf(f, nullptr, _IOFBF, 1 << 20);
  fprintf(f, "# simbricks-debug nicbm 1\n");
  return new DebugLog(f);
}

DebugLog::~DebugLog() {
  fclose(file_);
}

void DebugLog::RunnerInfo(unsigned idx, const char *pci_sock, const char *eth_sock,
                          uint64_t start_ts, uint64_t mac) {
  fprintf(file_, "# runner %u pci=%s eth=%s start=%lu mac=%lx\n", idx, pci_sock, eth_sock,
          start_ts, mac);
  fflush(file_);
}

void DebugLog::Emit(uint64_t ts, unsigned runner, const char *kind, const char *fmt, ...) {
  fprintf(file_, "%lu %u %s ", ts, runner, kind);
  va_list ap;
  va_start(ap, fmt);
  vfprintf(file_, fmt, ap);
  va_end(ap);
  fputc('\n', file_);
}

void DebugLog::Flush() {
  fflush(file_);
}

void Runner::SetDebugLog(DebugLog *log, unsigned idx, bool owned) {
  debug_log_ = log;
  debug_log_owned_ = owned;
  runner_idx_ = idx;
}

void Runner::Debug(const char *kind, const char *fmt, ...) {
  if (!debug_log_)
    return;
  char buf[512];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof(buf), fmt, ap);
  va_end(ap);
  debug_log_->Emit(main_time_, runner_idx_, kind, "%s", buf);
}

void Runner::IssueDma(DMAOp &op) {
  if (dma_pending_ < DMA_MAX_PENDING) {
    // can directly issue
    DmaDo(op);
  } else {
    if (debug_log_)
      debug_log_->Emit(main_time_, runner_idx_, "dma_queued", "0x%lx 0x%lx %zu",
                       (uintptr_t)&op, op.dma_addr_, op.len_);
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
  if (debug_log_)
    debug_log_->Emit(main_time_, runner_idx_, op.write_ ? "d2h_write" : "d2h_read",
                     "0x%lx 0x%lx %zu", (uintptr_t)&op, op.dma_addr_, op.len_);
  size_t maxlen = SimbricksBaseIfOutMsgLen(&nicif_.pcie.base);
  if (op.write_) {
    volatile struct SimbricksProtoPcieD2HWrite *write = &msg->write;
    if (maxlen < sizeof(*write) + op.len_) {
      sim_log::LogError(
          "issue_dma: write too big (%zu), can only fit up "
          "to (%zu)\n",
          op.len_, maxlen - sizeof(*write));
      sim_log::FlushLog();
      abort();
    }

    write->req_id = (uintptr_t)&op;
    write->offset = op.dma_addr_;
    write->len = op.len_;
    memcpy((void *)write->data, (void *)op.data_, op.len_);
    SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_WRITE);
  } else {
    volatile struct SimbricksProtoPcieD2HRead *read = &msg->read;
    if (maxlen < sizeof(struct SimbricksProtoPcieH2DReadcomp) + op.len_) {
      sim_log::LogError("issue_dma: read too big (%zu), can only fit up to (%zu)\n", op.len_,
                        maxlen - sizeof(struct SimbricksProtoPcieH2DReadcomp));
      sim_log::FlushLog();
      abort();
    }

    read->req_id = (uintptr_t)&op;
    read->offset = op.dma_addr_;
    read->len = op.len_;
    SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_READ);
  }
}

void Runner::MsiIssue(uint8_t vec) {
  if (SimbricksBaseIfInTerminated(&nicif_.pcie.base))
    return;

  volatile union SimbricksProtoPcieD2H *msg = D2HAlloc();
  if (debug_log_)
    debug_log_->Emit(main_time_, runner_idx_, "d2h_intr", "msi %u", vec);
  volatile struct SimbricksProtoPcieD2HInterrupt *intr = &msg->interrupt;
  intr->vector = vec;
  intr->inttype = SIMBRICKS_PROTO_PCIE_INT_MSI;

  SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT);
}

void Runner::MsiXIssue(uint8_t vec) {
  if (SimbricksBaseIfInTerminated(&nicif_.pcie.base))
    return;

  volatile union SimbricksProtoPcieD2H *msg = D2HAlloc();
  if (debug_log_)
    debug_log_->Emit(main_time_, runner_idx_, "d2h_intr", "msix %u", vec);
  volatile struct SimbricksProtoPcieD2HInterrupt *intr = &msg->interrupt;
  intr->vector = vec;
  intr->inttype = SIMBRICKS_PROTO_PCIE_INT_MSIX;

  SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT);
}

void Runner::IntXIssue(bool level) {
  if (SimbricksBaseIfInTerminated(&nicif_.pcie.base))
    return;

  volatile union SimbricksProtoPcieD2H *msg = D2HAlloc();
  if (debug_log_)
    debug_log_->Emit(main_time_, runner_idx_, "d2h_intr", "%s 0", level ? "intx_hi" : "intx_lo");
  volatile struct SimbricksProtoPcieD2HInterrupt *intr = &msg->interrupt;
  intr->vector = 0;
  intr->inttype = (level ? SIMBRICKS_PROTO_PCIE_INT_LEGACY_HI : SIMBRICKS_PROTO_PCIE_INT_LEGACY_LO);

  SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_INTERRUPT);
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

  if (debug_log_)
    debug_log_->Emit(main_time_, runner_idx_, "h2d_read", "%lu %u 0x%lx %u %lu",
                     (uint64_t)read->req_id, (unsigned)read->bar, (uint64_t)read->offset,
                     (unsigned)read->len, nicif_.pcie.base.in_timestamp);
  dev_.RegRead(read->bar, read->offset, (void *)rc->data, read->len);
  rc->req_id = read->req_id;
  if (debug_log_)
    debug_log_->Emit(main_time_, runner_idx_, "d2h_readcomp", "%lu", (uint64_t)rc->req_id);
  SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_READCOMP);
}

void Runner::H2DWrite(volatile struct SimbricksProtoPcieH2DWrite *write, bool posted) {
  volatile union SimbricksProtoPcieD2H *msg;
  volatile struct SimbricksProtoPcieD2HWritecomp *wc;
  if (debug_log_)
    debug_log_->Emit(main_time_, runner_idx_, "h2d_write", "%lu %u 0x%lx %u %u %lu",
                     (uint64_t)write->req_id, (unsigned)write->bar, (uint64_t)write->offset,
                     (unsigned)write->len, posted ? 1 : 0, nicif_.pcie.base.in_timestamp);
  dev_.RegWrite(write->bar, write->offset, (void *)write->data, write->len);
  if (!posted) {
    msg = D2HAlloc();
    wc = &msg->writecomp;
    wc->req_id = write->req_id;
    if (debug_log_)
      debug_log_->Emit(main_time_, runner_idx_, "d2h_writecomp", "%lu", (uint64_t)wc->req_id);
    SimbricksPcieIfD2HOutSend(&nicif_.pcie, msg, SIMBRICKS_PROTO_PCIE_D2H_MSG_WRITECOMP);
  }
}

void Runner::H2DReadcomp(volatile struct SimbricksProtoPcieH2DReadcomp *rc) {
  DMAOp *op = (DMAOp *)(uintptr_t)rc->req_id;
  if (debug_log_)
    debug_log_->Emit(main_time_, runner_idx_, "h2d_readcomp", "0x%lx %lu", (uint64_t)rc->req_id,
                     nicif_.pcie.base.in_timestamp);
  memcpy(op->data_, (void *)rc->data, op->len_);
  dev_.DmaComplete(*op);

  dma_pending_--;
  DmaTrigger();
}

void Runner::H2DWritecomp(volatile struct SimbricksProtoPcieH2DWritecomp *wc) {
  DMAOp *op = (DMAOp *)(uintptr_t)wc->req_id;
  if (debug_log_)
    debug_log_->Emit(main_time_, runner_idx_, "h2d_writecomp", "0x%lx %lu", (uint64_t)wc->req_id,
                     nicif_.pcie.base.in_timestamp);
  dev_.DmaComplete(*op);

  dma_pending_--;
  DmaTrigger();
}

void Runner::H2DDevctrl(volatile struct SimbricksProtoPcieH2DDevctrl *dc) {
  if (debug_log_)
    debug_log_->Emit(main_time_, runner_idx_, "h2d_devctrl", "0x%lx %lu", (uint64_t)dc->flags,
                     nicif_.pcie.base.in_timestamp);
  dev_.DevctrlUpdate(*(struct SimbricksProtoPcieH2DDevctrl *)dc);
}

void Runner::EthRecv(volatile struct SimbricksProtoNetMsgPacket *packet) {
  if (debug_log_)
    debug_log_->Emit(main_time_, runner_idx_, "eth_rx", "%u %u %lu", (unsigned)packet->port,
                     (unsigned)packet->len, nicif_.net.base.in_timestamp);
  dev_.EthRx(packet->port, (void *)packet->data, packet->len);
}

void Runner::EthSend(const void *data, size_t len) {
  if (debug_log_)
    debug_log_->Emit(main_time_, runner_idx_, "eth_tx", "%zu", len);
  volatile union SimbricksProtoNetMsg *msg = D2NAlloc();
  volatile struct SimbricksProtoNetMsgPacket *packet = &msg->packet;
  packet->port = 0;  // single port
  packet->len = len;
  memcpy((void *)packet->data, data, len);
  SimbricksNetIfOutSend(&nicif_.net, msg, SIMBRICKS_PROTO_NET_MSG_PACKET);
}

void Runner::PollH2D() {
  volatile union SimbricksProtoPcieH2D *msg = SimbricksPcieIfH2DInPoll(&nicif_.pcie, main_time_);
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
      sim_log::LogError("poll_h2d: peer terminated\n");
      break;

    default:
      sim_log::LogError("poll_h2d: unsupported type=%u\n", type);
  }

  SimbricksPcieIfH2DInDone(&nicif_.pcie, msg);
}

void Runner::PollN2D() {
  volatile union SimbricksProtoNetMsg *msg = SimbricksNetIfInPoll(&nicif_.net, main_time_);
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
      sim_log::LogError("poll_n2d: unsupported type=%u", t);
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
  return SimbricksNicIfInit(&nicif_, shmPath_, &netParams_, &pcieParams_, &dintro_);
}

Runner::Runner(Device &dev)
    : main_time_(0),
      dev_(dev),
      events_(EventCmp()),
      pcieAdapterParams_(nullptr),
      netAdapterParams_(nullptr) {
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

Runner::~Runner() {
  SimbricksParametersFree(pcieAdapterParams_);
  SimbricksParametersFree(netAdapterParams_);
}

static enum SimbricksBaseIfSyncMode GetSyncMode(bool sync) {
  if (sync)
    return kSimbricksBaseIfSyncRequired;
  else
    return kSimbricksBaseIfSyncDisabled;
}

int Runner::ParseArgs(int argc, char *argv[]) {
  if (pcieAdapterParams_ || netAdapterParams_) {
    sim_log::LogError("Arguments are already parsed\n");
    return -1;
  }
  if (argc >= 2 && !strncmp(argv[1], "--debug-log=", 12)) {
    if (!debug_log_) {
      DebugLog *log = DebugLog::Open(argv[1] + 12);
      if (!log)
        return -1;
      SetDebugLog(log, 0, true);
    }
    argv[1] = argv[0];
    argv++;
    argc--;
  }
  if (argc < 3 || argc > 6) {
    sim_log::LogError(
        "Usage: %s [--debug-log=PATH] PCI-PARAMS ETH-PARAMS "
        "[START-TICK] [MAC-ADDR] [LOG-FILE-PATH]\n",
        argv[0]);
    return -1;
  }
  if (argc >= 4)
    main_time_ = strtoull(argv[3], NULL, 0);
  if (argc >= 5)
    mac_addr_ = strtoull(argv[4], NULL, 16);
  if (argc >= 6)
    log_ = sim_log::Log::createLog(argv[5]);

  pcieAdapterParams_ = SimbricksParametersParse(argv[1]);
  netAdapterParams_ = SimbricksParametersParse(argv[2]);

  if (!(pcieAdapterParams_ && netAdapterParams_)) {
    sim_log::LogError("Failed to parse PCIe or Ethernet parameters\n");
    return -1;
  }

  if (!(pcieAdapterParams_->listen && netAdapterParams_->listen)) {
    sim_log::LogError("Nicbm currently only supports listening adapters\n");
    return -1;
  }

  pcieParams_.sock_path = pcieAdapterParams_->socket_path;
  netParams_.sock_path = netAdapterParams_->socket_path;
  // Since the NIC interface uses a single shared memory pool for both pcie and
  // net interface, we just take the shm path provided for the pcie adapter here
  shmPath_ = pcieAdapterParams_->shm_path;

  pcieParams_.sync_mode = GetSyncMode(pcieAdapterParams_->sync);
  netParams_.sync_mode = GetSyncMode(netAdapterParams_->sync);

  if (pcieAdapterParams_->sync_interval_set)
    pcieParams_.sync_interval = pcieAdapterParams_->sync_interval;
  if (netAdapterParams_->sync_interval_set)
    netParams_.sync_interval = netAdapterParams_->sync_interval;
  if (pcieAdapterParams_->link_latency_set)
    pcieParams_.link_latency = pcieAdapterParams_->link_latency;
  if (netAdapterParams_->link_latency_set)
    netParams_.link_latency = netAdapterParams_->link_latency;

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

  if (debug_log_)
    debug_log_->RunnerInfo(runner_idx_, pcieParams_.sock_path, netParams_.sock_path, main_time_,
                           mac_addr_);
  sim_log::LogInfo(log_, "mac_addr=%lx\n", mac_addr_);
  sim_log::LogInfo(log_, "sync_pci=%d sync_eth=%d\n", sync_pcie, sync_net);

  bool is_sync = sync_pcie || sync_net;

  while (!exiting) {
    while (SimbricksNicIfSync(&nicif_, main_time_)) {
      sim_log::LogWarn("SimbricksNicIfSync failed (t=%lu)\n", main_time_);
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

  sim_log::LogInfo("exit main_time: %lu\n", main_time_);
#ifdef STAT_NICBM
  sim_log::LogInfo("%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n", "h2d_poll_total", h2d_poll_total,
                   "h2d_poll_suc", h2d_poll_suc, (double)h2d_poll_suc / h2d_poll_total);

  sim_log::LogInfo("%65s: %22lu  sync_rate: %f\n", "h2d_poll_sync", h2d_poll_sync,
                   (double)h2d_poll_sync / h2d_poll_suc);

  sim_log::LogInfo("%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n", "n2d_poll_total", n2d_poll_total,
                   "n2d_poll_suc", n2d_poll_suc, (double)n2d_poll_suc / n2d_poll_total);

  sim_log::LogInfo("%65s: %22lu  sync_rate: %f\n", "n2d_poll_sync", n2d_poll_sync,
                   (double)n2d_poll_sync / n2d_poll_suc);

  sim_log::LogInfo("%20s: %22lu %20s: %22lu  sync_rate: %f\n", "recv_total",
                   h2d_poll_suc + n2d_poll_suc, "recv_sync", h2d_poll_sync + n2d_poll_sync,
                   (double)(h2d_poll_sync + n2d_poll_sync) / (h2d_poll_suc + n2d_poll_suc));

  sim_log::LogInfo("%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n", "s_h2d_poll_total",
                   s_h2d_poll_total, "s_h2d_poll_suc", s_h2d_poll_suc,
                   (double)s_h2d_poll_suc / s_h2d_poll_total);

  sim_log::LogInfo("%65s: %22lu  sync_rate: %f\n", "s_h2d_poll_sync", s_h2d_poll_sync,
                   (double)s_h2d_poll_sync / s_h2d_poll_suc);

  sim_log::LogInfo("%20s: %22lu %20s: %22lu  poll_suc_rate: %f\n", "s_n2d_poll_total",
                   s_n2d_poll_total, "s_n2d_poll_suc", s_n2d_poll_suc,
                   (double)s_n2d_poll_suc / s_n2d_poll_total);

  sim_log::LogInfo("%65s: %22lu  sync_rate: %f\n", "s_n2d_poll_sync", s_n2d_poll_sync,
                   (double)s_n2d_poll_sync / s_n2d_poll_suc);

  sim_log::LogInfo("%20s: %22lu %20s: %22lu  sync_rate: %f\n", "s_recv_total",
                   s_h2d_poll_suc + s_n2d_poll_suc, "s_recv_sync",
                   s_h2d_poll_sync + s_n2d_poll_sync,
                   (double)(s_h2d_poll_sync + s_n2d_poll_sync) / (s_h2d_poll_suc + s_n2d_poll_suc));
#endif

  SimbricksNicIfCleanup(&nicif_);
  if (debug_log_) {
    debug_log_->Flush();
    if (debug_log_owned_)
      delete debug_log_;
    debug_log_ = nullptr;
  }
  return 0;
}

void Runner::Device::Timed(TimedEvent &te) {
}

void Runner::Device::DevctrlUpdate(struct SimbricksProtoPcieH2DDevctrl &devctrl) {
  int_intx_en_ = devctrl.flags & SIMBRICKS_PROTO_PCIE_CTRL_INTX_EN;
  int_msi_en_ = devctrl.flags & SIMBRICKS_PROTO_PCIE_CTRL_MSI_EN;
  int_msix_en_ = devctrl.flags & SIMBRICKS_PROTO_PCIE_CTRL_MSIX_EN;
}

}  // namespace nicbm

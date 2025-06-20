/*
 * Copyright 2025 Max Planck Institute for Software Systems, and
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

#include <unistd.h>

#include <cassert>
#include <climits>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>

#include <simbricks/base/cxxatomicfix.h>
extern "C" {
#include <simbricks/mem/if.h>
#include <simbricks/parser/parser.h>
};

//#define INTERCONN_DEBUG

struct Pending;

struct Port {
  struct SimbricksMemIf memif;
  std::string url;

  Port(std::string url_) : url(url_) {
    SimbricksMemIfDefaultParams(&memif.base.params);
  }

  virtual ~Port() = default;

  void PrepareIntros(struct SimBricksBaseIfEstablishData *est) {
    // Relies on dummy intros
    assert(sizeof(SimbricksProtoMemMemIntro) ==
           sizeof(SimbricksProtoMemHostIntro));
    est->rx_intro = new SimbricksProtoMemMemIntro;
    est->rx_intro_len = sizeof(SimbricksProtoMemMemIntro);
    est->tx_intro = new SimbricksProtoMemMemIntro;
    est->tx_intro_len = sizeof(SimbricksProtoMemMemIntro);
  }

  void Sync(uint64_t cur_ts) {
    while (SimbricksBaseIfOutSync(&memif.base, cur_ts)) {
    }
  }

  bool IsSync() {
    return SimbricksBaseIfSyncEnabled(&memif.base);
  }

  uint64_t NextTimestamp() {
    return SimbricksBaseIfInTimestamp(&memif.base);
  }

  virtual void Poll() = 0;
};

struct Device: public Port {
  std::string name;
  Device(std::string name_, std::string url_) : Port(url_), name(name_) {
  }
  virtual void Poll() override;
  void Read(Pending *p);
  void Write(Pending *p, const void *data, bool posted);
};

struct Host: public Port {
  Host(std::string url_) : Port(url_) { }
  virtual void Poll() override;
  void CompletePendingR(Pending *p, const void *data);
  void CompletePendingW(Pending *p);
};

struct Pending {
  Host *host;
  bool write;
  uint64_t req_id;
  uint64_t addr;
  size_t len;
};

struct TableEntry {
  uint64_t vaddr_start;
  uint64_t vaddr_end;
  uint64_t phys_start;
  Device *dev;
};

std::vector<struct TableEntry> map_table;
static uint64_t cur_ts = 0;
static int exiting = 0;
struct SimbricksBaseIfSHMPool pool;

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
  fprintf(stderr, "main_time = %lu\n", cur_ts);
}

static bool ConnectAll(std::vector<Port*> &ports, const char *pool_path) {
  size_t n = ports.size();
  struct SimBricksBaseIfEstablishData ests[n];
  const char *urls[n];
  for (size_t i = 0; i < n; i++) {
    ests[i].base_if = &ports[i]->memif.base;
    ports[i]->PrepareIntros(&ests[i]);
    urls[i] = ports[i]->url.c_str();
  }

  fprintf(stderr, "Connecting all %zu...\n", n);
  int ret = SimbricksParametersEstablish(ests, urls, n, &pool, pool_path);
  fprintf(stderr, "Connected.\n");
  return ret == 0;
}

// Will look up the device to access at this address, and re-map the address
static Device *Lookup(uint64_t &addr, uint64_t len) {
  for (auto te: map_table) {
    if (te.vaddr_start <= addr && te.vaddr_end > addr) {
      if (addr + len > te.vaddr_end) {
        fprintf(stderr, "Lookup: End of accessed range (%lx + %lx) is not in "
                        "same range as start. Unsupported.\n",
                addr, len);
        abort();
      }
      addr = te.phys_start + (addr - te.vaddr_start);
      return te.dev;
    }
  }

  throw "No matching device found.";
}

void Device::Poll() {
  volatile union SimbricksProtoMemM2H *msg = SimbricksMemIfM2HInPoll(&memif, cur_ts);
  if (msg == nullptr)
      return;

#ifdef INTERCONN_DEBUG
  fprintf(stderr, "Device %p: Polled\n", this);
#endif

  uint8_t type = SimbricksMemIfM2HInType(&memif, msg);
  switch (type) {
    case SIMBRICKS_PROTO_MEM_M2H_MSG_READCOMP: {
      volatile struct SimbricksProtoMemM2HReadcomp &readcomp = msg->readcomp;
      Pending *pending = (Pending *) readcomp.req_id;

#ifdef INTERCONN_DEBUG
      fprintf(stderr, "Device %p: READCOMP %p->%lu\n", this, pending, pending->req_id);
#endif

      pending->host->CompletePendingR(pending, (void *) readcomp.data);
      break;
  }
  case SIMBRICKS_PROTO_MEM_M2H_MSG_WRITECOMP: {
    volatile struct SimbricksProtoMemM2HWritecomp &writecomp = msg->writecomp;
    Pending *pending = (Pending *) writecomp.req_id;

#ifdef INTERCONN_DEBUG
      fprintf(stderr, "Device %p: WRITECOMP %p->%lu\n", this, pending, pending->req_id);
#endif

    pending->host->CompletePendingW(pending);
    break;
  }
  case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
    break;
  default:
    fprintf(stderr, "Device::Poll: unsupported type=%d", type);
    abort();
  }

  SimbricksMemIfM2HInDone(&memif, msg);
}

void Host::Poll() {
  volatile union SimbricksProtoMemH2M *msg = SimbricksMemIfH2MInPoll(&memif, cur_ts);
  if (msg == nullptr)
      return;

#ifdef INTERCONN_DEBUG
  fprintf(stderr, "Host %p: Polled\n", this);
#endif

  uint8_t type = SimbricksMemIfH2MInType(&memif, msg);
  switch (type) {
    case SIMBRICKS_PROTO_MEM_H2M_MSG_READ: {
      volatile struct SimbricksProtoMemH2MRead &read = msg->read;

      uint64_t addr = read.addr;
      Device *dev = Lookup(addr, read.len);

      Pending *pending = new Pending;
      pending->write = false;
      pending->host = this;
      pending->addr = addr;
      pending->len = read.len;
      pending->req_id = read.req_id;

#ifdef INTERCONN_DEBUG
      fprintf(stderr, "Host %p: READ id=%lu->%p a=%lx->%lx l=%u\n", this,
              read.req_id, pending, read.addr, addr, read.len);
#endif

      dev->Read(pending);
      break;
    }
    case SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE: /* fallthru */
    case SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE_POSTED: {
      volatile struct SimbricksProtoMemH2MWrite &write = msg->write;

      uint64_t addr = write.addr;
      Device *dev = Lookup(addr, write.len);
      
      Pending *pending = new Pending;
      pending->write = false;
      pending->host = this;
      pending->addr = addr;
      pending->len = write.len;
      pending->req_id = write.req_id;

#ifdef INTERCONN_DEBUG
      fprintf(stderr, "Host %p: WRITE id=%lu->%p a=%lx->%lx l=%u\n", this,
              write.req_id, pending, write.addr, addr, write.len);
#endif

      dev->Write(pending, (const void *) write.data,
                 type == SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE_POSTED);
      break;
  }
  case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
    break;
  default:
    fprintf(stderr, "Device::Poll: unsupported type=%d", type);
    abort();
  }

  SimbricksMemIfH2MInDone(&memif, msg);
}

void Device::Read(Pending *p) {
  volatile union SimbricksProtoMemH2M *msg = SimbricksMemIfH2MOutAlloc(&memif, cur_ts);
  if (!msg)
    throw "No message buffer available";

  volatile struct SimbricksProtoMemH2MRead *read = &msg->read;
  read->addr = p->addr;
  read->len = p->len;
  read->as_id = 0;
  read->req_id = (uintptr_t) p;
  SimbricksMemIfH2MOutSend(&memif, msg, SIMBRICKS_PROTO_MEM_H2M_MSG_READ);
}

void Device::Write(Pending *p, const void *data, bool posted) {
  volatile union SimbricksProtoMemH2M *msg = SimbricksMemIfH2MOutAlloc(&memif, cur_ts);
  if (!msg)
    throw "No message buffer available";

  volatile struct SimbricksProtoMemH2MWrite *write = &msg->write;
  write->addr = p->addr;
  write->len = p->len;
  write->as_id = 0;
  memcpy((void *) write->data, data, p->len);

  if (!posted) {
    write->req_id = (uintptr_t) p;
    SimbricksMemIfH2MOutSend(&memif, msg, SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE);
  } else {
    write->req_id = 0;
    delete p;
    SimbricksMemIfH2MOutSend(&memif, msg, SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE_POSTED);
  }
}

void Host::CompletePendingR(Pending *p, const void *data) {
  volatile union SimbricksProtoMemM2H *msg = SimbricksMemIfM2HOutAlloc(&memif, cur_ts);
  if (!msg)
    throw "No message buffer available";

  volatile struct SimbricksProtoMemM2HReadcomp *rc = &msg->readcomp;
  rc->req_id = p->req_id;
  memcpy((void *) rc->data, data, p->len);

  delete p;
  SimbricksMemIfM2HOutSend(&memif, msg, SIMBRICKS_PROTO_MEM_M2H_MSG_READCOMP);
}

void Host::CompletePendingW(Pending *p) {
  volatile union SimbricksProtoMemM2H *msg = SimbricksMemIfM2HOutAlloc(&memif, cur_ts);
  if (!msg)
    throw "No message buffer available";

  volatile struct SimbricksProtoMemM2HWritecomp *wc = &msg->writecomp;
  wc->req_id = p->req_id;

  delete p;
  SimbricksMemIfM2HOutSend(&memif, msg, SIMBRICKS_PROTO_MEM_M2H_MSG_WRITECOMP);
}

int main(int argc, char *argv[]) {
  int c;
  int bad_option = 0;

  const char *pool_path = NULL;
  std::unordered_map<std::string, Device *> devices;
  std::vector<Port *> ports;

  // Parse command line argument
  while ((c = getopt(argc, argv, "d:h:p:m:")) != -1 && !bad_option) {
    switch (c) {
      case 'd': {
        std::string arg = optarg;
        size_t eq_pos = arg.find('=');
        if (eq_pos == std::string::npos) {
          perror("No equal sign found when parsing device");
          return EXIT_FAILURE;
        }

        std::string name = arg.substr(0, eq_pos);
        std::string url = arg.substr(eq_pos + 1);

        Device *d = new Device(name, url);
        devices[name] = d;
        ports.push_back(d);

#ifdef INTERCONN_DEBUG
        fprintf(stderr, "Device %p: Added name=%s url=%s\n", d, name.c_str(), url.c_str());
#endif
        break;
      }

      case 'h': {
        Host *h = new Host(optarg);
        ports.push_back(h);
#ifdef INTERCONN_DEBUG
        fprintf(stderr, "Host %p: Added url=%s\n", h, optarg);
#endif
        break;
      }

      case 'p':
        pool_path = optarg;
        break;

      case 'm': {
        char *token;
        char *ctx;
        int idx;
        struct TableEntry ent;

        token = strtok_r(optarg, ",", &ctx);
        idx = 0;
        while (token) {
          switch (idx) {
            case 0:
              ent.vaddr_start = strtoull(token, NULL, 0);
              break;
            case 1:
              ent.vaddr_end = strtoull(token, NULL, 0);
              break;
            case 2:
              ent.phys_start = strtoull(token, NULL, 0);
              break;
            case 3: {
              ent.dev = devices[token];
              break;
            }
            default:
              perror("error parsing map config");
              return EXIT_FAILURE;
          }
          idx++;

          token = strtok_r(NULL, ",", &ctx);
        }
#ifdef INTERCONN_DEBUG
        fprintf(stderr, "Add route: %lx-%lx -> %lx@%p\n", ent.vaddr_start, ent.vaddr_end, ent.phys_start, ent.dev);
#endif
        map_table.push_back(ent);
        break;
      }

      default:
        fprintf(stderr, "unknown option %c\n", c);
        bad_option = 1;
        break;
    }
  }

  if (devices.empty() || map_table.empty() || ports.empty() || bad_option) {
    fprintf(stderr,
            "Usage: interconnect -p POOL-PATH [-d DEV-NAME=DEV-URL ...] "
            "[-h HOST—URL ...] [-m ROUTE ...]\n");
    return EXIT_FAILURE;
  }

  signal(SIGINT, sigint_handler);
  signal(SIGTERM, sigint_handler);
  signal(SIGUSR1, sigusr1_handler);

  if (!ConnectAll(ports, pool_path))
    return EXIT_FAILURE;

  fprintf(stderr, "start polling\n");
  while (!exiting) {
    // Sync all interfaces
    for (auto port : ports)
      port->Sync(cur_ts);

    // Switch packets
    uint64_t min_ts;
    do {
      min_ts = ULLONG_MAX;
      for (auto port : ports) {
        port->Poll();
        if (port->IsSync()) {
          uint64_t ts = port->NextTimestamp();
          min_ts = ts < min_ts ? ts : min_ts;
        }
      }
    } while (!exiting && (min_ts <= cur_ts));

    // Update cur_ts
    if (min_ts < ULLONG_MAX) {
      cur_ts = min_ts;
    }
  }

  return 0;
}

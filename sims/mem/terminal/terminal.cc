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
#include <sstream>
#include <unordered_map>
#include <vector>

#include <simbricks/base/cxxatomicfix.h>
extern "C" {
#include <simbricks/mem/if.h>
#include <simbricks/parser/parser.h>
};

struct SimbricksMemIf memif;
struct SimbricksBaseIfSHMPool pool;
static uint64_t cur_ts = 0;
static int exiting = 0;
static std::stringstream outbuf;

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
  fprintf(stderr, "main_time = %lu\n", cur_ts);
}

static bool Connect(const char *url) {
  SimbricksMemIfDefaultParams(&memif.base.params);
  
  struct SimBricksBaseIfEstablishData est;
  est.base_if = &memif.base;
  assert(sizeof(SimbricksProtoMemMemIntro) ==
           sizeof(SimbricksProtoMemHostIntro));
  est.rx_intro = new SimbricksProtoMemMemIntro;
  est.rx_intro_len = sizeof(SimbricksProtoMemMemIntro);
  est.tx_intro = new SimbricksProtoMemMemIntro;
  est.tx_intro_len = sizeof(SimbricksProtoMemMemIntro);

  int ret = SimbricksParametersEstablish(&est, &url, 1, &pool, nullptr);
  return ret == 0;
}

static uint64_t Read(uint64_t addr, uint16_t len) {
  return 0;
}

static void Write(uint64_t addr, uint16_t len, uint64_t val) {
  if (addr == 0) {
    if ((char) val == '\n') {
      puts(outbuf.str().c_str());
      fflush(stdout);
      outbuf.str("");
    } else {
      outbuf << (char) val;
    }
  }
}

static void Poll() {
  volatile union SimbricksProtoMemH2M *msg = SimbricksMemIfH2MInPoll(&memif, cur_ts);
  if (msg == nullptr)
      return;

  uint8_t type = SimbricksMemIfH2MInType(&memif, msg);
  switch (type) {
    case SIMBRICKS_PROTO_MEM_H2M_MSG_READ: {
      volatile struct SimbricksProtoMemH2MRead &read = msg->read;

      if (read.len > 8)
        throw "Invalid read length";

      uint64_t val = Read(read.addr, read.len);

      volatile union SimbricksProtoMemM2H *omsg = SimbricksMemIfM2HOutAlloc(&memif, cur_ts);
      if (!omsg)
        throw "No message buffer available";

      volatile struct SimbricksProtoMemM2HReadcomp &rc = omsg->readcomp;
      rc.req_id = read.req_id;
      memcpy((void *) rc.data, &val, read.len);
      SimbricksMemIfM2HOutSend(&memif, omsg, SIMBRICKS_PROTO_MEM_M2H_MSG_READCOMP);
      break;
    }

    case SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE: /* fallthru */
    case SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE_POSTED: {
      volatile struct SimbricksProtoMemH2MWrite &write = msg->write;

      if (write.len > 8)
        throw "Invalid write length";

      uint64_t val = 0;
      memcpy(&val, (const void *) write.data, write.len);

      Write(write.addr, write.len, val);

      if (type != SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE_POSTED) {
        volatile union SimbricksProtoMemM2H *omsg = SimbricksMemIfM2HOutAlloc(&memif, cur_ts);
        if (!omsg)
          throw "No message buffer available";

        volatile struct SimbricksProtoMemM2HWritecomp &wc = omsg->writecomp;
        wc.req_id = write.req_id;
        SimbricksMemIfM2HOutSend(&memif, omsg, SIMBRICKS_PROTO_MEM_M2H_MSG_WRITECOMP);
      }
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

int main(int argc, char *argv[]) {
  char *url = argv[1];
  if (argc != 2) {
    fprintf(stderr,
            "Usage: terminal URL\n");
    return EXIT_FAILURE;
  }

  signal(SIGINT, sigint_handler);
  signal(SIGTERM, sigint_handler);
  signal(SIGUSR1, sigusr1_handler);

  if (!Connect(url))
    return EXIT_FAILURE;

  while (!exiting) {
    while (SimbricksBaseIfOutSync(&memif.base, cur_ts));

    uint64_t next_ts;
    do {
      Poll();
      next_ts = SimbricksBaseIfInTimestamp(&memif.base);
    } while (!exiting && next_ts <= cur_ts);
    cur_ts = next_ts;
  }

  return 0;
}

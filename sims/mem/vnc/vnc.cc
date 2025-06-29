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
#include <iostream>
#include <string>
#include <sstream>
#include <unordered_map>
#include <vector>

#include <simbricks/base/cxxatomicfix.h>
extern "C" {
#include <simbricks/mem/if.h>
#include <simbricks/parser/parser.h>
#include <rfb/rfb.h>
};

struct SimbricksMemIf memif;
struct SimbricksBaseIfSHMPool pool;
static uint64_t cur_ts = 0;
static int exiting = 0;
static std::stringstream outbuf;

static struct {
  int width;
  int height;
  int bytes_per_pixel;
  uint64_t size;
  rfbScreenInfoPtr rfbScreen;
} vnc_screen;

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
  if ((addr & 3) == 0 && addr < vnc_screen.size) {
    memcpy(vnc_screen.rfbScreen->frameBuffer + addr, &val, len);
    uint64_t pos = addr / 4;
    int x = pos % vnc_screen.width;
    int y = pos / vnc_screen.width;
    rfbMarkRectAsModified(vnc_screen.rfbScreen, x, y, x+1, y+1);
  } else {
    std::cerr << "encountered invalid write at address " << std::hex << addr << std::dec << "\n";
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

      if (write.len != vnc_screen.bytes_per_pixel)
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
  if (argc != 8) {
    std::cerr << "Usage: vnc URL WIDTH HEIGHT SPP BPP HOST PORT\n";
    return EXIT_FAILURE;
  }

  int width = std::stoi(argv[2]);
  int height = std::stoi(argv[3]);
  int samples_per_pixel = std::stoi(argv[4]);
  int bytes_per_pixel = std::stoi(argv[5]);
  //TODO parse host
  int port = std::stoi(argv[7]);

  if (samples_per_pixel > bytes_per_pixel) {
    std::cerr << "samples per pixel cannot be greater than bytes per pixel\n";
    return EXIT_FAILURE;
  }

  if (bytes_per_pixel != 1 and bytes_per_pixel != 2 and bytes_per_pixel !=4) {
    std::cerr << "invalid value for bytes per pixel: " << bytes_per_pixel << "\n";
    return EXIT_FAILURE;
  }

  rfbScreenInfoPtr rfbScreen = rfbGetScreen(
    NULL, NULL, width, height, 8, samples_per_pixel, bytes_per_pixel
  );
  if (!rfbScreen) {
    return EXIT_FAILURE;
  }
  rfbScreen->desktopName = "SimBricks VNC";
  rfbScreen->frameBuffer = (char*)calloc(
    width*height*bytes_per_pixel, sizeof(*rfbScreen->frameBuffer)
  );
  //TODO set host
  rfbScreen->port = port;
  rfbScreen->ipv6port = port;

  rfbInitServer(rfbScreen);

  vnc_screen.width = width;
  vnc_screen.height = height;
  vnc_screen.bytes_per_pixel = bytes_per_pixel;
  vnc_screen.size = width * height * bytes_per_pixel;
  vnc_screen.rfbScreen = rfbScreen;

  rfbRunEventLoop(rfbScreen, -1, TRUE);

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

  rfbShutdownServer(rfbScreen, TRUE);
  free(rfbScreen->frameBuffer);
  rfbScreenCleanup(rfbScreen);

  return 0;
}

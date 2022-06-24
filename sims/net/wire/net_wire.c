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

#include <assert.h>
#include <fcntl.h>
#include <linux/if.h>
#include <linux/if_tun.h>
#include <pcap/pcap.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <unistd.h>

#include <simbricks/network/if.h>

static uint64_t cur_ts;
static int exiting = 0;
static pcap_dumper_t *dumpfile = NULL;

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
  fprintf(stderr, "main_time = %lu\n", cur_ts);
}

static void move_pkt(struct SimbricksNetIf *from, struct SimbricksNetIf *to) {
  volatile union SimbricksProtoNetMsg *msg_from =
      SimbricksNetIfInPoll(from, cur_ts);
  volatile union SimbricksProtoNetMsg *msg_to;
  volatile struct SimbricksProtoNetMsgPacket *tx;
  volatile struct SimbricksProtoNetMsgPacket *rx;
  struct pcap_pkthdr ph;
  uint8_t type;

  if (msg_from == NULL)
    return;

  type = SimbricksNetIfInType(from, msg_from);
  if (type == SIMBRICKS_PROTO_NET_MSG_PACKET) {
    tx = &msg_from->packet;

    // log to pcap file if initialized
    if (dumpfile) {
      memset(&ph, 0, sizeof(ph));
      ph.ts.tv_sec = cur_ts / 1000000000000ULL;
      ph.ts.tv_usec = (cur_ts % 1000000000000ULL) / 1000ULL;
      ph.caplen = tx->len;
      ph.len = tx->len;
      pcap_dump((unsigned char *)dumpfile, &ph, (unsigned char *)tx->data);
    }

    msg_to = SimbricksNetIfOutAlloc(to, cur_ts);
    if (msg_to != NULL) {
      rx = &msg_to->packet;
      rx->len = tx->len;
      rx->port = 0;
      memcpy((void *)rx->data, (void *)tx->data, tx->len);

      SimbricksNetIfOutSend(to, msg_to, SIMBRICKS_PROTO_NET_MSG_PACKET);
    } else {
      fprintf(stderr, "move_pkt: dropping packet\n");
    }
  } else if (type == SIMBRICKS_PROTO_MSG_TYPE_SYNC) {
  } else {
    fprintf(stderr, "move_pkt: unsupported type=%u\n", type);
    abort();
  }

  SimbricksNetIfInDone(from, msg_from);
}

int main(int argc, char *argv[]) {
  struct SimbricksBaseIfParams params;
  struct SimbricksNetIf nsif_a, nsif_b;
  uint64_t ts_a, ts_b;
  int sync_a, sync_b;
  pcap_t *pc = NULL;

  SimbricksNetIfDefaultParams(&params);

  if (argc < 3 || argc > 7) {
    fprintf(stderr,
            "Usage: net_wire SOCKET-A SOCKET-B [SYNC-MODE (ignored)] "
            "[SYNC-PERIOD] [ETH-LATENCY] [PCAP-FILE]\n");
    return EXIT_FAILURE;
  }

  signal(SIGINT, sigint_handler);
  signal(SIGTERM, sigint_handler);
  signal(SIGUSR1, sigusr1_handler);

  if (argc >= 5)
    params.sync_interval = strtoull(argv[4], NULL, 0) * 1000ULL;

  if (argc >= 6)
    params.link_latency = strtoull(argv[5], NULL, 0) * 1000ULL;

  if (argc >= 7) {
    pc = pcap_open_dead_with_tstamp_precision(DLT_EN10MB, 65535,
                                              PCAP_TSTAMP_PRECISION_NANO);
    if (pc == NULL) {
      perror("pcap_open_dead failed");
      return EXIT_FAILURE;
    }

    dumpfile = pcap_dump_open(pc, argv[6]);
  }

  sync_a = sync_b = 1;
  if (SimbricksNetIfInit(&nsif_a, &params, argv[1], &sync_a) != 0) {
    return -1;
  }
  if (SimbricksNetIfInit(&nsif_b, &params, argv[2], &sync_b) != 0) {
    return -1;
  }

  printf("start polling\n");
  while (!exiting) {
    if (SimbricksNetIfOutSync(&nsif_a, cur_ts) != 0) {
      fprintf(stderr, "SimbricksNetIfOutSync(nsif_a) failed\n");
      abort();
    }
    if (SimbricksNetIfOutSync(&nsif_b, cur_ts) != 0) {
      fprintf(stderr, "SimbricksNetIfN2DSync(nsif_b) failed\n");
      abort();
    }

    do {
      move_pkt(&nsif_a, &nsif_b);
      move_pkt(&nsif_b, &nsif_a);
      ts_a = SimbricksNetIfInTimestamp(&nsif_a);
      ts_b = SimbricksNetIfInTimestamp(&nsif_b);
    } while (!exiting &&
             ((sync_a && ts_a <= cur_ts) || (sync_b && ts_b <= cur_ts)));

    if (sync_a && sync_b)
      cur_ts = ts_a <= ts_b ? ts_a : ts_b;
    else if (sync_a)
      cur_ts = ts_a;
    else if (sync_b)
      cur_ts = ts_b;
  }

  if (dumpfile)
    pcap_dump_close(dumpfile);
  return 0;
}

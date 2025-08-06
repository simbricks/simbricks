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

#include "dist/rdma/net_rdma.h"

#include <assert.h>
#include <fcntl.h>
#include <getopt.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/mman.h>
#include <unistd.h>

#include <simbricks/base/proto.h>

#include "dist/common/utils.h"

const char *shm_path = NULL;
size_t shm_size = 256 * 1024 * 1024ULL;  // 256MB

bool mode_listen = false;
struct sockaddr_in addr;

char *listen_info_file_path = NULL;
char *listen_ready_file_path = NULL;

int epfd = -1;

const char *ib_devname = NULL;
bool ib_connect = false;
uint8_t ib_port = 1;
int ib_sgid_idx = -1;

static void PrintUsage() {
  fprintf(stderr,
          "Usage: net_rdma [OPTIONS] IP PORT LISTEN-INFO-FILE LISTEN-READY-FILE\n"
          "    -l: Listen instead of connecting\n"
          "    -L LISTEN-SOCKET: listening socket for a simulator\n"
          "    -C CONN-SOCKET: connecting socket for a simulator\n"
          "    -s SHM-PATH: shared memory region path\n"
          "    -S SHM-SIZE: shared memory region size in MB (default 256)\n");
}

static int ParseArgs(int argc, char *argv[]) {
  const char *opts = "lL:C:s:S:D:ip:g:";
  int c;

  while ((c = getopt(argc, argv, opts)) != -1) {
    switch (c) {
      case 'l':
        mode_listen = true;
        break;

      case 'L':
        if (!BasePeerAdd(optarg, true))
          return 1;
        break;

      case 'C':
        if (!BasePeerAdd(optarg, false))
          return 1;
        break;

      case 's':
        if (!(shm_path = strdup(optarg))) {
          perror("ParseArgs: strdup failed");
          return 1;
        }
        break;

      case 'S':
        shm_size = strtoull(optarg, NULL, 10) * 1024 * 1024;
        break;

      case 'D':
        ib_devname = optarg;
        break;

      case 'i':
        ib_connect = true;
        break;

      case 'p':
        ib_port = strtoull(optarg, NULL, 10);
        break;

      case 'g':
        ib_sgid_idx = strtoull(optarg, NULL, 10);
        break;

      default:
        PrintUsage();
        return 1;
    }
  }

  if (optind + 4 != argc) {
    PrintUsage();
    return 1;
  }

  addr.sin_family = AF_INET;
  addr.sin_port = htons(strtoul(argv[optind + 1], NULL, 10));
  if ((addr.sin_addr.s_addr = inet_addr(argv[optind])) == INADDR_NONE) {
    PrintUsage();
    return 1;
  }

  listen_info_file_path = argv[optind + 2];
  listen_ready_file_path = argv[optind + 3];

  return 0;
}

static void *PollThread(void *data) {
  while (true)
    BasePoll();
  return NULL;
}

static int IOLoop() {
  while (1) {
    const size_t kNumEvs = 8;
    struct epoll_event evs[kNumEvs];
    int n = epoll_wait(epfd, evs, kNumEvs, -1);
    if (n < 0) {
      perror("IOLoop: epoll_wait failed");
      return 1;
    }

    for (int i = 0; i < n; i++) {
      struct Peer *peer = evs[i].data.ptr;
      if (peer && BasePeerEvent(peer, evs[i].events))
        return 1;
      else if (!peer && RdmaEvent())
        return 1;
    }

    fflush(stdout);
  }
}

int main(int argc, char *argv[]) {
  if (ParseArgs(argc, argv))
    return EXIT_FAILURE;

#ifdef DEBUG
  fprintf(stderr, "pid=%d shm=%s\n", getpid(), shm_path);
#endif

  if ((epfd = epoll_create1(0)) < 0) {
    perror("epoll_create1 failed");
    return EXIT_FAILURE;
  }

  if (BaseInit(shm_path, shm_size, epfd))
    return EXIT_FAILURE;

  if (BaseListen())
    return EXIT_FAILURE;

  if (mode_listen) {
    if (RdmaListen(&addr))
      return EXIT_FAILURE;
  } else {
    if (RdmaConnect(&addr))
      return EXIT_FAILURE;
  }
  printf("RDMA connected\n");
  fflush(stdout);

  if (BaseConnect())
    return EXIT_FAILURE;
  printf("Peers initialized\n");
  fflush(stdout);

  pthread_t poll_thread;
  if (pthread_create(&poll_thread, NULL, PollThread, NULL)) {
    perror("pthread_create failed (poll thread)");
    return EXIT_FAILURE;
  }

  return IOLoop();
}

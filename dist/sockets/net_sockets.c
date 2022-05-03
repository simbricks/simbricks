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
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <netinet/tcp.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/mman.h>
#include <unistd.h>

#include <simbricks/base/proto.h>

#include "dist/common/base.h"
#include "dist/common/utils.h"

//#define SOCK_DEBUG

#define MAX_PEERS 32
#define RXBUF_SIZE (1024 * 1024)
#define TXBUF_SIZE (128 * 1024)
#define TXBUF_NUM 16

struct SockIntroMsg {
  uint32_t payload_len;
  uint8_t data[];
} __attribute__((packed));

struct SockReportMsg {
  uint32_t written_pos[MAX_PEERS];
  uint32_t clean_pos[MAX_PEERS];
  bool valid[MAX_PEERS];
} __attribute__((packed));

struct SockEntriesMsg {
  uint32_t num_entries;
  uint32_t pos;
  uint8_t data[];
} __attribute__((packed));

enum SockMsgType {
  kMsgIntro,
  kMsgReport,
  kMsgEntries,
};

struct SockMsg {
  uint32_t msg_type;
  uint32_t msg_len;
  uint32_t msg_id;
  uint32_t id;
  union {
    struct SockIntroMsg intro;
    struct SockReportMsg report;
    struct SockEntriesMsg entries;
    struct SockMsg *next_free;
  };
} __attribute__((packed));


const char *shm_path = NULL;
size_t shm_size = 256 * 1024 * 1024ULL;  // 256MB

static bool mode_listen = false;
static struct sockaddr_in addr;

static int epfd = -1;
static int sockfd = -1;
static int msg_id = 0;

static uint8_t *rx_buffer;
static size_t rx_buf_pos = 0;

static struct SockMsg *tx_msgs_free = NULL;
pthread_spinlock_t freelist_spin;

static void PrintUsage() {
  fprintf(stderr,
          "Usage: net_sockets [OPTIONS] IP PORT\n"
          "    -l: Listen instead of connecting on socket\n"
          "    -L LISTEN-SOCKET: listening socket for a simulator\n"
          "    -C CONN-SOCKET: connecting socket for a simulator\n"
          "    -s SHM-PATH: shared memory region path\n"
          "    -S SHM-SIZE: shared memory region size in MB (default 256)\n");
}

static int ParseArgs(int argc, char *argv[]) {
  const char *opts = "lL:C:s:S:";
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

      default:
        PrintUsage();
        return 1;
    }
  }

  if (optind + 2  != argc) {
    PrintUsage();
    return 1;
  }

  addr.sin_family = AF_INET;
  addr.sin_port = htons(strtoul(argv[optind + 1], NULL, 10));
  if ((addr.sin_addr.s_addr = inet_addr(argv[optind])) == INADDR_NONE) {
    PrintUsage();
    return 1;
  }

  return 0;
}

static struct SockMsg *SockMsgAlloc() {
  pthread_spin_lock(&freelist_spin);
  struct SockMsg *msg = tx_msgs_free;
  if (msg != NULL) {
    tx_msgs_free = msg->next_free;
  }
  pthread_spin_unlock(&freelist_spin);
  return msg;
}

static void SockMsgFree(struct SockMsg *msg) {
  pthread_spin_lock(&freelist_spin);
  msg->next_free = tx_msgs_free;
  tx_msgs_free = msg;
  pthread_spin_unlock(&freelist_spin);
}

static int SockAllocInit() {
  if (pthread_spin_init(&freelist_spin, PTHREAD_PROCESS_PRIVATE)) {
    perror("SockAllocInit: pthread_spin_init failed");
    return 1;
  }

  if ((rx_buffer = calloc(1, RXBUF_SIZE)) == NULL) {
    perror("SockAllocInit rxbuf calloc failed");
    return 1;
  }

  int i;
  for (i = 0; i < TXBUF_NUM; i++) {
    struct SockMsg *msg;
    if ((msg = calloc(1, sizeof(*msg) + TXBUF_SIZE)) == NULL) {
      perror("SockAllocInit: calloc failed");
      return 1;
    }

    SockMsgFree(msg);
  }

  return 0;
}

static int SockInitCommon() {
  // disable nagling
  int flag = 1;
  if (setsockopt(sockfd, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag))) {
    perror("SockInitCommon: set sockopt nodelay failed");
    return 1;
  }

  // set non-blocking
  int flags = fcntl(sockfd, F_GETFL);
  if (fcntl(sockfd, F_SETFL, flags | O_NONBLOCK)) {
    perror("SockInitCommon: fcntl set nonblock failed");
    return 1;
  }

  // increase buffer size
  int n = 1024 * 1024;
  if (setsockopt(sockfd, SOL_SOCKET, SO_RCVBUF, &n, sizeof(n))) {
    perror("SockInitCommon: setsockopt rxbuf failed");
    return 1;
  }
  n = 1024 * 1024;
  if (setsockopt(sockfd, SOL_SOCKET, SO_SNDBUF, &n, sizeof(n))) {
    perror("SockInitCommon: setsockopt txbuf failed");
    return 1;
  }

  // add to epoll
  struct epoll_event epev;
  epev.events = EPOLLIN;
  epev.data.ptr = NULL;
  if (epoll_ctl(epfd, EPOLL_CTL_ADD, sockfd, &epev)) {
    perror("SockInitCommon: epoll_ctl failed");
    return 1;
  }

  return 0;
}

static int SockListen(struct sockaddr_in *addr) {
  int lfd;
  if ((lfd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)) < 0) {
    perror("RdmaIBListen: socket failed");
    return 1;
  }

  int flag;
  flag = 1;
  if (setsockopt(lfd, SOL_SOCKET, SO_REUSEPORT, &flag, sizeof(flag))) {
    perror("RdmaIBListen: setsockopt reuseport faild");
    return 1;
  }

  if (bind(lfd, (struct sockaddr *) addr, sizeof(*addr))) {
    perror("RdmaIBListen: bind failed");
    return 1;
  }

  if (listen(lfd, 1)) {
    perror("RdmaIBListen: listen");
    return 1;
  }

  if ((sockfd = accept(lfd, NULL, 0)) < 0) {
    perror("RdmaIBListen: accept failed");
    return 1;
  }
  close(lfd);

  return SockInitCommon();
}

static int SockConnect(struct sockaddr_in *addr) {
  if ((sockfd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)) < 0) {
    perror("RdmaIBConnect: socket failed");
    return 1;
  }

  if (connect(sockfd, (struct sockaddr *) addr, sizeof(*addr))) {
    perror("RdmaIBConnect: connect failed");
  }

  return SockInitCommon();
}

static int SockMsgRxIntro(struct SockMsg *msg) {
  struct SockIntroMsg *intro_msg = &msg->intro;
  if (msg->id >= peer_num) {
    fprintf(stderr, "SockMsgRxIntro: invalid peer id in message (%u)\n",
            msg->id);
    abort();
  }
  if (msg->msg_len <
      offsetof(struct SockMsg, intro.data) +  intro_msg->payload_len) {
    fprintf(stderr, "SockMsgRxIntro: message too short for payload len\n");
    abort();
  }
  struct Peer *peer = peers + msg->id;
#ifdef SOCK_DEBUG
  fprintf(stderr, "SockMsgRxIntro -> peer %s\n", peer->sock_path);
#endif

  if (peer->intro_valid_remote) {
    fprintf(stderr, "SockMsgRxIntro: received multiple messages (%u)\n",
            msg->id);
    abort();
  }
  if (intro_msg->payload_len > (uint32_t) sizeof(peer->intro_remote)) {
    fprintf(stderr, "SockMsgRxIntro: Intro longer than buffer\n");
    abort();
  }

  peer->intro_valid_remote = true;
  peer->intro_remote_len = intro_msg->payload_len;
  memcpy(peer->intro_remote, intro_msg->data, intro_msg->payload_len);

  if (BasePeerSetupQueues(peer)) {
    fprintf(stderr, "SockMsgRxIntro(%s): queue setup failed\n",
        peer->sock_path);
    abort();
  }
  if (BasePeerSendIntro(peer))
    return 1;

  if (peer->intro_valid_local) {
    fprintf(stderr, "SockMsgRxIntro(%s): marking peer as ready\n",
            peer->sock_path);
    peer->ready = true;
  }
  return 0;
}

static int SockMsgRxReport(struct SockMsg *msg) {
#ifdef SOCK_DEBUG
  fprintf(stderr, "SockMsgRxReport");
#endif
  for (size_t i = 0; i < MAX_PEERS && i < peer_num; i++) {
    if (!msg->report.valid[i])
      continue;

    if (i >= peer_num) {
      fprintf(stderr, "SockMsgRxReport: invalid ready peer number %zu\n", i);
      abort();
    }
    BasePeerReport(&peers[i], msg->report.written_pos[i],
                   msg->report.clean_pos[i]);
  }
  return 0;
}

static int SockMsgRxEntries(struct SockMsg *msg) {
  struct SockEntriesMsg *entries = &msg->entries;
  if (msg->id >= peer_num) {
    fprintf(stderr, "SockMsgRxEntries: invalid peer id in message (%u)\n",
            msg->id);
    abort();
  }

  struct Peer *peer = peers + msg->id;
#ifdef SOCK_DEBUG
  fprintf(stderr, "SockMsgRxEntries -> peer %s\n", peer->sock_path);
  fprintf(stderr, "  num=%u  pos=%u\n", entries->num_entries, entries->pos);
  /*fprintf(stderr, "  data: ");
  {
    size_t i;
    for (i = 0; i < entries->num_entries * peer->cleanup_elen; i++) {
      fprintf(stderr, "%02x ", entries->data[i]);
    }
  }
  fprintf(stderr, "\n");*/
#endif

  uint32_t len = entries->num_entries * peer->cleanup_elen;

  if (len + offsetof(struct SockMsg, entries.data) != msg->msg_len) {
    fprintf(stderr, "SockMsgRxEntries: invalid message length (m=%u l=%u)\n",
            msg->msg_len, len);
    abort();
  }

  uint32_t i;
  for (i = 0; i < entries->num_entries; i++)
    BaseEntryReceived(peer, entries->pos + i,
                      entries->data + (i * peer->cleanup_elen));
  return 0;
}

static int SockMsgRx(struct SockMsg *msg) {
#ifdef SOCK_DEBUG
  fprintf(stderr, "SockMsgRx(mi=%u t=%u i=%u l=%u)\n", msg->msg_id,
          msg->msg_type, msg->id, msg->msg_len);
#endif
  if (msg->msg_type == kMsgIntro)
    return SockMsgRxIntro(msg);
  else if (msg->msg_type == kMsgReport)
    return SockMsgRxReport(msg);
  else if (msg->msg_type == kMsgEntries)
    return SockMsgRxEntries(msg);

  fprintf(stderr, "SockMsgRx: unexpected message type = %u\n", msg->msg_type);
  abort();
}

static int SockEvent(uint32_t events) {
#ifdef SOCK_DEBUG
  bool had_leftover = rx_buf_pos > 0;
#endif
  ssize_t ret = read(sockfd, rx_buffer + rx_buf_pos, RXBUF_SIZE - rx_buf_pos);
  if (ret < 0) {
    perror("SockEvent: read failed");
    return 1;
  } else if (ret == 0) {
    fprintf(stderr, "SockEvent: eof on read\n");
    return 1;
  }

  rx_buf_pos += ret;

  struct SockMsg *msg = (struct SockMsg *) rx_buffer;
  while (rx_buf_pos >= sizeof(*msg) && rx_buf_pos >= msg->msg_len) {
    if (SockMsgRx(msg))
      return 1;

    rx_buf_pos -= msg->msg_len;
    if (rx_buf_pos > 0) {
      // if data is left move it to beginning of the buffer
      memmove(rx_buffer, rx_buffer + msg->msg_len, rx_buf_pos);
    }
  }

#ifdef SOCK_DEBUG
  if (rx_buf_pos > 0) {
    fprintf(stderr, "SockEvent: left over data rbp=%zu ml=%u\n", rx_buf_pos,
            msg->msg_len);
  } else if (had_leftover) {
    fprintf(stderr, "SockEvent: cleared leftover data\n");
  }
#endif

  return 0;
}

static int SockSend(struct SockMsg *msg) {
  msg->msg_id = __sync_fetch_and_add(&msg_id, 1);
  size_t len = msg->msg_len;
  size_t pos = 0;
  uint8_t *buf = (uint8_t *) msg;
  do {
    ssize_t ret = write(sockfd, buf + pos, len - pos);
    if (ret > 0) {
      pos += ret;
    } else if (ret == 0) {
      fprintf(stderr, "SockSend: EOF on TX\n");
      return 1;
    } else if (ret < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
      // HACK: this is ugly
    } else if (ret < 0) {
      perror("SockSend: write failed");
      return 1;
    }
#ifdef SOCK_DEBUG
    if (pos < len) {
      fprintf(stderr, "SockSend: short write pos=%zu len=%zu\n", pos, len);
    }
#endif
  } while (pos < len);

#ifdef SOCK_DEBUG
  fprintf(stderr, "SockSend(id=%u) Successful\n", msg->msg_id);
#endif
  return 0;
}

int BaseOpPassIntro(struct Peer *peer) {
#ifdef SOCK_DEBUG
  fprintf(stderr, "BaseOpPassIntro(%s)\n", peer->sock_path);
#endif

  struct SockMsg *msg = SockMsgAlloc();
  if (!msg)
    return 1;

  msg->msg_len = offsetof(struct SockMsg, intro.data) + peer->intro_local_len;
  if (msg->msg_len < sizeof(*msg))
    msg->msg_len = sizeof(*msg);
  msg->id = peer - peers;
  msg->msg_type = kMsgIntro;
  msg->intro.payload_len = peer->intro_local_len;
  memcpy(msg->intro.data, peer->intro_local, peer->intro_local_len);

  int ret = SockSend(msg);
  SockMsgFree(msg);
  return ret;
}

int BaseOpPassEntries(struct Peer *peer, uint32_t pos, uint32_t n) {
#ifdef SOCK_DEBUG
  fprintf(stderr, "BaseOpPassEntries(%s, n=%zu, pos=%u)\n", peer->sock_path, n,
          pos);
#endif
  if (n * peer->local_elen > TXBUF_SIZE) {
    fprintf(stderr,
            "BaseOpPassEntries: tx buffer too small (%u) for n (%u) entries\n",
            TXBUF_SIZE, n);
    abort();
  }

  if ((peer->last_sent_pos + 1) % peer->local_enum != pos) {
    fprintf(stderr, "BaseOpPassEntries: entry sent repeatedly: p=%u n=%u\n",
            pos, n);
    abort();
  }
  peer->last_sent_pos = pos + n - 1;

  struct SockMsg *msg = SockMsgAlloc();
  if (!msg)
    return 1;

  msg->id = peer - peers;
  msg->msg_type = kMsgEntries;
  msg->entries.num_entries = n;
  msg->entries.pos = pos;

  uint64_t abs_pos = pos * peer->local_elen;
  uint32_t len = n * peer->local_elen;
  memcpy(msg->entries.data, peer->local_base + abs_pos, len);
#ifdef SOCK_DEBUG
  /*fprintf(stderr, "  data: ");
  {
    size_t i;
    for (i = 0; i < n * peer->local_elen; i++) {
      fprintf(stderr, "%02x ", msg->entries.data[i]);
    }
  }
  fprintf(stderr, "\n");*/
#endif
  msg->msg_len = offsetof(struct SockMsg, entries.data) + len;

  int ret = SockSend(msg);
  SockMsgFree(msg);
  return ret;
}

int BaseOpPassReport() {
#ifdef SOCK_DEBUG
  fprintf(stderr, "BaseOpPassReport()\n");
#endif
  if (peer_num > MAX_PEERS) {
    fprintf(stderr, "BaseOpPassReport: peer_num (%zu) larger than max (%u)\n",
            peer_num, MAX_PEERS);
    abort();
  }

  struct SockMsg *msg = SockMsgAlloc();
  if (!msg)
    return 1;

  msg->msg_type = kMsgReport;
  msg->msg_len = sizeof(*msg);
  for (size_t i = 0; i < MAX_PEERS; i++) {
    if (i >= peer_num) {
      msg->report.valid[i] = false;
      continue;
    }

    struct Peer *peer = &peers[i];
    msg->report.valid[i] = peer->ready;
    if (!peer->ready)
      continue;

    peer->cleanup_pos_reported = peer->cleanup_pos_next;
    msg->report.clean_pos[i] = peer->cleanup_pos_reported;
    peer->local_pos_reported = peer->local_pos;
    msg->report.written_pos[i] = peer->local_pos_reported;
#ifdef SOCK_DEBUG
    fprintf(stderr, "  peer[%zu]  clean_pos=%u  written_pos=%u\n", i,
            peer->cleanup_pos_reported, peer->local_pos_reported);
#endif
  }

  int ret = SockSend(msg);
  SockMsgFree(msg);
  return ret;
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
      if (errno == EINTR)
        continue;

      perror("IOLoop: epoll_wait failed");
      return 1;
    }

    for (int i = 0; i < n; i++) {
      struct Peer *peer = evs[i].data.ptr;
      if (peer && BasePeerEvent(peer, evs[i].events))
        return 1;
      else if (!peer && SockEvent(evs[i].events))
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

  if (SockAllocInit())
    return EXIT_FAILURE;

  if (BaseInit(shm_path, shm_size, epfd))
    return EXIT_FAILURE;

  if (BaseListen())
    return  EXIT_FAILURE;

  if (mode_listen) {
    if (SockListen(&addr))
      return EXIT_FAILURE;
  } else {
    if (SockConnect(&addr))
      return EXIT_FAILURE;
  }
  printf("Socket connected\n");
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

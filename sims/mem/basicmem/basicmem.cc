/*
 * Copyright 2022 Max Planck Institute for Software Systems, and
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
#include <ctime>
#include <iostream>
#include <vector>

#include <simbricks/base/cxxatomicfix.h>
extern "C" {
#include <simbricks/mem/if.h>
};

#define BASICMEM_DEBUG 1

static int exiting = 0;
static uint64_t cur_ts = 0;
uint8_t *mem_array;
uint64_t size;
uint64_t base_addr;

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
    fprintf(stderr, "main_time = %lu\n", cur_ts);
}

bool MemifInit(struct SimbricksMemIf *memif, const char *shm_path,
                struct SimbricksBaseIfParams *memParams) {
  
  struct SimbricksBaseIf *membase = &memif->base;
  struct SimbricksBaseIfSHMPool pool_;
  memset(&pool_, 0, sizeof(pool_));
  
  struct SimBricksBaseIfEstablishData ests[1];
  struct SimbricksProtoMemHostIntro intro;
  unsigned n_bifs = 0;

  memset(&intro, 0, sizeof(intro));
  ests[n_bifs].base_if = membase;
  ests[n_bifs].tx_intro = &intro;
  ests[n_bifs].tx_intro_len = sizeof(intro);
  ests[n_bifs].rx_intro = &intro;
  ests[n_bifs].rx_intro_len = sizeof(intro);
  n_bifs++;
  
  if (SimbricksBaseIfInit(membase, memParams)) {
    perror("Init: SimbricksBaseIfInit failed");
  }

  std::string shm_path_ = shm_path;

  if (SimbricksBaseIfSHMPoolCreate(
          &pool_, shm_path_.c_str(),
          SimbricksBaseIfSHMSize(&membase->params)) != 0) {
    perror("MemifInit: SimbricksBaseIfSHMPoolCreate failed");
    return false;
  }

  if (SimbricksBaseIfListen(membase, &pool_) != 0) {
    perror("MemifInit: SimbricksBaseIfListen failed");
    return false;
  }

  if (SimBricksBaseIfEstablish(ests, 1)) {
    fprintf(stderr, "SimBricksBaseIfEstablish failed\n");
    return false;
  }

  printf("done connecting\n");
  return true;
}

volatile union SimbricksProtoMemM2H* M2HAlloc(SimbricksMemIf *memif, uint64_t cur_ts) {

  volatile union SimbricksProtoMemM2H *msg_to;
  bool first = true;
  while ((msg_to = SimbricksMemIfM2HOutAlloc(memif, cur_ts)) == NULL){
    if (first) {
      fprintf(stderr, "M2HAlloc: warning waiting for entry (%zu)\n",
              memif->base.out_pos);
      first = false;
    }
  }

  if (!first){
    fprintf(stderr, "D2HAlloc: entry successfully allocated\n");
  }

  return msg_to;
}


void PollH2M(struct SimbricksMemIf *memif, uint64_t cur_ts) {
  volatile union SimbricksProtoMemH2M *msg = SimbricksMemIfH2MInPoll(memif, cur_ts);

  if (msg == NULL){
    return;
  }

  int i;
  uint8_t type;
  uint64_t addr, len;
  volatile uint8_t *data;
  volatile union SimbricksProtoMemM2H *msg_to; 

  type = SimbricksMemIfH2MInType(memif, msg);
  switch (type) {
    case SIMBRICKS_PROTO_MEM_H2M_MSG_READ:
      addr = msg->read.addr;
      len = msg->read.len;

      msg_to = M2HAlloc(memif, cur_ts);
      msg_to->readcomp.req_id = msg->read.req_id;
      memcpy((void *)msg_to->readcomp.data, &mem_array[addr], len);


      SimbricksMemIfM2HOutSend(memif, msg_to, SIMBRICKS_PROTO_MEM_M2H_MSG_READCOMP);

#if BASICMEM_DEBUG 
      printf("received H2M read. Sending read comp msg\n");
#endif
      break;
    case SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE:
      addr = msg->write.addr;
      len = msg->write.len;
      data = msg->write.data;
      memcpy(&mem_array[addr], (void*)data, len);

      msg_to = M2HAlloc(memif, cur_ts);
      msg_to->writecomp.req_id = msg->write.req_id;
      SimbricksMemIfM2HOutSend(memif, msg_to, SIMBRICKS_PROTO_MEM_M2H_MSG_WRITECOMP);

#if BASICMEM_DEBUG 
      printf("received H2M write addr: %lu size: %d\n", addr, msg->write.len);
      for (i = 0; i < (int)len; i++){
        printf("%X ", msg->write.data[i]);
      }
      printf("\n");

#endif
      break;
    case SIMBRICKS_PROTO_MSG_TYPE_SYNC:
      break;
    default:
      fprintf(stderr, "poll_h2m: unsupported type=%u\n", type);
  }

  SimbricksMemIfH2MInDone(memif, msg);
}

int main(int argc, char *argv[]) {
  
  

  int asid = 0;

  signal(SIGINT, sigint_handler);
  signal(SIGUSR1, sigusr1_handler);

  int sync_mem = 1;
  uint64_t next_ts = 0;
  const char *shmPath;
  struct SimbricksBaseIfParams memParams;
  struct SimbricksMemIf memif;
  
  SimbricksMemIfDefaultParams(&memParams);

  if (argc < 6 || argc > 10) {
    fprintf(stderr,
            "Usage: basicmem [SIZE] [BASE-ADDR] [ASID] [MEM-SOCKET] "
            "SHM [SYNC-MODE] [START-TICK] [SYNC-PERIOD] [MEM-LATENCY]\n");
    return -1;
  }
  if (argc >= 8)
     cur_ts = strtoull(argv[7], NULL, 0);
  if (argc >= 9)
    memParams.sync_interval =  strtoull(argv[8], NULL, 0) * 1000ULL;
  if (argc >= 10)
    memParams.link_latency = strtoull(argv[9], NULL, 0) * 1000ULL;

  size = strtoull(argv[1], NULL, 0);
  base_addr = strtoull(argv[2], NULL, 0);
  asid = atoi(argv[3]);
  memParams.sock_path = argv[4];
  shmPath = argv[5];

  memParams.sync_mode = kSimbricksBaseIfSyncOptional;
  memParams.blocking_conn = false;
  memif.base.sync = sync_mem;

  mem_array = (uint8_t *) malloc(size * sizeof(uint8_t));
  if (!mem_array){
    perror("no array allocated\n");
  }

  if (!MemifInit(&memif, shmPath, &memParams)){
    return EXIT_FAILURE;
  }

  printf("start polling\n");
  while (!exiting){
    while (SimbricksMemIfM2HOutSync(&memif, cur_ts)) {
      fprintf(stderr, "warn: SimbricksMemIfSync failed (t=%lu)\n", cur_ts);
    }

    do {
      
      PollH2M(&memif, cur_ts);

      if (sync_mem){
        next_ts = SimbricksMemIfH2MInTimestamp(&memif);
      }

    } while (!exiting && next_ts <= cur_ts);

  }
  return 0;
}

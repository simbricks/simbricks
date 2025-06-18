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
#include <libelf.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#include <simbricks/mem/if.h>
#include <simbricks/mem/proto.h>

#define BASICMEM_DEBUG 0

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
  struct SimbricksProtoMemHostIntro m_intro;
  struct SimbricksProtoMemHostIntro h_intro;
  unsigned n_bifs = 0;

  memset(&m_intro, 0, sizeof(m_intro));
  ests[n_bifs].base_if = membase;
  ests[n_bifs].tx_intro = &m_intro;
  ests[n_bifs].tx_intro_len = sizeof(m_intro);
  ests[n_bifs].rx_intro = &h_intro;
  ests[n_bifs].rx_intro_len = sizeof(h_intro);
  n_bifs++;

  if (SimbricksBaseIfInit(membase, memParams)) {
    perror("Init: SimbricksBaseIfInit failed");
  }

  if (SimbricksBaseIfSHMPoolCreate(
          &pool_, shm_path, SimbricksBaseIfSHMSize(&membase->params)) != 0) {
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

volatile union SimbricksProtoMemM2H *M2HAlloc(struct SimbricksMemIf *memif,
                                              uint64_t cur_ts) {
  volatile union SimbricksProtoMemM2H *msg_to;
  bool first = true;
  while ((msg_to = SimbricksMemIfM2HOutAlloc(memif, cur_ts)) == NULL) {
    if (first) {
      fprintf(stderr, "M2HAlloc: warning waiting for entry (%zu)\n",
              memif->base.out_pos);
      first = false;
    }
  }

  if (!first) {
    fprintf(stderr, "D2HAlloc: entry successfully allocated\n");
  }

  return msg_to;
}

void PollH2M(struct SimbricksMemIf *memif, uint64_t cur_ts) {
  volatile union SimbricksProtoMemH2M *msg =
      SimbricksMemIfH2MInPoll(memif, cur_ts);

  if (msg == NULL) {
    return;
  }

  uint8_t type;
  uint64_t addr, len;
  volatile union SimbricksProtoMemM2H *msg_to;

  type = SimbricksMemIfH2MInType(memif, msg);
  switch (type) {
    case SIMBRICKS_PROTO_MEM_H2M_MSG_READ:
      addr = msg->read.addr;
      len = msg->read.len;

      msg_to = M2HAlloc(memif, cur_ts);
      msg_to->readcomp.req_id = msg->read.req_id;
      memcpy((void *)msg_to->readcomp.data, &mem_array[addr], len);

      SimbricksMemIfM2HOutSend(memif, msg_to,
                               SIMBRICKS_PROTO_MEM_M2H_MSG_READCOMP);

#if BASICMEM_DEBUG
      printf("received H2M read. addr: 0x%lx size: 0x%lx\n", addr, len);
#endif
      break;
    case SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE:
      addr = msg->write.addr;
      len = msg->write.len;
      memcpy(&mem_array[addr], (const void *)msg->write.data, len);

      msg_to = M2HAlloc(memif, cur_ts);
      msg_to->writecomp.req_id = msg->write.req_id;
      SimbricksMemIfM2HOutSend(memif, msg_to,
                               SIMBRICKS_PROTO_MEM_M2H_MSG_WRITECOMP);

#if BASICMEM_DEBUG
      printf("received H2M write addr: 0x%lx size: %d\n", addr, msg->write.len);
      for (i = 0; i < (int)len; i++) {
        printf("%X ", msg->write.data[i]);
      }
      printf("\n");
#endif
      break;
    case SIMBRICKS_PROTO_MEM_H2M_MSG_WRITE_POSTED:
      addr = msg->write.addr;
      len = msg->write.len;
      memcpy(&mem_array[addr], (const void *)msg->write.data, len);

#if BASICMEM_DEBUG
      printf("received H2M posted write addr: 0x%lx size: %d\n", addr,
             msg->write.len);
      for (i = 0; i < (int)len; i++) {
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

bool LoadElf(const char *elf_file) {
  elf_version(EV_CURRENT);

  int fd = open(elf_file, O_RDONLY);
  Elf *elf = elf_begin(fd, ELF_C_READ, NULL);
  if (!elf) {
    fprintf(stderr, "failed to load elf: %s\n", elf_errmsg(elf_errno()));
    return false;
  }

  size_t file_size;
  const char *raw_data = elf_rawfile(elf, &file_size);

  size_t ident_size;
  const char* ident = elf_getident(elf, &ident_size);
  bool is_64 = ident[EI_CLASS] == ELFCLASS64;

  size_t hdr_num;
  if (elf_getphdrnum(elf, &hdr_num)) {
    fprintf(stderr, "failed to get phdnum\n");
    return false;
  }

  if (is_64) {
    Elf64_Phdr *phdr = elf64_getphdr(elf);

    for (size_t i = 0; i < hdr_num; ++i) {
      if (phdr[i].p_type != PT_LOAD) {
        continue;
      }
      if (phdr[i].p_filesz == 0) {
        continue;
      }
      
      if (phdr[i].p_vaddr + phdr[i].p_filesz > size) {
        fprintf(stderr, "elf does not fit inside memory\n");
        return false;
      }
      memcpy(mem_array + phdr[i].p_vaddr, raw_data + phdr[i].p_offset, phdr[i].p_memsz);
    }
  } else {
    Elf32_Phdr *phdr = elf32_getphdr(elf);

    for (size_t i = 0; i < hdr_num; ++i) {
      if (phdr[i].p_type != PT_LOAD) {
        continue;
      }
      if (phdr[i].p_filesz == 0) {
        continue;
      }
      
      if (phdr[i].p_vaddr + phdr[i].p_filesz > size) {
        fprintf(stderr, "elf does not fit inside memory\n");
        return false;
      }
      memcpy(mem_array + phdr[i].p_vaddr, raw_data + phdr[i].p_offset, phdr[i].p_memsz);
    }
  }

  return true;
}

int main(int argc, char *argv[]) {
  signal(SIGINT, sigint_handler);
  signal(SIGUSR1, sigusr1_handler);

  int sync_mem = 1;
  uint64_t next_ts = 0;
  const char *shmPath;
  struct SimbricksBaseIfParams memParams;
  struct SimbricksMemIf memif;
  const char *elf_file = NULL;

  SimbricksMemIfDefaultParams(&memParams);

  if (argc < 6 || argc > 11) {
    fprintf(stderr,
            "Usage: basicmem [SIZE] [BASE-ADDR] [ASID] [MEM-SOCKET] "
            "SHM [SYNC-MODE] [START-TICK] [SYNC-PERIOD] [MEM-LATENCY] [ELF]\n");
    return -1;
  }
  if (argc >= 8)
    cur_ts = strtoull(argv[7], NULL, 0);
  if (argc >= 9)
    memParams.sync_interval = strtoull(argv[8], NULL, 0) * 1000ULL;
  if (argc >= 10)
    memParams.link_latency = strtoull(argv[9], NULL, 0) * 1000ULL;
  if (argc >= 11)
    elf_file = argv[10];

  size = strtoull(argv[1], NULL, 0);
  base_addr = strtoull(argv[2], NULL, 0);
  memParams.sock_path = argv[4];
  shmPath = argv[5];

  memParams.sync_mode = kSimbricksBaseIfSyncOptional;
  memParams.blocking_conn = true;

  mem_array = (uint8_t *)calloc(size, sizeof(uint8_t));
  if (!mem_array) {
    perror("no array allocated\n");
  }

  if (elf_file != NULL) {
    if (!LoadElf(elf_file)) {
      fprintf(stderr, "faild to load ELF binary %s\n", elf_file);
      return EXIT_FAILURE;
    }
  }

  if (!MemifInit(&memif, shmPath, &memParams)) {
    return EXIT_FAILURE;
  }

  printf("start polling\n");
  while (!exiting) {
    while (SimbricksMemIfM2HOutSync(&memif, cur_ts)) {
      fprintf(stderr, "warn: SimbricksMemIfSync failed (t=%lu)\n", cur_ts);
    }

    do {
      PollH2M(&memif, cur_ts);

      if (sync_mem) {
        next_ts = SimbricksMemIfH2MInTimestamp(&memif);
      }
    } while (!exiting && next_ts <= cur_ts);

    cur_ts = next_ts;
  }
  return 0;
}

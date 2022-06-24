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

#include <signal.h>
#include <verilated.h>
#include <verilated_fst_c.h>

#include <iostream>
#include <vector>

#include "sims/net/menshen/obj_dir/Vrmt_wrapper.h"
#include "sims/net/menshen/ports.h"

#define MAX_PKT_SIZE 2048

// #define ETH_DEBUG
// #define TRACE_ENABLED

class EthernetTx;
class EthernetRx;

std::vector<Port *> ports;
int synchronized = 0;
uint64_t sync_period = (500 * 1000ULL);  // 500ns
uint64_t eth_latency = (500 * 1000ULL);  // 500ns
int sync_mode = SIMBRICKS_PROTO_SYNC_SIMBRICKS;
static uint64_t clock_period = 4 * 1000ULL;  // 4ns -> 250MHz
uint64_t main_time = 0;
int exiting = 0;
EthernetTx *txMAC;
EthernetRx *rxMAC;

static void sigint_handler(int dummy) {
  exiting = 1;
}

static void sigusr1_handler(int dummy) {
  fprintf(stderr, "main_time = %lu\n", main_time);
}

double sc_time_stamp() {
  return main_time;
}

static void reset_inputs(Vrmt_wrapper *top) {
  top->clk = 0;
  top->aresetn = 0;
  top->vlan_drop_flags = 0;

  memset(top->s_axis_tdata, 0, sizeof(top->s_axis_tdata));
  top->s_axis_tkeep = 0;
  memset(top->s_axis_tuser, 0, sizeof(top->s_axis_tuser));
  top->s_axis_tvalid = 0;
  top->s_axis_tlast = 0;

  top->m_axis_tready = 0;
}

static void dump_if(Vrmt_wrapper *top) {
  std::cout << "Dumping Interfaces:" << std::endl;
  std::cout << "  clk = " << top->clk << std::endl;
  std::cout << "  aresetn = " << top->aresetn << std::endl;
  std::cout << "  ctrl_token = " << top->ctrl_token << std::endl;
  std::cout << "  vlan_drop_flags = " << top->vlan_drop_flags << std::endl;
  std::cout << std::endl;

  std::cout << "  s_axis_tdata = { ";
  for (size_t i = 0;
       i < sizeof(top->s_axis_tdata) / sizeof(top->s_axis_tdata[0]); i++) {
    std::cout << top->s_axis_tdata[i] << " ";
  }
  std::cout << "}" << std::endl;
  std::cout << "  s_axis_tkeep = " << top->s_axis_tkeep << std::endl;
  std::cout << "  s_axis_tuser = { ";
  for (size_t i = 0;
       i < sizeof(top->s_axis_tuser) / sizeof(top->s_axis_tuser[0]); i++) {
    std::cout << top->s_axis_tuser[i] << " ";
  }
  std::cout << "}" << std::endl;
  std::cout << "  s_axis_tvalid = " << top->s_axis_tvalid << std::endl;
  std::cout << "  s_axis_tready = " << top->s_axis_tready << std::endl;
  std::cout << "  s_axis_tlast = " << top->s_axis_tlast << std::endl;
  std::cout << std::endl;

  std::cout << "  m_axis_tdata = { ";
  for (size_t i = 0;
       i < sizeof(top->m_axis_tdata) / sizeof(top->m_axis_tdata[0]); i++) {
    std::cout << top->m_axis_tdata[i] << " ";
  }
  std::cout << "}" << std::endl;
  std::cout << "  m_axis_tkeep = " << top->m_axis_tkeep << std::endl;
  std::cout << "  m_axis_tuser = { ";
  for (size_t i = 0;
       i < sizeof(top->m_axis_tuser) / sizeof(top->m_axis_tuser[0]); i++) {
    std::cout << top->m_axis_tuser[i] << " ";
  }
  std::cout << "}" << std::endl;
  std::cout << "  m_axis_tvalid = " << top->m_axis_tvalid << std::endl;
  std::cout << "  m_axis_tready = " << top->m_axis_tready << std::endl;
  std::cout << "  m_axis_tlast = " << top->m_axis_tlast << std::endl;
}

class EthernetTx {
 protected:
  Vrmt_wrapper &top;
  uint8_t packet_buf[MAX_PKT_SIZE];
  size_t packet_len;

 public:
  explicit EthernetTx(Vrmt_wrapper &top_) : top(top_), packet_len(0) {
  }

  void packet_done(uint16_t port_id) {
    if (port_id >= ports.size()) {
#ifdef ETH_DEBUG
      std::cerr << "EthernetTx: invalid port set (" << port_id
                << "), setting to 0" << std::endl;
#endif
      port_id = 0;
    }

    ports[port_id]->TxPacket(packet_buf, packet_len, main_time);

#ifdef ETH_DEBUG
    std::cerr << main_time << " EthernetTx: packet len=" << std::hex
              << packet_len << " port=" << port_id << " ";
    for (size_t i = 0; i < packet_len; i++) {
      std::cerr << (unsigned)packet_buf[i] << " ";
    }
    std::cerr << std::endl;
#endif
  }

  void step() {
    top.m_axis_tready = 1;

    if (top.m_axis_tvalid) {
      /* iterate over all bytes on the bus */
      uint8_t *txbus = (uint8_t *)&top.m_axis_tdata;
      for (size_t i = 0; i < sizeof(top.m_axis_tdata); i++) {
        if ((top.m_axis_tkeep & (1ULL << i)) != 0) {
          assert(packet_len < 2048);
          packet_buf[packet_len++] = txbus[i];
        }
      }

      if (top.m_axis_tlast) {
        packet_done((top.m_axis_tuser[0] >> 24) & 0xff);
        packet_len = 0;
      }
    }
  }
};

class EthernetRx {
 protected:
  Vrmt_wrapper &top;

  static const size_t FIFO_SIZE = 32;
  uint16_t fifo_ports[FIFO_SIZE];
  uint8_t fifo_bufs[FIFO_SIZE][MAX_PKT_SIZE];
  size_t fifo_lens[FIFO_SIZE];
  size_t fifo_pos_rd;
  size_t fifo_pos_wr;

  size_t packet_off;

 public:
  explicit EthernetRx(Vrmt_wrapper &top_)
      : top(top_), fifo_pos_rd(0), fifo_pos_wr(0), packet_off(0) {
    for (size_t i = 0; i < FIFO_SIZE; i++)
      fifo_lens[i] = 0;
  }

  void packet_received(const void *data, size_t len, uint16_t port) {
    if (fifo_lens[fifo_pos_wr] != 0) {
#ifdef ETH_DEBUG
      std::cerr << "EthernetRx: dropping packet" << std::endl;
#endif
      return;
    }

    memcpy(fifo_bufs[fifo_pos_wr], data, len);
    fifo_lens[fifo_pos_wr] = len;
    fifo_ports[fifo_pos_wr] = port;

#ifdef ETH_DEBUG
    std::cout << main_time << " rx into " << fifo_pos_wr << std::endl;
    std::cerr << main_time << " EthernetRx: packet len=" << std::hex << len
              << " ";
    for (size_t i = 0; i < len; i++) {
      std::cerr << (unsigned)fifo_bufs[fifo_pos_wr][i] << " ";
    }
    std::cerr << std::endl;
#endif

    fifo_pos_wr = (fifo_pos_wr + 1) % FIFO_SIZE;
  }

  void step() {
    if (fifo_lens[fifo_pos_rd] != 0) {
      // we have data to send
      if (packet_off != 0 && !top.s_axis_tready) {
        // no ready signal, can't advance
#ifdef ETH_DEBUG
        std::cerr << "eth rx: no ready " << fifo_pos_rd << " " << packet_off
                  << std::endl;
#endif
      } else if (packet_off == fifo_lens[fifo_pos_rd]) {
        // done with packet
#ifdef ETH_DEBUG
        std::cerr << main_time << " EthernetRx: finished packet" << std::endl;
#endif
        top.s_axis_tvalid = 0;
        top.s_axis_tlast = 0;
        top.s_axis_tuser[0] = 0;

        packet_off = 0;
        fifo_lens[fifo_pos_rd] = 0;
        fifo_pos_rd = (fifo_pos_rd + 1) % FIFO_SIZE;
      } else {
        // put out more packet data
#ifdef ETH_DEBUG
        std::cerr << main_time << " EthernetRx: push flit " << packet_off
                  << std::endl;
        if (packet_off == 0)
          std::cout << "rx from " << fifo_pos_rd << std::endl;
#endif
        top.s_axis_tkeep = 0;
        uint8_t *rdata = (uint8_t *)&top.s_axis_tdata;
        size_t i;

        /*if (packet_off == 0) {
            dump_if(&top);
        }*/
        if (packet_off == 0)
          top.s_axis_tuser[0] = fifo_lens[fifo_pos_rd] |
                                (((uint64_t)fifo_ports[fifo_pos_rd]) << 16) |
                                (((uint64_t)fifo_ports[fifo_pos_rd]) << 24);
        else
          top.s_axis_tuser[0] = 0;

        for (i = 0; i < sizeof(top.s_axis_tdata) &&
                    packet_off < fifo_lens[fifo_pos_rd];
             i++) {
          rdata[i] = fifo_bufs[fifo_pos_rd][packet_off];
          top.s_axis_tkeep |= (1ULL << i);
          packet_off++;
        }
        top.s_axis_tvalid = 1;
        top.s_axis_tlast = (packet_off == fifo_lens[fifo_pos_rd]);
      }
      //  trace->dump(main_time);
    } else {
      // no data
      top.s_axis_tuser[0] = 0;
      top.s_axis_tvalid = 0;
      top.s_axis_tlast = 0;
    }
  }
};

static void poll_ports() {
  uint16_t p_id = 0;
  for (auto port : ports) {
    while (!exiting) {
      const void *data;
      size_t len;
      enum Port::RxPollState ps = port->RxPacket(data, len, main_time);
      if (ps == Port::kRxPollFail)
        break;

      if (ps == Port::kRxPollSuccess)
        rxMAC->packet_received(data, len, p_id);

      port->RxDone();

      if (!synchronized)
        break;
    }

    p_id++;
  }
}

int main(int argc, char *argv[]) {
  signal(SIGINT, sigint_handler);
  signal(SIGUSR1, sigusr1_handler);

  char *vargs[2] = {argv[0], NULL};
  Verilated::commandArgs(1, vargs);
#ifdef TRACE_ENABLED
  Verilated::traceEverOn(true);
#endif
  Vrmt_wrapper *top = new Vrmt_wrapper;

  /* execute reset */
  reset_inputs(top);
  top->aresetn = 0;
  for (int i = 0; i < 16; i++) {
    top->eval();
    top->clk = !top->clk;
  }
  top->aresetn = 1;

  dump_if(top);

  if (argc <= 1) {
    std::cerr << "no ports" << std::endl;
    return EXIT_FAILURE;
  }

  struct SimbricksBaseIfParams params;
  SimbricksNetIfDefaultParams(&params);

  for (int i = 1; i < argc; i++) {
    NetPort *np = new NetPort(&params);
    if (!np->Connect(argv[i], synchronized)) {
      std::cerr << "connecting to port " << argv[i] << " failed" << std::endl;
      return EXIT_FAILURE;
    }
    ports.push_back(np);
  }

  txMAC = new EthernetTx(*top);
  rxMAC = new EthernetRx(*top);

#ifdef TRACE_ENABLED
  VerilatedFstC *trace = nullptr;
  trace = new VerilatedFstC;
  top->trace(trace, 99);
  trace->open("debug.fst");
#endif
  while (!exiting) {
    // Sync all interfaces
    for (auto port : ports)
      port->Sync(main_time);

    poll_ports();

    /* falling edge */
    top->clk = !top->clk;
    main_time += clock_period / 2;
    top->eval();
#ifdef TRACE_ENABLED
    trace->dump(main_time);
#endif

    txMAC->step();
    rxMAC->step();

    /* rising edge */
    top->clk = !top->clk;
    main_time += clock_period / 2;
    top->eval();
#ifdef TRACE_ENABLED
    trace->dump(main_time);
#endif
  }

#ifdef TRACE_ENABLED
  trace->close();
#endif
  dump_if(top);

  return 0;
}

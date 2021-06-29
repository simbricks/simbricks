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

#include "trace/process.h"

#include <boost/bind.hpp>
#include <boost/foreach.hpp>
#include <iostream>
#include <memory>
#include <vector>

#include "trace/events.h"
#include "trace/parser.h"

template <typename T>
struct event_pair_cmp {
  bool operator()(const std::pair<T, std::shared_ptr<event>> l,
                  const std::pair<T, std::shared_ptr<event>> r) const {
    return l.second->ts < r.second->ts;
  }
};

/** merge multiple event streams into one ordered by timestamp */
void MergeEvents(coro_t::push_type &sink,
                 std::set<coro_t::pull_type *> &all_parsers) {
  typedef std::pair<coro_t::pull_type *, std::shared_ptr<event>> itpair_t;

  // create set of pairs of source and next event, ordered by timestamp of next
  // event.
  std::set<itpair_t, event_pair_cmp<coro_t::pull_type *>> active;

  // initially populate the set
  for (auto p : all_parsers) {
    if (*p) {
      auto ev = p->get();
      (*p)();
      active.insert(std::make_pair(p, ev));
    }
  }

  // iterate until there are no more active sources
  while (!active.empty()) {
    // grab event with lowest timestamp
    auto i = active.begin();
    itpair_t p = *i;
    active.erase(i);

    // emit event
    sink(p.second);

    // check if there is another event in the source, if so, re-enqueue
    if (*p.first) {
      auto ev = p.first->get();
      (*p.first)();
      active.insert(std::make_pair(p.first, ev));
    }
  }
}

void Printer(coro_t::pull_type &source) {
  uint64_t ts_off = 0;
  for (auto ev: source) {
    std::shared_ptr<EHostCall> hc;
    std::shared_ptr<EHostInstr> hi;
    if ((hi = std::dynamic_pointer_cast<EHostInstr>(ev))) {
      continue;
    } else if ((hc = std::dynamic_pointer_cast<EHostCall>(ev)) &&
        strcmp(ev->source->label, "C") &&
        hc->fun == "__sys_sendto") {
      std::cout << "---------- REQ START:" << ev->ts << std::endl;
      ts_off = ev->ts;
    }

    std::cout << ev->source->label << " ";

    ev->ts -= ts_off;
    ev->ts /= 1000;
    ev->dump(std::cout);
  }
}

void Consumer(coro_t::pull_type &source) {
  for (auto ev: source) {
  }
}

struct InstStatsData {
  const char *label;
  uint64_t nInsts;
  uint64_t tMin;
  uint64_t tMax;
  uint64_t tMean;
  std::vector <uint64_t> tAll;
};

void InstStats(coro_t::push_type &sink, coro_t::pull_type &source,
    struct InstStatsData &data) {
  uint64_t last_ts = 0;
  uint64_t first_ts = 0;
  data.nInsts = 0;
  for (auto ev: source) {
    std::shared_ptr<EHostInstr> hi;
    if ((hi = std::dynamic_pointer_cast<EHostInstr>(ev))) {
      if (!last_ts) {
        // first instruction
        first_ts = hi->ts;
        data.tMin = UINT64_MAX;
        data.tMax = 0;
      } else {
        uint64_t lat = hi->ts - last_ts;

        data.nInsts++;
        data.tAll.push_back(lat);
        if (lat < data.tMin)
          data.tMin = lat;
        if (lat > data.tMax)
          data.tMax = lat;

        /*if (lat > 4000)
          std::cout << "ILAT: " << lat  << " " << std::hex << hi->pc <<
              std::dec << "  " << hi->ts << std::endl;*/
        }
      last_ts = hi->ts;
      //last_pc = hi->pc;
    }
    sink(ev);
  }

  if (data.nInsts != 0)
    data.tMean = (last_ts - first_ts) / data.nInsts;
  else
    data.tMean = 0;
}


int main(int argc, char *argv[]) {
  if (argc != 5) {
    std::cerr << "Usage: process CLIENT_HLOG CLIENT_NLOG SERVER_HLOG "
                  "SERVER_CLOG" << std::endl;
    return 1;
  }

  sym_map syms;
  syms.add_filter("entry_SYSCALL_64");
  syms.add_filter("__do_sys_gettimeofday");
  syms.add_filter("__sys_sendto");
  syms.add_filter("i40e_lan_xmit_frame");
  syms.add_filter("syscall_return_via_sysret");
  syms.add_filter("__sys_recvfrom");
  syms.add_filter("deactivate_task");
  syms.add_filter("interrupt_entry");
  syms.add_filter("i40e_msix_clean_rings");
  syms.add_filter("napi_schedule_prep");
  syms.add_filter("__do_softirq");
  syms.add_filter("trace_napi_poll");
  syms.add_filter("net_rx_action");
  syms.add_filter("i40e_napi_poll");
  syms.add_filter("activate_task");
  syms.add_filter("copyout");

  syms.load_file("linux.dump", 0);
  syms.load_file("i40e.dump", 0xffffffffa0000000ULL);
  std::cerr << "map loaded" << std::endl;

  std::set<log_parser *> all_parsers;

  gem5_parser ch(syms);
  ch.open(argv[1]);
  ch.label = "C";
  all_parsers.insert(&ch);

  gem5_parser sh(syms);
  sh.open(argv[3]);
  sh.label = "S";
  all_parsers.insert(&sh);

  nicbm_parser cn;
  cn.open(argv[2]);
  cn.label = "C";
  all_parsers.insert(&cn);

  nicbm_parser sn;
  sn.open(argv[4]);
  sn.label = "S";
  all_parsers.insert(&sn);

  std::cerr << "Opened all" << std::endl;

  std::set<coro_t::pull_type *> sources;
  std::set<InstStatsData *> isds;
  for (auto p : all_parsers) {
    coro_t::pull_type *src = new coro_t::pull_type(
      boost::bind(&log_parser::read_coro, boost::ref(*p), _1));
      InstStatsData *isd = new InstStatsData;
      isd->label = p->label;
    coro_t::pull_type *istat = new coro_t::pull_type(
      boost::bind(InstStats, _1, boost::ref(*src), boost::ref(*isd)));
    sources.insert(istat);
    isds.insert(isd);
  }

  coro_t::pull_type merged(boost::bind(MergeEvents, _1, boost::ref(sources)));
  Consumer(merged);

  std::cout << "Stats:" << std::endl;
  for (auto isd : isds) {
    if (!isd->nInsts)
      continue;

    std::sort(isd->tAll.begin(), isd->tAll.end());

    std::cout << " - " << isd->label << std::endl;
    std::cout << "    Instrs: " << isd->nInsts << std::endl;
    std::cout << "    Mean instr time: " << isd->tMean << std::endl;
    for (int i = 0; i <= 100; i += 1)
      std::cout << "    P[" << i << "] instr time: " <<
          isd->tAll[isd->tAll.size() * i / 100 - (i == 100 ? 1 : 0)] <<
          std::endl;
  }
}

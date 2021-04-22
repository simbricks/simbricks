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
#include <boost/coroutine2/all.hpp>
#include <boost/foreach.hpp>
#include <iostream>
#include <memory>

#include "trace/events.h"
#include "trace/parser.h"

template <typename T>
struct event_pair_cmp {
  bool operator()(const std::pair<T, std::shared_ptr<event>> l,
                  const std::pair<T, std::shared_ptr<event>> r) const {
    return l.second->ts < r.second->ts;
  }
};

typedef boost::coroutines2::asymmetric_coroutine<std::shared_ptr<event>> coro_t;

void ReadEvents(coro_t::push_type &sink, log_parser &lp) {
  while (lp.next_event() && lp.cur_event) {
    lp.cur_event->source = &lp;
    sink(lp.cur_event);
  }
}

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
    if ((hc = std::dynamic_pointer_cast<EHostCall>(ev)) &&
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
  gem5_parser sh(syms);
  nicbm_parser cn;
  nicbm_parser sn;
  ch.open(argv[1]);
  cn.open(argv[2]);
  sh.open(argv[3]);
  sn.open(argv[4]);
  ch.label = cn.label = "C";
  sh.label = sn.label = "S";
  all_parsers.insert(&ch);
  all_parsers.insert(&cn);
  all_parsers.insert(&sh);
  all_parsers.insert(&sn);

  std::cerr << "Opened all" << std::endl;

  std::set<coro_t::pull_type *> sources;
  for (auto p : all_parsers) {
    sources.insert(new coro_t::pull_type(
      boost::bind(ReadEvents, _1, boost::ref(*p))));
  }

  coro_t::pull_type merged(boost::bind(MergeEvents, _1, boost::ref(sources)));
  Printer(merged);
}

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

#include <iostream>

#include "trace/events.h"
#include "trace/parser.h"

struct log_parser_cmp {
  bool operator()(const log_parser *l, const log_parser *r) const {
    return l->cur_event->ts < r->cur_event->ts;
  }
};

int main(int argc, char *argv[]) {
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

  std::set<log_parser *, log_parser_cmp> active_parsers;

  for (auto p : all_parsers) {
    if (p->next_event() && p->cur_event)
      active_parsers.insert(p);
  }

  uint64_t ts_off = 0;
  while (!active_parsers.empty()) {
    auto i = active_parsers.begin();
    log_parser *p = *i;
    active_parsers.erase(i);

    EHostCall *hc;
    event *ev = p->cur_event;
    if (p == &ch && (hc = dynamic_cast<EHostCall *>(ev)) &&
        hc->fun == "__sys_sendto") {
      std::cout << "---------- REQ START:" << ev->ts << std::endl;
      ts_off = ev->ts;
    }

    std::cout << p->label << " ";

    ev->ts -= ts_off;
    ev->ts /= 1000;
    ev->dump(std::cout);

    delete ev;

    if (p->next_event() && p->cur_event)
      active_parsers.insert(p);
  }
}

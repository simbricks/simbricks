#include <iostream>

#include "events.h"
#include "parser.h"
#include "process.h"

int main(int argc, char *argv[])
{
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

    gem5_parser client(syms);
    //gem5_parser server(syms);
    //nicbm_parser client;
    nicbm_parser server;
    client.open(argv[1]);
    server.open(argv[2]);

    client.next_event();
    server.next_event();
    while (client.cur_event || server.cur_event) {
        event *ev;
        const char *pref;
        if (((client.cur_event && server.cur_event) &&
                    client.cur_event->ts <= server.cur_event->ts) ||
                (!server.cur_event && client.cur_event))
        {
            ev = client.cur_event;
            client.next_event();
            pref = "C";
        } else {
            ev = server.cur_event;
            server.next_event();
            pref = "S";
        }
        std::cout << pref << " ";
        ev->dump(std::cout);
    }

}

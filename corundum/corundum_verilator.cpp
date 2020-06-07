#include <iostream>

#include "Vinterface.h"
#include "verilated.h"
#include "verilated_vcd_c.h"

static uint64_t main_time = 0;

double sc_time_stamp()
{
    return main_time;
}

int main(int argc, char *argv[])
{
    Verilated::commandArgs(argc, argv);
    Vinterface *top = new Vinterface;

    top->final();
    delete top;
    return 0;
}

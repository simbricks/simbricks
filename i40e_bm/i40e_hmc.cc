#include <stdlib.h>
#include <string.h>
#include <cassert>
#include <iostream>

#include "i40e_bm.h"

#include "i40e_base_wrapper.h"

using namespace i40e;

extern nicbm::Runner *runner;

host_mem_cache::host_mem_cache(i40e_bm &dev_)
    : dev(dev_)
{
    for (size_t i = 0; i < MAX_SEGMENTS; i++) {
        segs[i].pdir_addr = 0;
        segs[i].pgcount = 0;
        segs[i].valid = false;
        segs[i].direct = false;
    }
}

void host_mem_cache::reg_updated(uint64_t addr)
{
    std::cerr << "hmc reg updated " << addr << std::endl;
}

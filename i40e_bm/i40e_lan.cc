#include <stdlib.h>
#include <string.h>
#include <cassert>
#include <iostream>

#include "i40e_bm.h"

#include "i40e_base_wrapper.h"

using namespace i40e;

extern nicbm::Runner *runner;

lan::lan(i40e_bm &dev_, size_t num_qs_)
    : dev(dev_), num_qs(num_qs_)
{
}

void lan::qena_updated(uint16_t idx, bool rx)
{
}

void lan::tail_updated(uint16_t idx, bool rx)
{
}

/*
 * Copyright 2024 Max Planck Institute for Software Systems, and
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

#include <stdlib.h>
#include <string.h>

#include <cassert>
#include <iostream>

#include "sims/nic/i40e_bm/i40e_base_wrapper.h"
#include "sims/nic/i40e_bm/i40e_bm.h"

namespace i40e {

ptpmgr::ptpmgr(i40e_bm &dev_)
    : dev(dev_),
      last_updated(0),
      last_val(0),
      offset(0),
      inc_val(0),
      adj_neg(false),
      adj_val(0) {
}

uint64_t ptpmgr::update_clock() {
  /* this simulates the behavior of the PHC, but instead of doing it cycle by
     cycle, we calculate updates when the clock is accessed or parameters are
     modified, applying the same changes that should have happened cycle by
     cycle. Before modifying any of the parameters update_clock has to be
     called to get the correct behavior, to ensure e.g. that updates to adj and
     inc are applied at the correct points in time.*/
  uint64_t ps_per_cycle = 1000000000000ULL / CLOCK_HZ;
  uint64_t cycle_now = dev.runner_->TimePs() / ps_per_cycle;
  uint64_t cycles_passed = cycle_now - last_updated;

  // increment clock
  last_val += (__uint128_t)inc_val * cycles_passed;

  // factor in adjustments
  if (adj_val != 0) {
    __uint128_t adj;
    if (adj_val <= cycles_passed) {
      adj = cycles_passed;
      adj_val -= cycles_passed;
    } else {
      adj = adj_val;
      adj_val = 0;
    }

    adj = adj << 32;
    if (adj_neg)
      last_val -= adj;
    else
      last_val += adj;
  }

  last_updated = cycle_now;
  return (last_val >> 32) + offset;
}

uint64_t ptpmgr::phc_read() {
  return update_clock();
}

void ptpmgr::phc_write(uint64_t val) {
  uint64_t cur_val = update_clock();
  offset += (val - cur_val);
}

uint32_t ptpmgr::adj_get() {
  update_clock();

  uint32_t x = (adj_val << I40E_PRTTSYN_ADJ_TSYNADJ_SHIFT) &
               I40E_PRTTSYN_ADJ_TSYNADJ_MASK;
  if (adj_neg)
    x |= I40E_PRTTSYN_ADJ_SIGN_MASK;
  return x;
}

void ptpmgr::adj_set(uint32_t val) {
  update_clock();
  adj_val =
      (val & I40E_PRTTSYN_ADJ_TSYNADJ_MASK) >> I40E_PRTTSYN_ADJ_TSYNADJ_SHIFT;
  adj_neg = (val & I40E_PRTTSYN_ADJ_SIGN_MASK);
}

void ptpmgr::inc_set(uint64_t inc) {
  update_clock();
  inc_val = inc;
}

}  // namespace i40e

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

#include "lib/simbricks/nicbm/multinic.h"

#include <string.h>

#include <boost/bind.hpp>
#include <boost/fiber/all.hpp>
#include <thread>
#include <vector>

namespace nicbm {

void MultiNicRunner::CompRunner::YieldPoll() {
  boost::this_fiber::yield();
}

int MultiNicRunner::CompRunner::NicIfInit() {
  volatile bool ready = false;
  volatile int result = 0;

  // NicIfInit will block, so run it in a separate thread and then wait for it
  std::thread t([this, &ready, &result]() {
    result = Runner::NicIfInit();
    ready = true;
  });

  while (!ready)
    YieldPoll();
  t.join();
  return result;
}

MultiNicRunner::CompRunner::CompRunner(Device &dev) : Runner(dev) {
}

MultiNicRunner::MultiNicRunner(DeviceFactory &factory) : factory_(factory) {
}

int MultiNicRunner::RunMain(int argc, char *argv[]) {
  int start = 0;
  std::vector<Runner *> runners;
  std::vector<boost::fibers::fiber *> fibers;
  do {
    int end;
    for (end = start + 1; end < argc && strcmp(argv[end], "--"); end++)
      ;
    argv[start] = argv[0];

    CompRunner *r = new CompRunner(factory_.create());
    if (r->ParseArgs(end - start, argv + start))
      return -1;

    auto *f = new boost::fibers::fiber(
        boost::bind(&CompRunner::RunMain, boost::ref(*r)));
    runners.push_back(r);
    fibers.push_back(f);
    start = end;
  } while (start < argc);

  for (auto f : fibers) {
    f->join();
    delete (f);
  }
  return 0;
}

}  // namespace nicbm

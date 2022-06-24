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

#ifndef SIMBRICKS_BASE_CXXATOMICFIX_H_
#define SIMBRICKS_BASE_CXXATOMICFIX_H_

/**
 * FIXME: This is a worklaround till we fix all simbricks headers to be
 * compatible with C++, elliminating the need for extern "C", making it possible
 * to include this in the generic header where we use the atomics.
 *
 * until then, this needs to be included before the generic header.
 */

#include <atomic>
#define _Atomic(T) std::atomic<T>
using std::atomic_load_explicit;
using std::atomic_store_explicit;
using std::memory_order_acquire;
using std::memory_order_release;

#endif  // SIMBRICKS_BASE_CXXATOMICFIX_H_

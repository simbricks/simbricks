/*
 * Copyright 2025 Max Planck Institute for Software Systems, and
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

#ifndef SIMBRICKS_PARSER_PARSER_H_
#define SIMBRICKS_PARSER_PARSER_H_

#include <stdbool.h>
#include <stdint.h>

#include <simbricks/base/if.h>

struct SimbricksAdapterParams {
  bool listen;
  char *socket_path;
  char *shm_path;
  bool sync;
  bool link_latency_set;
  /** Link latency/propagation delay [picoseconds] */
  uint64_t link_latency;
  bool sync_interval_set;
  /** Maximum gap between sync messages [picoseconds] */
  uint64_t sync_interval;
};

struct SimbricksAdapterParams *SimbricksParametersParse(const char *url);
void SimbricksParametersFree(struct SimbricksAdapterParams *params);

/**
 * Initialize, setup, and connect `n` SimBricks interfaces based on provided
 * URLs.
 *
 * This includes creating an appropriate shared memory pool, if necessary.
 * Parsing parameters from the URLs and setting them for each interface. Then
 * establish listening connections, and wait for outgoing connections. Returns
 * once all interfaces are connected.
 */
int SimbricksParametersEstablish(struct SimBricksBaseIfEstablishData *ifs, const char **urls,
                                 size_t n, struct SimbricksBaseIfSHMPool *pool,
                                 const char *pool_path);

#endif  // SIMBRICKS_PARSER_PARSER_H_

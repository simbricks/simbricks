#ifndef UTILS_PARSER_H_
#define UTILS_PARSER_H_

#include <stdbool.h>
#include <stdint.h>
#include <simbricks/base/if.h>

struct SimbricksAdapterParams {
    bool listen;
    char *socket_path;
    char *shm_path;
    bool sync;
    bool link_latency_set;
    uint64_t link_latency;
    bool sync_interval_set;
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
int SimbricksParametersEstablish(struct SimBricksBaseIfEstablishData *ifs,
                                 const char **urls, size_t n,
                                 struct SimbricksBaseIfSHMPool *pool,
                                 const char *pool_path);

#endif // UTILS_PARSER_H_
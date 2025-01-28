#ifndef UTILS_PARSER_H_
#define UTILS_PARSER_H_

#include <stdbool.h>
#include <stdint.h>

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

#endif // UTILS_PARSER_H_
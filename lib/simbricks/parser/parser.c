#include "parser.h"

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <errno.h>

static const char *NextDelimiter(const char *start, const char *end, int c) {
    assert(start <= end);
    start = strchr(start, c);
    if (start && start < end) {
        return start;
    } else {
        return end;
    }
}

static bool ParseUInteger(const char *str, uint64_t *val) {
    char *endptr;
    errno = 0;
    *val = strtoul(str, &endptr, 10);

    if (errno != 0 || str == endptr || *endptr != '\0') {
        return false;
    }

    return true;
}

// Parse SimBricks "URLs" in the following format:
// ADDR:SYNC[ARGS]
// ADDR = connect:UX_SOCKET_PATH |
//        listen:UX_SOCKET_PATH:SHM_PATH
// SYNC = sync=<true|false>
// ARGS = :latency=XX | :sync_interval=XX
//
// Returns NULL when a failure occured
struct SimbricksAdapterParams *SimbricksParametersParse(const char *url) {
    struct SimbricksAdapterParams *params = malloc(sizeof(struct SimbricksAdapterParams));
    if (params == NULL) {
        fprintf(stderr, "Failed to allocate memory for SimbricksAdapterParams\n");
        return NULL;
    }
    params->socket_path = NULL;
    params->shm_path = NULL;
    params->link_latency_set = false;
    params->sync_interval_set = false;

    const char *url_end = url + strlen(url);
    const char *start = url;
    const char *colon = NextDelimiter(start, url_end, ':');

    // parse type (listen/connect)
    if (colon - start == 7 && strncmp(start, "connect", 7) == 0) {
        params->listen = false;
    } else if (colon - start == 6 && strncmp(start, "listen", 6) == 0) {
        params->listen = true;
    } else {
        fprintf(stderr, "Type is neither 'listen' nor 'connect': %s\n", url);
        goto error;
    }

    // parse unix socket path
    start = colon + 1;
    if (start >= url_end) {
        fprintf(stderr, "Socket path is missing: %s\n", url);
        goto error;
    }
    colon = NextDelimiter(start, url_end, ':');
    if (colon == start) {
        fprintf(stderr, "Socket path cannot be empty: %s\n", url);
        goto error;
    }

    params->socket_path = malloc(colon - start + 1);
    if (params->socket_path == NULL) {
        fprintf(stderr, "Failed to allocate memory for socket path\n");
        goto error;
    }
    memcpy(params->socket_path, start, colon - start);
    params->socket_path[colon - start] = '\0';

    // parse shm path if type is listen
    if (params->listen) {
        start = colon + 1;
        if (start >= url_end) {
            fprintf(stderr, "Shared memory path is missing: %s\n", url);
            goto error;
        }
        colon = NextDelimiter(start, url_end, ':');
        if (colon == start) {
            fprintf(stderr, "Shared memory path cannot be empty: %s\n", url);
            goto error;
        }

        params->shm_path = malloc(colon - start + 1);
        if (params->shm_path == NULL) {
            fprintf(stderr, "Failed to allocate memory for shared memory path\n");
            goto error;
        }
        memcpy(params->shm_path, start, colon - start);
        params->shm_path[colon - start] = '\0';
    }

    // parse sync
    start = colon + 1;
    if (start >= url_end) {
        fprintf(stderr, "Sync parameter is missing: %s\n", url);
        goto error;
    }
    colon = NextDelimiter(start, url_end, ':');
    const char *delim = NextDelimiter(start, colon, '=');
    if (delim == colon) {
        fprintf(stderr, "Sync parameter has an invalid format: %s\n", url);
        goto error;
    }
    if (!(delim - start == 4 && strncmp(start, "sync", 4) == 0)) {
        fprintf(stderr, "Sync parameter has an invalid format: %s\n", url);
        goto error;
    }
    start = delim + 1;
    if (start >= colon) {
        fprintf(stderr, "Sync parameter has an invalid format: %s\n", url);
        goto error;
    }
    if (colon - start == 4 && strncmp(start, "true", 4) == 0) {
        params->sync = true;
    } else if (colon - start == 5 && strncmp(start, "false", 5) == 0) {
        params->sync = false;
    } else {
        fprintf(stderr, "Sync parameter has an invalid format: %s\n", url);
        goto error;
    }

    // parse optional arguments
    start = colon + 1;
    while (start < url_end) {
        colon = NextDelimiter(start, url_end, ':');
        const char *delim = NextDelimiter(start, colon, '=');
        if (delim + 1 >= colon) {
            fprintf(stderr, "Optional parameter has an invalid format: %s\n", url);
            goto error;
        }
        char *arg = malloc(colon - delim);
        memcpy(arg, delim + 1, colon - delim - 1);
        arg[colon - delim - 1] = '\0';
        if (delim - start == 7 && strncmp(start, "latency", 7) == 0) {
            if (ParseUInteger(arg, &params->link_latency)) {
                params->link_latency_set = true;
            } else {
                fprintf(stderr, "Failed to parse link latency value: %s\n", url);
                free(arg);
                goto error;
            }
        } else if (delim - start == 13 && strncmp(start, "sync_interval", 13) == 0) {
            if (ParseUInteger(arg, &params->sync_interval)) {
                params->sync_interval_set = true;
            } else {
                fprintf(stderr, "Failed to parse sync interval value: %s\n", url);
                free(arg);
                goto error;
            }
        } else {
            fprintf(stderr, "Invalid optional parameter: %s\n", url);
            free(arg);
            goto error;
        }
        free(arg);
        start = colon + 1;
    }

    return params;
error:
    SimbricksParametersFree(params);
    return NULL;
}

void SimbricksParametersFree(struct SimbricksAdapterParams *params) {
    free(params->socket_path);
    free(params->shm_path);
    free(params);
}
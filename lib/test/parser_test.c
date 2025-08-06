#include "lib/simbricks/parser/parser.h"

#include <stdio.h>
#include <string.h>

#define TEST_CASE(test_fn, name) \
    printf("Executing test %s\n", name); \
    if (test_fn()) { \
        printf("SUCCESS: %s\n", name); \
    } else { \
        fprintf(stderr, "FAILED: %s\n", name); \
    }

static bool test_valid_connect() {
    char *url = "connect:/some/path:sync=true";
    struct SimbricksAdapterParams *params = SimbricksParametersParse(url);
    if (!params) {
        fprintf(stderr, "Parsing of '%s' failed unexpectedly\n", url);
        goto error;
    }
    if (params->listen) {
        fprintf(stderr, "Type is 'listen' but expected 'connect'\n");
        goto error;
    }
    if (strcmp(params->socket_path, "/some/path") != 0) {
        fprintf(stderr, "UxSocketPath has value '%s' but expected '/some/path'\n",
            params->socket_path);
        goto error;
    }
    if (!params->sync) {
        fprintf(stderr, "Sync is false but expected true\n");
        goto error;
    }
    // success
    SimbricksParametersFree(params);
    return true;
error:
    // failure
    SimbricksParametersFree(params);
    return false;
}

static bool test_valid_listen() {
    char *url = "listen:/some/path:/shm/path:sync=false";
    struct SimbricksAdapterParams *params = SimbricksParametersParse(url);
    if (!params) {
        fprintf(stderr, "Parsing of '%s' failed unexpectedly\n", url);
        goto error;
    }
    if (!params->listen) {
        fprintf(stderr, "Type is 'connect' but expected 'listen'\n");
        goto error;
    }
    if (strcmp(params->socket_path, "/some/path") != 0) {
        fprintf(stderr, "UxSocketPath has value '%s' but expected '/some/path'\n", params->socket_path);
        goto error;
    }
    if (strcmp(params->shm_path, "/shm/path") != 0) {
        fprintf(stderr, "ShmPath has value '%s' but expected '/shm/path'\n", params->shm_path);
        goto error;
    }
    if (params->sync) {
        fprintf(stderr, "Sync is true but expected false\n");
        goto error;
    }
    // success
    SimbricksParametersFree(params);
    return true;
error:
    // failure
    SimbricksParametersFree(params);
    return false;
}

static bool test_valid_optional_args() {
    char *url = "connect:/some/path:sync=true:latency=100:sync_interval=42";
    struct SimbricksAdapterParams *params = SimbricksParametersParse(url);
    if (!params) {
        fprintf(stderr, "Parsing of '%s' failed unexpectedly\n", url);
        goto error;
    }
    if (params->listen) {
        fprintf(stderr, "Type is 'listen' but expected 'connect'\n");
        goto error;
    }
    if (strcmp(params->socket_path, "/some/path") != 0) {
        fprintf(stderr, "UxSocketPath has value '%s' but expected '/some/path'\n", params->socket_path);
        goto error;
    }
    if (!params->sync) {
        fprintf(stderr, "Sync is false but expected true\n");
        goto error;
    }
    if (!params->link_latency_set) {
        fprintf(stderr, "Expected that link latency is set, but it is not\n");
        goto error;
    }
    if (params->link_latency != 100) {
        fprintf(stderr, "Link latency was %lu but expected %d\n", params->link_latency, 100);
        goto error;
    }
    if (!params->sync_interval_set) {
        fprintf(stderr, "Expected that sync interval is set, but it is not\n");
        goto error;
    }
    if (params->sync_interval != 42) {
        fprintf(stderr, "Sync interval was %lu but expected %d\n", params->sync_interval, 42);
        goto error;
    }
    // success
    SimbricksParametersFree(params);
    return true;
error:
    // failure
    SimbricksParametersFree(params);
    return false;
}

int main(void) {
    TEST_CASE(test_valid_connect, "test_valid_connect")
    TEST_CASE(test_valid_listen, "test_valid_listen")
    TEST_CASE(test_valid_optional_args, "test_valid_optional_args")
}
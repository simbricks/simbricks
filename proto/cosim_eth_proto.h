#ifndef COSIM_ETH_PROTO_H_
#define COSIM_ETH_PROTO_H_

#include <stdint.h>

/******************************************************************************/
/* Initialization messages on Unix socket */

/** in dev_intro.flags to indicate that sender supports issuing syncs. */
#define COSIM_ETH_PROTO_FLAGS_DI_SYNC (1 << 0)

/**
 * welcome message sent by device to network. This message comes with the shared
 * memory file descriptor attached.
 */
struct cosim_eth_proto_dev_intro {
    /** flags: see COSIM_ETH_PROTO_FLAGS_DI_* */
    uint64_t flags;

    /** offset of the device-to-network queue in shared memory region */
    uint64_t d2n_offset;
    /** size of an entry in the device-to-network queue in bytes */
    uint64_t d2n_elen;
    /** total device-to-network queue length in #entries */
    uint64_t d2n_nentries;

    /** offset of the net-to-device queue in shared memory region */
    uint64_t n2d_offset;
    /** size of an entry in the net-to-device queue in bytes */
    uint64_t n2d_elen;
    /** total net-to-device queue length in #entries */
    uint64_t n2d_nentries;
} __attribute__((packed));


#define COSIM_ETH_PROTO_FLAGS_NI_SYNC (1 << 0)

/** welcome message sent by network to device */
struct cosim_eth_proto_net_intro {
    /** flags: see COSIM_ETH_PROTO_FLAGS_IN_* */
  uint64_t flags;
} __attribute__((packed));


/******************************************************************************/
/* Messages on in-memory device to network channel */

/** Mask for ownership bit in own_type field */
#define COSIM_ETH_PROTO_D2N_OWN_MASK 0x80
/** Message is owned by device */
#define COSIM_ETH_PROTO_D2N_OWN_DEV 0x00
/** Message is owned by network */
#define COSIM_ETH_PROTO_D2N_OWN_NET 0x80

/** Mask for type value in own_type field */
#define COSIM_ETH_PROTO_D2N_MSG_MASK 0x7f
#define COSIM_ETH_PROTO_D2N_MSG_SYNC 0x1
#define COSIM_ETH_PROTO_D2N_MSG_SEND 0x2

struct cosim_eth_proto_d2n_dummy {
    uint8_t pad[48];
    uint64_t timestamp;
    uint8_t pad_[7];
    uint8_t own_type;
} __attribute__((packed));

struct cosim_eth_proto_d2n_sync {
    uint8_t pad[48];
    uint64_t timestamp;
    uint8_t pad_[7];
    uint8_t own_type;
} __attribute__((packed));

struct cosim_eth_proto_d2n_send {
    uint16_t len;
    uint8_t port;
    uint8_t pad[45];
    uint64_t timestamp;
    uint8_t pad_[7];
    uint8_t own_type;
    uint8_t data[];
} __attribute__((packed));

union cosim_eth_proto_d2n {
    struct cosim_eth_proto_d2n_dummy dummy;
    struct cosim_eth_proto_d2n_sync sync;
    struct cosim_eth_proto_d2n_send send;
};


/******************************************************************************/
/* Messages on in-memory network to device channel */

#define COSIM_ETH_PROTO_N2D_OWN_MASK 0x80
/** Message is owned by host */
#define COSIM_ETH_PROTO_N2D_OWN_NET 0x00
/** Message is owned by device */
#define COSIM_ETH_PROTO_N2D_OWN_DEV 0x80

#define COSIM_ETH_PROTO_N2D_MSG_MASK 0x7f
#define COSIM_ETH_PROTO_N2D_MSG_SYNC 0x1
#define COSIM_ETH_PROTO_N2D_MSG_RECV 0x2

struct cosim_eth_proto_n2d_dummy {
    uint8_t pad[48];
    uint64_t timestamp;
    uint8_t pad_[7];
    uint8_t own_type;
} __attribute__((packed));

struct cosim_eth_proto_n2d_sync {
    uint8_t pad[48];
    uint64_t timestamp;
    uint8_t pad_[7];
    uint8_t own_type;
} __attribute__((packed));

struct cosim_eth_proto_n2d_recv {
    uint16_t len;
    uint8_t port;
    uint8_t pad[45];
    uint64_t timestamp;
    uint8_t pad_[7];
    uint8_t own_type;
    uint8_t data[];
};

union cosim_eth_proto_n2d {
    struct cosim_eth_proto_n2d_dummy dummy;
    struct cosim_eth_proto_n2d_sync sync;
    struct cosim_eth_proto_n2d_recv recv;
};

#endif /* ndef COSIM_ETH_PROTO_H_ */

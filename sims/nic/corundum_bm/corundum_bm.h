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

#pragma once

#include <list>
#include <vector>
#include <stdint.h>
extern "C" {
#include <simbricks/proto/pcie.h>
}
#include <simbricks/nicbm/nicbm.h>

typedef uint32_t reg_t;
typedef uint64_t addr_t;
typedef uint16_t ptr_t;

#define REG_FW_ID                   0x0000
#define REG_FW_VER                  0x0004
#define REG_BOARD_ID                0x0008
#define REG_BOARD_VER               0x000C
#define REG_PHC_COUNT               0x0010
#define REG_PHC_OFFSET              0x0014
#define REG_PHC_STRIDE              0x0018
#define REG_IF_COUNT                0x0020
#define REG_IF_STRIDE               0x0024
#define REG_IF_CSR_OFFSET           0x002C

#define IF_FEATURE_RSS              (1 << 0)
#define IF_FEATURE_PTP_TS           (1 << 4)
#define IF_FEATURE_TX_CSUM          (1 << 8)
#define IF_FEATURE_RX_CSUM          (1 << 9)
#define IF_FEATURE_RX_HASH          (1 << 10)

#define PHC_REG_FEATURES            0x0200
#define PHC_REG_PTP_CUR_SEC_L       0x0218
#define PHC_REG_PTP_CUR_SEC_H       0x021C
#define PHC_REG_PTP_SET_FNS         0x0230
#define PHC_REG_PTP_SET_NS          0x0234
#define PHC_REG_PTP_SET_SEC_L       0x0238
#define PHC_REG_PTP_SET_SEC_H       0x023C

#define IF_REG_IF_ID                0x80000
#define IF_REG_IF_FEATURES          0x80004
#define IF_REG_EVENT_QUEUE_COUNT    0x80010
#define IF_REG_EVENT_QUEUE_OFFSET   0x80014
#define IF_REG_TX_QUEUE_COUNT       0x80020
#define IF_REG_TX_QUEUE_OFFSET      0x80024
#define IF_REG_TX_CPL_QUEUE_COUNT   0x80028
#define IF_REG_TX_CPL_QUEUE_OFFSET  0x8002C
#define IF_REG_RX_QUEUE_COUNT       0x80030
#define IF_REG_RX_QUEUE_OFFSET      0x80034
#define IF_REG_RX_CPL_QUEUE_COUNT   0x80038
#define IF_REG_RX_CPL_QUEUE_OFFSET  0x8003C
#define IF_REG_PORT_COUNT           0x80040
#define IF_REG_PORT_OFFSET          0x80044
#define IF_REG_PORT_STRIDE          0x80048

#define QUEUE_ACTIVE_MASK 0x80000000
#define QUEUE_ARM_MASK 0x80000000
#define QUEUE_CONT_MASK 0x40000000

#define EVENT_QUEUE_BASE_ADDR_REG       0x100000
#define EVENT_QUEUE_ACTIVE_LOG_SIZE_REG 0x100008
#define EVENT_QUEUE_INTERRUPT_INDEX_REG 0x10000C
#define EVENT_QUEUE_HEAD_PTR_REG        0x100010
#define EVENT_QUEUE_TAIL_PTR_REG        0x100018

#define TX_QUEUE_BASE_ADDR_REG       0x200000
#define TX_QUEUE_ACTIVE_LOG_SIZE_REG 0x200008
#define TX_QUEUE_CPL_QUEUE_INDEX_REG 0x20000C
#define TX_QUEUE_HEAD_PTR_REG        0x200010
#define TX_QUEUE_TAIL_PTR_REG        0x200018

#define TX_CPL_QUEUE_BASE_ADDR_REG       0x400000
#define TX_CPL_QUEUE_ACTIVE_LOG_SIZE_REG 0x400008
#define TX_CPL_QUEUE_INTERRUPT_INDEX_REG 0x40000C
#define TX_CPL_QUEUE_HEAD_PTR_REG        0x400010
#define TX_CPL_QUEUE_TAIL_PTR_REG        0x400018

#define RX_QUEUE_BASE_ADDR_REG       0x600000
#define RX_QUEUE_ACTIVE_LOG_SIZE_REG 0x600008
#define RX_QUEUE_CPL_QUEUE_INDEX_REG 0x60000C
#define RX_QUEUE_HEAD_PTR_REG        0x600010
#define RX_QUEUE_TAIL_PTR_REG        0x600018

#define RX_CPL_QUEUE_BASE_ADDR_REG       0x700000
#define RX_CPL_QUEUE_ACTIVE_LOG_SIZE_REG 0x700008
#define RX_CPL_QUEUE_INTERRUPT_INDEX_REG 0x70000C
#define RX_CPL_QUEUE_HEAD_PTR_REG        0x700010
#define RX_CPL_QUEUE_TAIL_PTR_REG        0x700018

#define PORT_REG_PORT_ID                    0x800000
#define PORT_REG_PORT_FEATURES              0x800004
#define PORT_REG_PORT_MTU                   0x800008
#define PORT_REG_SCHED_COUNT                0x800010
#define PORT_REG_SCHED_OFFSET               0x800014
#define PORT_REG_SCHED_STRIDE               0x800018
#define PORT_REG_SCHED_TYPE                 0x80001C
#define PORT_REG_SCHED_ENABLE               0x800040
#define PORT_REG_RSS_MASK                   0x800080

#define PORT_QUEUE_ENABLE   0x900000

namespace corundum {

#define DESC_SIZE 16
#define CPL_SIZE 32
#define EVENT_SIZE 32
#define MAX_DMA_LEN 2048

class DescRing;

struct Desc {
    uint16_t rsvd0;
    uint16_t tx_csum_cmd;
    uint32_t len;
    uint64_t addr;
} __attribute__((packed)) ;

struct Cpl {
    uint16_t queue;
    uint16_t index;
    uint16_t len;
    uint16_t rsvd0;
    uint32_t ts_ns;
    uint16_t ts_s;
    uint16_t rx_csum;
    uint32_t rx_hash;
    uint8_t rx_hash_type;
    uint8_t rsvd1;
    uint8_t rsvd2;
    uint8_t rsvd3;
    uint32_t rsvd4;
    uint32_t rsvd5;
} __attribute__((packed)) ;

#define EVENT_TYPE_TX_CPL 0x0000
#define EVENT_TYPE_RX_CPL 0x0001

struct Event {
    uint16_t type;
    uint16_t source;
} __attribute__((packed)) ;

struct RxData {
    size_t len;
    uint8_t data[MAX_DMA_LEN];
};

#define DMA_TYPE_DESC   0
#define DMA_TYPE_MEM    1
#define DMA_TYPE_TX_CPL 2
#define DMA_TYPE_RX_CPL 3
#define DMA_TYPE_EVENT  4

struct DMAOp : public nicbm::DMAOp {
    DMAOp() {
        data = databuf;
    }

    uint8_t type;
    DescRing *ring;
    RxData *rx_data;
    uint64_t tag;
    uint8_t databuf[MAX_DMA_LEN];
};

class DescRing {
public:
    DescRing();
    ~DescRing();

    addr_t dmaAddr();
    size_t sizeLog();
    unsigned index();
    ptr_t headPtr();
    ptr_t tailPtr();

    void setDMALower(uint32_t addr);
    void setDMAUpper(uint32_t addr);
    void setSizeLog(size_t size_log);
    void setIndex(unsigned index);
    virtual void setHeadPtr(ptr_t ptr);
    void setTailPtr(ptr_t ptr);

    virtual void dmaDone(DMAOp *op) = 0;

protected:
    bool empty();
    bool full();
    bool updatePtr(ptr_t ptr, bool head);

    addr_t _dmaAddr;
    size_t _sizeLog;
    size_t _size;
    size_t _sizeMask;
    unsigned _index;
    ptr_t _headPtr;
    ptr_t _tailPtr;
    ptr_t _currHead;
    ptr_t _currTail;
    bool active;
    bool armed;
    std::vector<bool> cplDma;
};

class EventRing : public DescRing {
public:
    EventRing();
    ~EventRing();

    virtual void dmaDone(DMAOp *op) override;
    void issueEvent(unsigned type, unsigned source);
};

class CplRing : public DescRing {
public:
    CplRing(EventRing *eventRing);
    ~CplRing();

    virtual void dmaDone(DMAOp *op) override;
    void complete(unsigned index, size_t len, bool tx);

private:
    struct CplData {
        unsigned index;
        size_t len;
        bool tx;
    };
    EventRing *eventRing;
    std::list<CplData> pending;
};

class TxRing : public DescRing {
public:
    TxRing(CplRing *cplRing);
    ~TxRing();

    virtual void setHeadPtr(ptr_t ptr) override;
    virtual void dmaDone(DMAOp *op) override;

private:
    CplRing *txCplRing;
};

class RxRing : public DescRing {
public:
    RxRing(CplRing *cplRing);
    ~RxRing();

    virtual void dmaDone(DMAOp *op) override;
    void rx(RxData *rx_data);

private:
    CplRing *rxCplRing;
};

class Port {
public:
    Port();
    ~Port();

    unsigned id();
    unsigned features();
    size_t mtu();
    size_t schedCount();
    addr_t schedOffset();
    addr_t schedStride();
    unsigned schedType();
    unsigned rssMask();

    void setId(unsigned id);
    void setFeatures(unsigned features);
    void setMtu(size_t mtu);
    void setSchedCount(size_t count);
    void setSchedOffset(addr_t offset);
    void setSchedStride(addr_t stride);
    void setSchedType(unsigned type);
    void setRssMask(unsigned mask);
    void schedEnable();
    void schedDisable();
    void queueEnable();
    void queueDisable();

private:
    unsigned _id;
    unsigned _features;
    size_t _mtu;
    size_t _schedCount;
    addr_t _schedOffset;
    addr_t _schedStride;
    unsigned _schedType;
    unsigned _rssMask;
    bool _schedEnable;
    bool _queueEnable;
};

class Corundum : public nicbm::SimpleDevice<reg_t> {
public:
    Corundum();
    ~Corundum();

    virtual void setup_intro(struct cosim_pcie_proto_dev_intro &di);
    virtual reg_t reg_read(uint8_t bar, addr_t addr);
    virtual void reg_write(uint8_t bar, addr_t addr, reg_t val);
    virtual void dma_complete(nicbm::DMAOp &op);
    virtual void eth_rx(uint8_t port, const void *data, size_t len);

private:
    EventRing eventRing;
    TxRing txRing;
    CplRing txCplRing;
    RxRing rxRing;
    CplRing rxCplRing;
    Port port;
    uint32_t features;
};

} // namespace corundum

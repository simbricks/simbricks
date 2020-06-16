#pragma once

#include <stdint.h>

typedef uint32_t reg_t;
typedef uint64_t addr_t;

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
#define MAX_DMA_LEN 2048
#define HW_PTR_MASK 0xFFFF

class DescRing;

struct Desc {
    uint16_t rsvd0;
    uint16_t tx_csum_cmd;
    uint32_t len;
    uint64_t addr;
} __attribute__((packed)) ;


#define DMA_TYPE_DESC 0
#define DMA_TYPE_MEM  1

struct DMAOp {
    uint8_t type;
    addr_t dma_addr;
    size_t len;
    DescRing *ring;
    uint64_t tag;
    bool write;
    uint8_t data[MAX_DMA_LEN];
};

class DescRing {
public:
    DescRing();
    ~DescRing();

    addr_t dmaAddr();
    size_t sizeLog();
    unsigned index();
    unsigned headPtr();
    unsigned tailPtr();

    void setDMALower(uint32_t addr);
    void setDMAUpper(uint32_t addr);
    void setSizeLog(size_t size_log);
    void setIndex(unsigned index);
    virtual void setHeadPtr(unsigned ptr);
    void setTailPtr(unsigned ptr);

    virtual void dmaDone(DMAOp *op);

protected:
    bool empty();

    addr_t _dmaAddr;
    size_t _sizeLog;
    size_t _size;
    size_t _sizeMask;
    unsigned _index;
    unsigned _headPtr;
    unsigned _tailPtr;
    bool active;
};

class TxRing : public DescRing {
public:
    TxRing();
    ~TxRing();

    virtual void setHeadPtr(unsigned ptr) override;
    virtual void dmaDone(DMAOp *op) override;
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

class Corundum {
public:
    Corundum();
    ~Corundum();

    reg_t readReg(addr_t addr);
    void writeReg(addr_t addr, reg_t val);

private:
    DescRing eqRing;
    TxRing txRing;
    DescRing txCplRing;
    DescRing rxRing;
    DescRing rxCplRing;
    Port port;
};

} // namespace corundum

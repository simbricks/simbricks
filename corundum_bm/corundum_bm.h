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
    void setHeadPtr(unsigned ptr);
    void setTailPtr(unsigned ptr);

private:
    addr_t _dmaAddr;
    size_t _sizeLog;
    size_t _size;
    unsigned _index;
    unsigned _headPtr;
    unsigned _tailPtr;
};

class Corundum {
public:
    Corundum();
    ~Corundum();

    reg_t readReg(addr_t addr);
    void writeReg(addr_t addr, reg_t val);

private:
    DescRing eqRing;
    DescRing txRing;
    DescRing txCqRing;
    DescRing rxRing;
    DescRing rxCqRing;
};

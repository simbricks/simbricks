#ifndef SIMS_NIC_E1000_GEM5_SUPPORT_H_
#define SIMS_NIC_E1000_GEM5_SUPPORT_H_

#include <arpa/inet.h>
#include <functional>
#include <memory>

#include <simbricks/nicbm/nicbm.h>

#define DNET_LIL_ENDIAN 42
#define DNET_BYTESEX DNET_LIL_ENDIAN

//#define DEBUG_E1000
#ifdef DEBUG_E1000
#   define DPRINTF(x,y...) fprintf(stderr, #x ": " y)
#else
#   define DPRINTF(x,y...) do { } while (0)
#endif


typedef uint64_t Addr;
typedef uint64_t Tick;

#define ETH_ADDR_LEN 6

class Gem5TimerEv;

class EthPacketData {
  public:
    unsigned length;
    uint8_t *data;

    EthPacketData(unsigned len) : length(0), data(new uint8_t[len]) { }
    ~EthPacketData() { delete[] data; }
};
typedef std::shared_ptr<EthPacketData> EthPacketPtr;

class EventFunctionWrapper : public nicbm::TimedEvent {
  public:
    bool sched;
    std::function<void(void)> callback;
    std::string _name;

    EventFunctionWrapper(const std::function<void(void)> &callback,
                         const std::string &name)
        : sched(false), callback(callback), _name(name)
    { }

    virtual ~EventFunctionWrapper() = default;
    bool scheduled() { return sched; }
};

static inline uint16_t htobe(uint16_t x) {
  return htons(x);
}

static inline uint16_t htole(uint16_t x) {
  return x;
}

void warn(const char *fmt, ...);
void panic(const char *fmt, ...);

#endif  // SIMS_NIC_E1000_GEM5_SUPPORT_H_
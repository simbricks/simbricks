#pragma once

#include <stdint.h>

typedef uint32_t reg_t;
typedef uint64_t addr_t;

class Corundum {
public:
    Corundum();
    ~Corundum();

    reg_t readReg(addr_t addr);
    void writeReg(addr_t addr, reg_t val);

private:

};

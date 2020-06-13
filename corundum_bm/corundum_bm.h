#pragma once

#include <stdint.h>

#define REG_A 0x0
#define REG_B 0x4
#define REG_C 0x10
#define REG_D 0x14
#define REG_E 0x20
#define REG_F 0x24
#define REG_G 0x28
#define REG_H 0x2c
#define REG_I 0x30
#define REG_J 0x34
#define REG_K 0x38
#define REG_L 0x3c
#define REG_M 0x40
#define REG_N 0x44
#define REG_O 0x48

struct CorundumRegs {
    uint32_t reg_a;
    uint32_t reg_b;
    uint32_t reg_c;
    uint32_t reg_d;
    uint32_t reg_e;
    uint32_t reg_f;
    uint32_t reg_g;
    uint32_t reg_h;
    uint32_t reg_i;
    uint32_t reg_j;
    uint32_t reg_k;
    uint32_t reg_l;
    uint32_t reg_m;
    uint32_t reg_n;
    uint32_t reg_o;
};

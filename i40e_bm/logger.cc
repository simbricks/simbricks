#include <iostream>

#include "i40e_bm.h"

using namespace i40e;

extern nicbm::Runner *runner;

logger::logger(const std::string &label_)
    : label(label_)
{
}

logger &logger::operator<<(char c)
{
    if (c == endl) {
        std::cerr << runner->time_ps() << " " << label << ": " << ss.str() <<
            std::endl;
    } else {
        ss << c;
    }
    return *this;
}

logger &logger::operator<<(int32_t i)
{
    ss << i;
    return *this;
}

logger &logger::operator<<(uint8_t i)
{
    ss << (unsigned) i;
    return *this;
}

logger &logger::operator<<(uint16_t i)
{
    ss << i;
    return *this;
}

logger &logger::operator<<(uint32_t i)
{
    ss << i;
    return *this;
}

logger &logger::operator<<(uint64_t i)
{
    ss << i;
    return *this;
}

logger &logger::operator<<(bool b)
{
    ss << b;
    return *this;
}

logger &logger::operator<<(const char *str)
{
    ss << str;
    return *this;
}

logger &logger::operator<<(void *ptr)
{
    ss << ptr;
    return *this;
}

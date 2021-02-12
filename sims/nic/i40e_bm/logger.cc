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

#include <iostream>

#include "sims/nic/i40e_bm/i40e_bm.h"

using namespace i40e;

extern nicbm::Runner *runner;

logger::logger(const std::string &label_)
    : label(label_)
{
    ss << std::hex;
}

logger &logger::operator<<(char c)
{
    if (c == endl) {
        std::cerr << runner->time_ps() << " " << label << ": " << ss.str() <<
            std::endl;
        ss.str(std::string());
        ss << std::hex;
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

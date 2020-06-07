CPPFLAGS += -I../nicsim_common/include -I../proto
CFLAGS += -Wall -Wextra -Wno-unused-parameter -O3

dummy_nic: dummy_nic.o ../nicsim_common/libnicsim_common.a

all: dummy_nic

clean:
	rm -f *.o dummy_nic

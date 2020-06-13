CPPFLAGS += -I../proto -I../netsim_common/include
CFLAGS += -Wall -Wextra -Wno-unused-parameter -O3

net_wire: net_wire.o ../netsim_common/libnetsim_common.a

all: net_wire

clean:
	rm -f *.o net_wire

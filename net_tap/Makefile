CPPFLAGS += -I../proto -I../netsim_common/include
CFLAGS += -Wall -Wextra -Wno-unused-parameter -O3
LDLIBS += -lpthread

net_tap: net_tap.o ../netsim_common/libnetsim_common.a

all: net_tap

clean:
	rm -f *.o net_tap

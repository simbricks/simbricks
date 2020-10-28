CPPFLAGS := -I../proto -I../netsim_common/include
CFLAGS := -Wall -Wextra -O3
LD := g++

all: net_switch

net_switch: net_switch.o ../netsim_common/libnetsim_common.a
	$(LD) -o $@ $^

clean:
	rm -f *.o net_switch

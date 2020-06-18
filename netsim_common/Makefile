CPPFLAGS += -I include/ -I../proto/
CFLAGS += -Wall -Wextra -Wno-unused-parameter -O3 -fPIC

all: libnetsim_common.a

libnetsim_common.a: netsim.o utils.o
	$(AR) rcs $@ $^

clean:
	rm -rf libnetsim_common.a *.o

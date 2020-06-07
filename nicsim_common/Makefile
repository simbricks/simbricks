CPPFLAGS += -I include/ -I../proto/
CFLAGS += -Wall -Wextra -Wno-unused-parameter -O3

all: libnicsim_common.a

libnicsim_common.a: nicsim.o utils.o
	$(AR) rcs $@ $^

clean:
	rm -rf libnicsim_common.a nicsim.o utils.o

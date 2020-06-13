CPPFLAGS += -I../nicsim_common/include -I../proto
CFLAGS += -Wall -Wextra -Wno-unused-parameter -O3

all: corundum_bm tester

corundum_bm: corundum_bm.o ../nicsim_common/libnicsim_common.a

tester: tester.o ../nicsim_common/libnicsim_common.a

clean:
	rm -f *.o corundum_bm tester

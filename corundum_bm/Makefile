CPPFLAGS += -I../nicsim_common/include -I../netsim_common/include -I../proto
CPPFLAGS += -I../libnicbm/include/
CFLAGS += -Wall -Wextra -Wno-unused-parameter -O3

all: corundum_bm tester

corundum.o: corundum.cc
	g++ $(CFLAGS) $(CPPFLAGS) -c -o $@ $<

corundum_bm: corundum_bm.o ../libnicbm/libnicbm.a ../nicsim_common/libnicsim_common.a
	g++ $^ -o $@

tester: tester.o ../libnicbm/libnicbm.a ../nicsim_common/libnicsim_common.a

clean:
	rm -f *.o corundum_bm tester

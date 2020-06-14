CPPFLAGS += -I../nicsim_common/include -I../proto
CFLAGS += -Wall -Wextra -Wno-unused-parameter -O3

all: corundum_bm tester

corundum.o: corundum.cc
	g++ $(CFLAGS) $(CPPFLAGS) -c -o $@ $<

corundum_bm: corundum_bm.o ../nicsim_common/libnicsim_common.a
	g++ $^ -o $@ -lm -lstdc++

tester: tester.o ../nicsim_common/libnicsim_common.a

clean:
	rm -f *.o corundum_bm tester

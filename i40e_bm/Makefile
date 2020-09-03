CPPFLAGS += -I../nicsim_common/include -I../proto
CPPFLAGS += -I../libnicbm/include/
CXXFLAGS += -Wall -Wextra -Wno-unused-parameter -O3 -g
LDFLGAS = -g

OBJS := i40e_bm.o i40e_queues.o i40e_adminq.o i40e_hmc.o i40e_lan.o xsums.o

all: i40e_bm

i40e_bm: $(OBJS) ../libnicbm/libnicbm.a ../nicsim_common/libnicsim_common.a
i40e_bm: CC=$(CXX)

clean:
	rm -f *.o i40e_bm

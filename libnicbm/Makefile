CPPFLAGS += -I include/ -I../proto/ -I../nicsim_common/include/
CPPFLAGS += -I../libnicbm/include/
CXXFLAGS += -Wall -Wextra -Wno-unused-parameter -O3

OBJS := nicbm.o

all: libnicbm.a

libnicbm.a: $(OBJS)
	$(AR) rcs $@ $^

clean:
	rm -rf libnicbm.a $(OBJS)

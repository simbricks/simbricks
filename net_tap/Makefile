CPPFLAGS += -I../proto
CFLAGS += -Wall -Wextra -Wno-unused-parameter -O3
LDLIBS += -lpthread

net_tap: net_tap.o

all: net_tap

clean:
	rm -f *.o net_tap

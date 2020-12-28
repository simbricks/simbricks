CXXFLAGS := -O3 -Wall -Wextra -g -Wno-unused-parameter -fpermissive
LDLIBS := -lboost_iostreams

process: process.o sym_map.o log_parser.o gem5.o nicbm.o
process: CC=$(CXX)

clean:
	rm *.o process

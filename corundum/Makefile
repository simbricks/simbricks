CXXFLAGS = -Wall

VERILATOR = verilator
VFLAGS = +1364-2005ext+v \
    -Wno-WIDTH -Wno-PINMISSING -Wno-LITENDIAN -Wno-IMPLICIT -Wno-SELRANGE \
    -Wno-CASEINCOMPLETE -Wno-UNSIGNED

SRCS = corundum_verilator.cpp

all: corundum_verilator

obj_dir/Vinterface.cpp: rtl/interface.v
	$(VERILATOR) $(VFLAGS) --cc -O3 \
	    -CFLAGS "-I$(PWD)/../nicsim_common/include -I$(PWD)/../proto -O3" \
	    -y rtl \
	    -y lib/axi/rtl \
	    -y lib/eth/lib/axis/rtl/ \
	    -y ./lib/pcie/rtl \
	    rtl/interface.v --exe $(SRCS) "$(PWD)/../nicsim_common/libnicsim_common.a"

obj_dir/Vinterface: obj_dir/Vinterface.cpp $(SRCS)
	 $(MAKE) -C obj_dir -f Vinterface.mk

corundum_verilator: obj_dir/Vinterface
	cp $< $@

#obj_dir/%.o: CXXFLAGS += -Wno-all
#obj_dir/%.o: CPPFLAGS += -I /usr/share/verilator/include/
#
#obj_dir/verilated.o: /usr/share/verilator/include/verilated.cpp
#	$(CXX) $(CXXFLAGS) -c $< -o $@
#
#obj_dir/verilated_vcd_c.o: /usr/share/verilator/include/verilated_vcd_c.cpp
#	$(CXX) $(CXXFLAGS) -c $< -o $@
#
#corundum_verilator: corundum_verilator.o obj_dir/verilated.o \
#	    obj_dir/verilated_vcd_c.o obj_dir/Vinterface.o \
#	    obj_dir/Vinterface__Syms.o obj_dir/Vinterface__Trace.o \
#	    obj_dir/Vinterface__Trace__Slow.o
#	$(CXX) $(CXXFLAGS) $(LDFLAGS) -o $@ $^ $(LDLIBS)

clean:
	rm -rf obj_dir corundum_verilator *.o

.PHONY: all clean

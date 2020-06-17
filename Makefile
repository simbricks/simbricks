all: \
	corundum/corundum_verilator \
	corundum_bm/corundum_bm \
	net_tap/net_tap \
	net_wire/net_wire

clean:
	make -C corundum/ clean
	make -C corundum_bm/ clean
	make -C net_tap/ clean
	make -C net_wire/ clean
	make -C nicsim_common/ clean
	make -C netsim_common/ clean

corundum/corundum_verilator: nicsim_common/libnicsim_common.a
	make -C corundum/ all

corundum_bm/corundum_bm: nicsim_common/libnicsim_common.a
	make -C corundum_bm/ all

net_tap/net_tap: netsim_common/libnetsim_common.a
	make -C net_tap/

net_wire/net_wire: netsim_common/libnetsim_common.a
	make -C net_wire/

nicsim_common/libnicsim_common.a:
	make -C nicsim_common/

netsim_common/libnetsim_common.a:
	make -C netsim_common/

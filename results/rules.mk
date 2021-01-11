all: build/results.tex build/simtime_graph.dat

clean:
	rm -rf build

build/results.tex: build/loc_corundum_bm build/loc_corundum_verilator \
    build/nopaxos_eval build/vr_eval build/corundum_eval
	@echo '%' This is generated with make in the results directory \
	    of the ehsim repo >$@
	cat $^ >>$@

# Lines of code in corundum
build/loc_corundum_bm: loccount_corundum_bm.sh common-functions.sh
	@mkdir -p $(dir $@)
	bash loccount_corundum_bm.sh >$@

build/loc_corundum_verilator: loccount_corundum_verilator.sh common-functions.sh
	@mkdir -p $(dir $@)
	bash loccount_corundum_verilator.sh >$@

build/nopaxos_eval: nopaxos_eval.sh common-functions.sh
	@mkdir -p $(dir $@)
	bash nopaxos_eval.sh >$@

build/vr_eval: vr_eval.sh common-functions.sh
	@mkdir -p $(dir $@)
	bash vr_eval.sh >$@

build/corundum_eval: corundum.sh common-functions.sh
	@mkdir -p $(dir $@)
	bash corundum.sh >$@

build/simtime_graph.dat: simtime_graph.sh common-functions
	@mkdir -p $(dir $@)
	bash simtime_graph.sh >$@

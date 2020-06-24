all: build/results.tex

clean:
	rm -rf build

build/results.tex: build/loc_corundum_bm build/loc_corundum_verilator
	@echo '%' This is generated with make in the results directory \
	    of the ehsim repo >$@
	cat $^ >>$@

# Lines of code in corundum
build/loc_corundum_bm: loccount_corundum_bm.sh
	@mkdir -p $(dir $@)
	bash loccount_corundum_bm.sh >$@

build/loc_corundum_verilator: loccount_corundum_verilator.sh
	@mkdir -p $(dir $@)
	bash loccount_corundum_verilator.sh >$@

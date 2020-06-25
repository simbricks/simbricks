MQNICMOD := $(abspath ../images/mqnic/mqnic.ko)

GUESTS := \
    qemu-pair-client \
    qemu-pair-server \
    gem5-pair-client \
    gem5-pair-server-cp \
    gem5-pair-client-cp \
	qemu-nopaxos-replica-0 \
	qemu-nopaxos-replica-1 \
	qemu-nopaxos-replica-2 \
	qemu-nopaxos-client \
	gem5-nopaxos-client \
	gem5-nopaxos-replica-0-cp \
	gem5-nopaxos-replica-1-cp \
	gem5-nopaxos-replica-2-cp \
	gem5-nopaxos-client-cp \
	qemu-vr-replica-0 \
	qemu-vr-replica-1 \
	qemu-vr-replica-2 \
	qemu-vr-client \
	gem5-vr-replica-0-cp \
	gem5-vr-replica-1-cp \
	gem5-vr-replica-2-cp \
	gem5-vr-client-cp \


EXPERIMENTS := \
    qemu-corundum-bm-pair \
    qemu-corundum-verilator-pair \
    gem5-kvm-corundum-bm-pair \
    gem5-timing-corundum-verilator-pair \
    qemu-ns3-bridge-pair \
    qemu-ns3-dumbbell-pair \
    gem5-kvm-ns3-dumbbell-pair \

REPLICATION ?= 1

BUILDDIR := build
OUTDIR := out

GUESTS_TARS := $(addprefix $(BUILDDIR)/,$(addsuffix .tar, $(GUESTS)))
EXPERIMENTS_READY := $(addprefix $(OUTDIR)/,$(addsuffix /ready,$(EXPERIMENTS)))

all: $(GUESTS_TARS) $(EXPERIMENTS_READY)

clean:
	rm -rf $(BUILDDIR) $(OUTDIR)

#######################################
# Running experiments

define run_experiment_repl
$(OUTDIR)/%/$(1)/ready: experiments/%.sh $(GUESTS_TARS)
	bash $$< $(1)
	touch $$@
endef

REPLIDS := $(shell seq $(REPLICATION))

$(foreach i,$(REPLIDS), $(eval $(call run_experiment_repl,$(i))))

$(OUTDIR)/%/ready: experiments/%.sh $(addprefix $(OUTDIR)/%/,$(addsuffix /ready,$(REPLIDS)))
	touch $@

#######################################
# Guest Tars

guest-tars: $(GUESTS_TARS)

define build_guest
$(1)_OBJS := $(wildcard guests/$(1)/*)
$(BUILDDIR)/$(1).tar: $$($(1)_OBJS)
	rm -rf $(BUILDDIR)/$(1)
	mkdir -p $(BUILDDIR)/$(1)/guest
	cp $(MQNICMOD) $(BUILDDIR)/$(1)/guest/
	cp $$($(1)_OBJS) $(BUILDDIR)/$(1)/guest/
	cd $(BUILDDIR)/$(1) && tar cf $$(abspath $$@) guest/
	rm -rf $(BUILDDIR)/$(1)
endef

$(foreach guest,$(GUESTS), $(eval $(call build_guest,$(guest))))

MQNICMOD := $(abspath ../images/mqnic/mqnic.ko)
EXP_RUNNER ?= bash

GUESTS := \
    qemu-pair-client \
    qemu-pair-client-8-1 \
    qemu-pair-client-8-2 \
    qemu-pair-client-8-3 \
    qemu-pair-client-8-4 \
    qemu-pair-client-8-5 \
    qemu-pair-client-8-6 \
    qemu-pair-client-8-7 \
    qemu-pair-client-8-8 \
    qemu-pair-server \
    gem5-pair-client \
    gem5-pair-server-cp \
    gem5-pair-client-cp \
    gem5-pair-client-8-1 \
    gem5-pair-client-8-2 \
    gem5-pair-client-8-3 \
    gem5-pair-client-8-4 \
    gem5-pair-client-8-5 \
    gem5-pair-client-8-6 \
    gem5-pair-client-8-7 \
    gem5-pair-client-8-8 \
    gem5-pair-server-udp \
    gem5-pair-client-udp-0m \
    gem5-pair-client-udp-10m \
    gem5-pair-client-udp-30m \
    gem5-pair-client-udp-50m \
    gem5-pair-client-udp-80m \
    gem5-pair-client-udp-100m \
    gem5-pair-client-udp-120m \
    gem5-pair-client-udp-150m \
	qemu-nopaxos-replica-0 \
	qemu-nopaxos-replica-1 \
	qemu-nopaxos-replica-2 \
	qemu-nopaxos-client \
	qemu-nopaxos-endhost-sequencer \
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
    qemu-mtcp-server \
    qemu-mtcp-client \
    gem5-pair-i40e-server \
    gem5-pair-i40e-client \
    gem5-pair-i40e-client-2 \
    qemu-pair-i40e-server \
    qemu-pair-i40e-client \
    qemu-pair-i40e-client-2 \
    qemu-i40e-rpc-server \
    qemu-i40e-rpc-client \
    qemu-tas-server \
    qemu-tas-client \
    qemu-echo-client \
    qemu-echo-server-0 \
    qemu-echo-server-1 \
    qemu-echo-server-2 \

# experiments we want for the paper
EXPERIMENTS := \
    qemu-ns3-nopaxos \
    qemu-ns3-nopaxos-verilator \
    gem5-timing-corundum-verilator-ns3-nopaxos-nocp \
    gem5-timing-corundum-bm-ns3-nopaxos-nocp \
    qemu-ns3-vr \
    qemu-ns3-vr-verilator \
    gem5-timing-corundum-verilator-ns3-vr-nocp \
    gem5-timing-corundum-bm-ns3-vr-nocp \
    qemu-corundum-bm-switched-1 \
    qemu-corundum-bm-switched-8 \
    qemu-corundum-verilator-switched-1 \
    qemu-corundum-verilator-switched-8 \
    gem5-timing-corundum-verilator-switched-1-nocp \
    gem5-timing-corundum-verilator-switched-8-nocp \
    gem5-timing-corundum-verilator-pair-udp-0m \
    gem5-timing-corundum-verilator-pair-udp-10m \
    gem5-timing-corundum-verilator-pair-udp-30m \
    gem5-timing-corundum-verilator-pair-udp-50m \
    gem5-timing-corundum-verilator-pair-udp-80m \
    gem5-timing-corundum-verilator-pair-udp-100m \
    gem5-timing-corundum-verilator-pair-udp-150m \


#experiments using check points
EXP_CP := \
    gem5-timing-corundum-verilator-pair-cp \
    gem5-i40e-pair \
    gem5-i40e-mtcp \
    gem5-i40e-cc \

#experiments not using check points
EXP_NCP := \
    qemu-corundum-bm-echo-switch \
    qemu-corundum-bm-pair \
    qemu-corundum-bm-switched-1 \
    qemu-i40e-bm-mtcp \
    qemu-i40e-bm-rpc \
    qemu-i40e-bm-pair \
    qemu-i40e-bm-tas \
    qemu-i40e-bm-cc \
    qemu-ns3-nopaxos \
    qemu-ns3-nopaxos-endhost-sequencer \

# all experiments in repo
ALL_EXPERIMENTS := \
    $(EXPERIMENTS) \
    qemu-corundum-bm-pair \
    qemu-corundum-verilator-pair \
    gem5-kvm-corundum-bm-pair \
    gem5-timing-corundum-verilator-pair \
    qemu-ns3-bridge-pair \
    qemu-ns3-dumbbell-pair \
    gem5-kvm-ns3-dumbbell-pair \
    gem5-kvm-corundum-verilator-pair \
    gem5-timing-corundum-verilator-pair-udp \
    gem5-timing-corundum-verilator-pair-largewin \
    gem5-timing-corundum-verilator-pair-16f \


REPLICATION ?= 1

BUILDDIR := build
OUTDIR := out

GUESTS_TARS := $(addprefix $(BUILDDIR)/,$(addsuffix .tar, $(GUESTS)))
EXPERIMENTS_READY := $(addprefix $(OUTDIR)/,$(addsuffix /ready,$(EXPERIMENTS)))
EXP_CP_READY := $(addprefix $(OUTDIR)/,$(addsuffix /ready,$(EXP_CP)))
EXP_NCP_READY := $(addprefix $(OUTDIR)/,$(addsuffix /ready,$(EXP_NCP)))

all: guest-tars experiments

clean:
	rm -rf $(BUILDDIR) $(OUTDIR)

#######################################
# Running experiments

REPLIDS := $(shell seq $(REPLICATION))
experiments-ncp: $(EXP_NCP_READY)
experiments-cp: $(EXP_CP_READY)
experiments: $(EXPERIMENTS_READY)

define run_ex_ncp_repl
$(OUTDIR)/$(1)/$(2)/ready: experiments/$(addsuffix .sh,$(1)) $(GUESTS_TARS)
	$(EXP_RUNNER) $$< $(2)
	@# hacks for our NFS :/
	@ls $(OUTDIR) >/dev/null
	@ls $(OUTDIR)/$(1) >/dev/null
	@ls $(OUTDIR)/$(1)/$(2) >/dev/null
	touch $$@

endef

define run_ex_ncp
$(foreach i,$(REPLIDS),$(eval $(call run_ex_ncp_repl,$(1),$(i))))
$(OUTDIR)/$(1)/ready: experiments/$(addsuffix .sh,$(1)) $(addprefix $(OUTDIR)/$(1)/,$(addsuffix /ready,$(REPLIDS)))
	touch $$@
endef

define run_ex_cp_repl
$(OUTDIR)/$(1)/$(2)/ready: experiments/$(addsuffix .sh,$(1)) $(OUTDIR)/$(1)/checkpoint/ready $(GUESTS_TARS)
	$(EXP_RUNNER) $$< $(2)
	@# hacks for our NFS :/
	@ls $(OUTDIR) >/dev/null
	@ls $(OUTDIR)/$(1) >/dev/null
	@ls $(OUTDIR)/$(1)/$(2) >/dev/null
	touch $$@
endef

define run_ex_cp
$(foreach i,$(REPLIDS),$(eval $(call run_ex_cp_repl,$(1),$(i))))

$(OUTDIR)/$(1)/checkpoint/ready: experiments/$(addsuffix -mck.sh,$(1)) $(GUESTS_TARS)
	$(EXP_RUNNER) $$<
	@# hacks for our NFS :/
	@ls $(OUTDIR) >/dev/null
	@ls $(OUTDIR)/$(1) >/dev/null
	@ls $(OUTDIR)/$(1)/$(2) >/dev/null
	touch $$@

$(OUTDIR)/$(1)/ready: experiments/$(addsuffix .sh,$(1)) $(addprefix $(OUTDIR)/$(1)/,$(addsuffix /ready,$(REPLIDS)))
	touch $$@

endef
$(foreach sc, $(EXP_CP),$(eval $(call run_ex_cp,$(sc))))
$(foreach sc, $(EXP_NCP),$(eval $(call run_ex_ncp,$(sc))))

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

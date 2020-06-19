MQNICMOD := $(abspath ../images/mqnic/mqnic.ko)

GUESTS := \
    qemu-pair-client \
    qemu-pair-server \
    gem5-pair-client \
    gem5-pair-server-cp \
    gem5-pair-client-cp \

EXPERIMENTS := \
    qemu-corundum-bm-pair \
    qemu-corundum-verilator-pair \
    gem5-kvm-corundum-bm-pair \
    gem5-timing-corundum-verilator-pair \

BUILDDIR := build
OUTDIR := out

GUESTS_TARS := $(addprefix $(BUILDDIR)/,$(addsuffix .tar, $(GUESTS)))
EXPERIMENTS_READY := $(addprefix $(OUTDIR)/,$(addsuffix /ready,$(EXPERIMENTS)))

all: $(GUESTS_TARS) $(EXPERIMENTS_READY)

clean:
	rm -rf $(BUILDDIR) $(OUTDIR)

#######################################
# Running experiments

$(OUTDIR)/%/ready: experiments/%.sh $(GUESTS_TARS)
	bash $<
	touch $@

#######################################
# Guest Tars

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

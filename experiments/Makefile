MQNICMOD := $(abspath ../images/mqnic/mqnic.ko)

GUESTS := \
    qemu-pair-client \
    qemu-pair-server \

EXPERIMENTS := \
    qemu-corundum-bm-pair \
    qemu-corundum-verilator-pair \

BUILDDIR := build
OUTDIR := out

GUESTS_TARS := $(addprefix $(BUILDDIR)/,$(addsuffix .tar, $(GUESTS)))
EXPERIMENTS_OUTPUTS := $(addprefix $(OUTDIR)/,$(EXPERIMENTS))

all: $(GUESTS_TARS) $(EXPERIMENTS_OUTPUTS)

clean:
	rm -rf $(BUILDDIR) $(OUTDIR)

#######################################
# Running experiments

run: $(EXPERIMENTS)

$(OUTDIR)/%: experiments/%.sh $(GUESTS_TARS)
	bash $<

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

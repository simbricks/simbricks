all: $(ALL_ALL)

clean:
	rm -rf $(CLEAN_ALL)

distclean:
	rm -rf $(CLEAN_ALL) $(DISTCLEAN_ALL)


.PHONY: all clean distclean
.DEFAULT_GOAL := all

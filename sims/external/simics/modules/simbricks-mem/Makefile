# -*- Makefile ; coding: utf-8 -*-

# Simics module makefile

MODULE_CLASSES=simbricks_mem
MODULE_COMPONENTS=simbricks_mem_comp

SRC_FILES = simbricks_mem.c
PYTHON_FILES = simbricks_mem_comp.py module_load.py

# SIMBRICKS_LIB needs to be set by caller
MODULE_CFLAGS := -I"$(SIMBRICKS_LIB)"
MODULE_LDFLAGS := -L"$(SIMBRICKS_LIB)" -lsimbricks

SIMICS_API := 6
THREAD_SAFE:=yes

ifeq ($(MODULE_MAKEFILE),)
$(error Make sure you compile your module from the project directory)
else
include $(MODULE_MAKEFILE)
endif

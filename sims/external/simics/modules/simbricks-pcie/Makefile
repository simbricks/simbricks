# -*- Makefile ; coding: utf-8 -*-

# © 2010 Intel Corporation

# Simics module makefile

MODULE_CLASSES=simbricks_pcie
MODULE_COMPONENTS=simbricks_pcie_comp

SRC_FILES = simbricks_pcie.c
PYTHON_FILES = simbricks_pcie_comp.py module_load.py

# SIMBRICKS_LIB needs to be set by caller
MODULE_CFLAGS := -I"$(SIMBRICKS_LIB)" -Wno-address-of-packed-member
MODULE_LDFLAGS := -L"$(SIMBRICKS_LIB)" -lsimbricks

D:= 1

SIMICS_API := 6
THREAD_SAFE:= yes

COMPILE_PYC = 0

ifeq ($(MODULE_MAKEFILE),)
$(error Make sure you compile your module from the project directory)
else
include $(MODULE_MAKEFILE)
endif

include mk/subdir_pre.mk

lib_proto_inc := $(d)proto/

$(eval $(call subdir,netif))
$(eval $(call subdir,nicif))
$(eval $(call subdir,nicbm))

include mk/subdir_post.mk

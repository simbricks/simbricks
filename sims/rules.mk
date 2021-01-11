include mk/subdir_pre.mk

$(eval $(call subdir,external))
$(eval $(call subdir,net))
$(eval $(call subdir,nic))

include mk/subdir_post.mk

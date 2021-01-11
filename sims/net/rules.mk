include mk/subdir_pre.mk

$(eval $(call subdir,wire))
$(eval $(call subdir,tap))
$(eval $(call subdir,switch))

include mk/subdir_post.mk

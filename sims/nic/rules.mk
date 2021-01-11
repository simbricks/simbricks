include mk/subdir_pre.mk

$(eval $(call subdir,corundum))
$(eval $(call subdir,corundum_bm))
$(eval $(call subdir,i40e_bm))

include mk/subdir_post.mk

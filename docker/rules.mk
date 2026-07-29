# Copyright 2022 Max Planck Institute for Software Systems, and
# National University of Singapore
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

include mk/subdir_pre.mk

# Configuration parameters to control docker image build
DOCKER_REGISTRY ?= docker.io/simbricks/
DOCKER_REGISTRY_FROM ?= docker.io/simbricks/
DOCKER_TAG ?= :latest

CONDA_CHANNEL ?= latest

DOCKER_IMAGES := simbricks-baseenv simbricks-runner simbricks-executor

docker-images:
	docker build -t \
		$(DOCKER_REGISTRY)simbricks-baseenv$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		--build-arg="CONDA_CHANNEL=$(CONDA_CHANNEL)" \
		-f docker/Dockerfile.baseenv docker
	docker build -t \
		$(DOCKER_REGISTRY)simbricks-runner$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.runner docker
	docker build -t \
		$(DOCKER_REGISTRY)simbricks-executor$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.executor docker

docker-retag:
	for i in $(DOCKER_IMAGES) ; do \
		docker image inspect \
		  $(DOCKER_REGISTRY_FROM)$${i}$(DOCKER_TAG_FROM) >/dev/null && \
		docker tag $(DOCKER_REGISTRY_FROM)$${i}$(DOCKER_TAG_FROM) \
			$(DOCKER_REGISTRY)$${i}$(DOCKER_TAG) ; \
		done

docker-push:
	for i in $(addprefix $(DOCKER_REGISTRY), $(addsuffix $(DOCKER_TAG), \
		$(DOCKER_IMAGES))) ; do \
		docker image inspect $$i >/dev/null && docker push $$i ; \
		done

docker-pull:
	for i in $(addprefix $(DOCKER_REGISTRY), $(addsuffix $(DOCKER_TAG), \
		$(DOCKER_IMAGES))) ; do \
		docker pull $$i ; \
		done

include mk/subdir_post.mk

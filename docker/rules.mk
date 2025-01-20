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
DOCKER_REGISTRY ?= docker.io/
DOCKER_TAG ?= :latest

DOCKER_IMAGES := simbricks/simbricks-build simbricks/simbricks-base \
  simbricks/simbricks simbricks/simbricks-runenv simbricks/simbricks-min \
  simbricks/simbricks-dist-worker simbricks/simbricks-gem5opt

REQUIREMENTS_TXT := $(d)requirements.txt

$(REQUIREMENTS_TXT):
	cat requirements.txt doc/requirements.txt > $@

docker-images: $(REQUIREMENTS_TXT)
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-build$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.buildenv docker
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-base$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.base .
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile .
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-runenv$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.runenv docker
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-min$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.min docker
# The simbricks-dist-worker should be obsolete now and can be removed
#	docker build -t \
#		$(DOCKER_REGISTRY)simbricks/simbricks-dist-worker$(DOCKER_TAG) \
#		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
#		--build-arg="TAG=$(DOCKER_TAG)" \
#		-f docker/Dockerfile.dist-worker docker
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-runner$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.runner docker

docker-images-debug:
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-gem5opt$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.gem5opt docker

docker-images-tofino:
	docker build -t $(DOCKER_REGISTRY)simbricks/simbricks-tofino$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.tofino .

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

CLEAN := $(REQUIREMENTS_TXT)

include mk/subdir_post.mk

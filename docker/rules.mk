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

DOCKER_IMAGES_SIMS := simbricks/simbricks-build simbricks/simbricks-runenv \
  simbricks/simbricks-sims simbricks/simbricks-fullsims

DOCKER_IMAGES_SYMPHONY := simbricks/simbricks-local simbricks/simbricks-runner \
  simbricks/simbricks-executor

REQUIREMENTS_TXT := $(d)requirements.txt

$(REQUIREMENTS_TXT):
	cat requirements.txt doc/requirements.txt > $@

docker-images-sims: $(REQUIREMENTS_TXT)
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-build$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.buildenv docker
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-runenv$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.runenv docker
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-sims$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.sims .
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-fullsims$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.full .

docker-images-symphony: $(REQUIREMENTS_TXT)
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-local$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.local .
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-runner$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.runner .
	docker build -t \
		$(DOCKER_REGISTRY)simbricks/simbricks-executor$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.executor .

docker-images: docker-images-sims docker-images-symphony

docker-images-tofino:
	docker build -t $(DOCKER_REGISTRY)simbricks/simbricks-tofino$(DOCKER_TAG) \
		--build-arg="REGISTRY=$(DOCKER_REGISTRY)" \
		--build-arg="TAG=$(DOCKER_TAG)" \
		-f docker/Dockerfile.tofino .


docker-retag-sims:
	for i in $(DOCKER_IMAGES_SIMS) ; do \
		docker image inspect \
		  $(DOCKER_REGISTRY_FROM)$${i}$(DOCKER_TAG_FROM) >/dev/null && \
		docker tag $(DOCKER_REGISTRY_FROM)$${i}$(DOCKER_TAG_FROM) \
			$(DOCKER_REGISTRY)$${i}$(DOCKER_TAG) ; \
		done

docker-retag-symphony:
	for i in $(DOCKER_IMAGES_SYMPHONY) ; do \
		docker image inspect \
		  $(DOCKER_REGISTRY_FROM)$${i}$(DOCKER_TAG_FROM) >/dev/null && \
		docker tag $(DOCKER_REGISTRY_FROM)$${i}$(DOCKER_TAG_FROM) \
			$(DOCKER_REGISTRY)$${i}$(DOCKER_TAG) ; \
		done


docker-push-sims:
	for i in $(addprefix $(DOCKER_REGISTRY), $(addsuffix $(DOCKER_TAG), \
		$(DOCKER_IMAGES_SIMS))) ; do \
		docker image inspect $$i >/dev/null && docker push $$i ; \
		done

docker-push-symphony:
	for i in $(addprefix $(DOCKER_REGISTRY), $(addsuffix $(DOCKER_TAG), \
		$(DOCKER_IMAGES_SYMPHONY))) ; do \
		docker image inspect $$i >/dev/null && docker push $$i ; \
		done

docker-pull-sims:
	for i in $(addprefix $(DOCKER_REGISTRY), $(addsuffix $(DOCKER_TAG), \
		$(DOCKER_IMAGES_SIMS))) ; do \
		docker pull $$i ; \
		done

CLEAN := $(REQUIREMENTS_TXT)

include mk/subdir_post.mk

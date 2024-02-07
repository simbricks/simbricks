ARG REGISTRY=
ARG TAG=:latest
FROM ${REGISTRY}simbricks/simbricks-base${TAG}
RUN make -j `nproc` build-images-min COMPRESSED_IMAGES=true \
 && bash docker/cleanup_images.sh

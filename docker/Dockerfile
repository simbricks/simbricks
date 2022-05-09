FROM simbricks/simbricks-build:latest
COPY . /simbricks
WORKDIR /simbricks
RUN make -j `nproc` ENABLE_VERILATOR=y
RUN git submodule update --init sims/external/qemu \
 && make -j `nproc` sims/external/qemu/ready \
 && bash docker/cleanup_external.sh
RUN make -j `nproc` build-images-min COMPRESSED_IMAGES=true \
 && bash docker/cleanup_images.sh

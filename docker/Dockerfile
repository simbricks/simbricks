FROM simbricks/simbricks-build:latest
COPY . /simbricks
WORKDIR /simbricks
RUN make -j `nproc` ENABLE_VERILATOR=y
RUN git submodule update --init sims/external/qemu \
 && make -j `nproc` sims/external/qemu/ready \
 && bash docker/cleanup_external.sh
RUN git submodule update --init sims/external/gem5 \
 && make -j `nproc` sims/external/gem5/ready \
 && bash docker/cleanup_gem5.sh
RUN git submodule update --init sims/external/femu \
 && make -j `nproc` sims/external/femu/ready
RUN make -j `nproc` build-images-min COMPRESSED_IMAGES=true \
 && bash docker/cleanup_images.sh

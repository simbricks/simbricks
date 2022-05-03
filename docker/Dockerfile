FROM simbricks-build AS simbricks-obj
COPY . /simbricks
WORKDIR /simbricks
RUN make -j `nproc` ENABLE_VERILATOR=y
RUN make -j `nproc` sims/external/qemu/ready
RUN make -j `nproc` build-images-min COMPRESSED_IMAGES=true \
	&& rm -f images/output-*/*.raw


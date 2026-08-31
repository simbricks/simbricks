..
  Copyright 2026 Max Planck Institute for Software Systems,
  National University of Singapore, and SimBricks UG (haftungsbeschraenkt)
..
  Permission is hereby granted, free of charge, to any person obtaining
  a copy of this software and associated documentation files (the
  "Software"), to deal in the Software without restriction, including
  without limitation the rights to use, copy, modify, merge, publish,
  distribute, sublicense, and/or sell copies of the Software, and to
  permit persons to whom the Software is furnished to do so, subject to
  the following conditions:
..
  The above copyright notice and this permission notice shall be
  included in all copies or substantial portions of the Software.
..
  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
  EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
  MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
  IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
  CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
  TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
  SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

.. _sec-disk-images:

Disk Images and Data Flow
**********************************************

Full-system host simulators such as QEMU and gem5 boot a complete Linux system. For this they need
a disk image containing the operating system, drivers, and benchmark applications, plus the boot
artifacts (kernel, initrd). This chapter explains how disk images are referenced in virtual
prototype scripts, how SimBricks can build them for you, where the files come from, and how
per-run inputs and outputs flow through a simulation.

There are two ways to get an image, and they mix freely:

- **Bring one you built.** Any tooling that produces a qcow2 or raw image works — packer, a
  distribution's cloud image, ``virt-install``, your own scripts, whatever your group already
  uses. SimBricks never needs to know how it was made.
- **Describe it in the virtual prototype script.** Start from an image of the first kind and list
  the changes you want on top of it. SimBricks builds the result on the Runner when the run is
  prepared, and reuses it for later runs.

The second is not a replacement for the first: it exists because the common case — an existing
base image plus a package to install and a few files to copy in — should not require a separate
build pipeline, a second repository, or a manual copy step onto a shared Runner.

Referencing an image you already have
=====================================

Disk images are part of the System Configuration. ``simbricks.orchestration.system`` provides a
small hierarchy of disk image classes (see :ref:`sec-orchestration-framework-ref` for the API
reference). A disk image is created once on the ``System`` and can then be attached to one or more
hosts with ``host.add_disk()``:

.. code-block:: python

  from simbricks.orchestration import system

  syst = system.System()
  disk = system.DistroDiskImage(syst, "base")

  host0 = ...
  host0.add_disk(disk)
  host0.add_disk(system.LinuxConfigDiskImage(syst, host0))

The image types that reference an existing image are:

- ``DistroDiskImage(system, name)``: an image distributed alongside SimBricks, **by name**. It is
  looked up in the *global input directory* of the execution environment under
  ``images/<name>/<name>`` (qcow2) or ``images/<name>/<name>.raw`` (raw) — see
  :ref:`sec-disk-images-global-input`. The ``base`` image is pre-installed in the SimBricks
  executor environments.
- ``ExternalDiskImage(system, path, boot_dir=None)``: an image at an explicit path **on the
  machine that executes the run**.
- ``ExternalDiskImageArtifact(system, path, boot_dir=None)``: an image on the machine you *submit*
  from, shipped to the Runner with the run. Input artifacts travel inside the run event, so this
  suits a small image; anything sizeable belongs in an ``HttpDiskImage`` or the global input
  directory.
- ``HttpDiskImage(system, url, checksum=None, format="qcow2", boot_dir=None)``: an image the
  Runner downloads. ``format`` says what the URL serves, and the checksum is verified against
  those bytes before anything else touches them (``"sha256:..."``, or any algorithm ``hashlib``
  knows). The download is cached, so a URL is fetched once however many runs use it, and it is
  put through ``qemu-img`` on the way in: what is kept is qcow2, compressed as the cache asks
  (see :ref:`sec-disk-images-caching`), so a raw or vmdk URL backs a layered build just as well
  as a qcow2 one. That conversion is the one thing outside a builder package that needs
  ``qemu-img`` on the Runner; with a qcow2 URL and ``--image-cache-compression none`` there is
  nothing to convert and it is never called.
- ``LinuxConfigDiskImage(system, host)``: a small, dynamically generated image holding the
  commands to run on the host during simulation. This is how your workload gets into the guest —
  see :ref:`sec-disk-images-guest-payload`.
- ``DummyDiskImage``: not something you instantiate. A Runner that cannot import the class an
  image asks for keeps it as one of these, and says which type and module were missing when a
  simulator needs the image.

Different host simulators support different image formats: QEMU works with qcow2 (using a
copy-on-write overlay per host, so hosts can share one backing image) and raw, while gem5 requires
raw images. The orchestration framework automatically selects a format both the image and the
simulator support, and copies the image per host where necessary.

.. _sec-disk-images-building:

Building an image from the script
=================================

A **layered image** is a base image plus an ordered list of changes. Both are declared in the same
script that defines the virtual prototype, and the image is built on the Runner while the run is
prepared:

.. code-block:: python

  from simbricks.imagebuild.guestfs import GuestfsImage
  from simbricks.orchestration import system

  syst = system.System()
  base = system.DistroDiskImage(syst, "base")

  image = GuestfsImage(syst, base)
  image.run("apt-get update && apt-get install -y --no-install-recommends iperf3")
  image.add_file("/etc/simbricks-bench.conf", "duration=10\n")
  image.copy_in("./mybench", "/usr/local/bin/mybench", mode=0o755)
  image.run_script("./setup-my-software.sh")

  host = system.FullSystemHost(syst)
  host.add_disk(image)

Any of the image types above can be the base, including another layered image. The layer
operations are:

- ``run(cmd)``: run a shell command in the image.
- ``run_script(path)`` / ``run_script_str(name, script)``: run a script, taken from the submitting
  machine or given inline.
- ``add_file(dest, content, mode=None)``: write a file into the image.
- ``copy_in(src, dest, mode=None)``: copy a file from the submitting machine into the image.

Files named by ``copy_in`` and ``run_script`` are collected as input artifacts automatically, so
the same script works unchanged locally and when submitted to a remote Runner.

``image.disk_size = "32G"`` grows the image before the layers run — the disk, its largest
partition, and the ext, xfs or btrfs filesystem on it. Leave it unset to keep the base image's
size. It is a property rather than a layer because the build materializes a single image: the
growth can only happen as that image is created. For a filesystem the guestfs builder cannot
grow, set ``grow_filesystem = False`` on it: the disk and the partition still grow, and the
filesystem is left to a layer, where the guest's own tools are available.

Choosing a builder
------------------

The builder is the class you instantiate, and each lives in its own package so a Runner only
installs the tooling for the ways it actually builds images:

.. list-table::
  :header-rows: 1
  :widths: 25 35 40

  * - Class
    - Package
    - Use it when
  * - ``GuestfsImage``
    - ``simbricks-imagebuild-guestfs``
    - The default. Applies the whole layer list offline with ``virt-customize``, without booting
      a VM, so an ordinary change costs seconds.
  * - ``PackerImage``
    - ``simbricks-imagebuild-packer``
    - The build needs a running system: services started, a kernel of its own, anything that only
      works in a booted guest. Costs a full boot per build.

Both need tooling on the Runner that is not a conda dependency: ``qemu-utils`` either way, since
the image itself is written and converted with ``qemu-img``, plus ``libguestfs-tools`` for the
guestfs builder and ``packer`` and ``xorriso`` for the packer builder. The
``simbricks/simbricks-executor`` image has all of it. A missing tool is reported by name before
anything else runs.

A Runner without the package a script asks for cannot deserialize that image, and says which
class and module it could not import — that is the intended way to find out that a Runner is not
set up for the build your script wants.

Both take the resources the build itself gets, as ``cpus`` and ``mem_size`` (e.g. ``"4G"``). This
is worth setting for a layer that compiles something: libguestfs gives its appliance a single
vCPU and little memory, and the machine packer boots defaults to 2 vCPUs and 2G. The packer
builder additionally takes ``accelerator`` (``kvm`` where the Runner has ``/dev/kvm``, else
``tcg``), the guest credentials it logs in with, ``ssh_timeout``, and ``cleanup``, which trims
package caches and logs after the layers.

``PackerDiskImage(system, packer_config_path)`` predates all of this and is still there: it runs
a Packer configuration of your own during preparation. It has no layers and no content hash, so
nothing about it is cached, and ``PackerImage`` is what you want for new scripts.

.. _sec-disk-images-caching:

Reusing builds across runs
==========================

Every image has a **content hash**: what the built image would contain, decided without building
it — the base's identity, the builder class, the disk size, and what each layer does, including
the contents of the files it copies in. Give a Runner a cache directory and builds are stored
under that hash and reused:

.. code-block:: shell

  simbricks-run --image-cache-dir /var/cache/simbricks-images \
                --image-cache-size 200G ...

On a Runner, the same is configured with ``image_cache_dir`` and ``image_cache_size`` in the
fragment executor settings. With no cache directory, every run builds its images from scratch, as
before.

What the cache gives you:

- **Later runs skip the build entirely**, including the boot artifacts extracted from the image.
- **Appending a layer only runs the new layer.** The hash is rolling, so every prefix of the layer
  list has its own hash, and a build starts from the longest prefix already in the cache. Editing
  or inserting a layer invalidates only that layer onwards.
- **Concurrent runs cooperate.** An entry is locked while it is built, so a second run wanting the
  same image waits for the first rather than building it again. Without a cache directory there is
  nothing to coordinate through and both runs build.
- **An entry is a delta on the entry it was built from.** Appending a layer to a cached image
  costs an entry the size of what that layer wrote, not the size of a whole image. A simulator
  that reads qcow2 gets the chain hard linked into the run with a fresh overlay on top, so a hit
  copies nothing; one that needs a single flat image — gem5, and raw generally — gets it
  flattened once, kept beside the chain for later runs to reuse.
- **Bounded growth.** With ``--image-cache-size``, least recently used entries are dropped once
  the cache exceeds it. A run that has already taken an image out is unaffected by that image
  being evicted.
- **Entries are compressed**, with zstd, which typically cuts an entry to a third of its size for
  a read cost in the low percent — so a cache of a given size holds more images and evicts less
  often. It is paid once, when the entry is written. ``--image-cache-compression`` (or
  ``image_cache_compression`` on a Runner) takes ``none`` to turn it off, or ``zlib`` for a QEMU
  too old to read zstd.

Anything that is per-run — ``LinuxConfigDiskImage``, above all — is never cached and says so if
asked for a hash.

Boot artifacts
==============

Simulators that boot a kernel directly cannot read it out of the image, so they need the kernel,
initrd, or uncompressed ``vmlinux`` handed to them separately. They ask the image for what they
need, and where those files come from depends on the image type:

- ``DistroDiskImage``: alongside the image in the global input directory, under ``boot/``.
- ``ExternalDiskImage``, ``ExternalDiskImageArtifact``, ``HttpDiskImage``: from the directory
  given as ``boot_dir=``, if you have prebuilt ones.
- Layered images: extracted from the image that was just built — offline with libguestfs, or
  downloaded from the guest over SSH by the packer builder while the machine is still up. They are
  cached with the image, so a cache hit does not have to boot anything.

Setting a simulator's kernel path explicitly (e.g. ``QemuSim.kernel_path``) overrides all of this
and skips the lookup.

Building images outside SimBricks
=================================

Images built elsewhere are first-class, and one is always involved: every layered image starts
from a base that something else produced. Use whatever fits — a distribution cloud image via
``HttpDiskImage`` is often enough to start from.

The ``base`` image shipped with SimBricks is built by :image-builder:`\ `, a small,
simulator-independent packer harness that turns a stock cloud image into an image plus its boot
artifacts. It is the right tool when you are producing a *base* image for others to build on: a
custom kernel, a driver stack, anything large enough that you want it built once and distributed
rather than rebuilt per experiment. Its output directory maps 1:1 onto the global input layout
below.

.. _sec-disk-images-global-input:

The global input directory
==========================

Executions resolve ``DistroDiskImage`` references inside a **global input directory**: a directory
of (typically large, reusable) input files that exists once per execution environment rather than
per run. The expected layout for disk images is:

.. code-block:: text

  <global_input>/images/<name>/<name>        # the image, qcow2
  <global_input>/images/<name>/<name>.raw    # the image, raw (needed by gem5)
  <global_input>/images/<name>/boot/vmlinuz  # kernel (bzImage), used by QEMU
  <global_input>/images/<name>/boot/initrd   # initramfs, used by QEMU
  <global_input>/images/<name>/boot/vmlinux  # kernel (ELF), used by gem5

How the global input directory is located depends on how you execute:

- **SimBricks Cloud / executor image:** the ``simbricks/simbricks-executor`` Docker image ships
  with a pre-built ``base`` image at ``/global_input/images/base/`` and sets the
  ``GLOBAL_INPUT_DIR=/global_input`` environment variable.
- **Local execution with** ``simbricks-run``: pass ``--global-input-dir <DIR>`` on the command
  line (see :ref:`sec-execution`).

At preparation time, the global input directory is symlinked into the run's working directory as
``global_input``, and simulators resolve boot artifacts through that link (e.g. QEMU passes
``global_input/images/base/boot/vmlinuz`` as its kernel).

.. _sec-disk-images-guest-payload:

Getting your workload into the guest
====================================

The commands that a host executes during simulation are configured through its applications
(``host.add_app(...)``). Under the hood, ``LinuxConfigDiskImage`` packs the generated commands
(``guest/run.sh``, plus any additional config files you attach to the host) into a tar archive that
is attached to the simulated host as a second disk. The base disk images install a small init
script (``guestinit.sh``) in the guest that unpacks this archive from ``/dev/sdb`` and executes
``guest/run.sh``. The host simulator's kernel command line is set up to run this init script
instead of a regular init system, and all output is delivered over the serial console ``ttyS0``,
which is how the application output ends up in your simulation logs.

So there are three places your software can come from, in increasing order of how much they cost
to change:

- **The applications on the host** — anything that can simply be executed at run time.
- **Layers on the image** (:ref:`sec-disk-images-building`) — packages to install, files to bake
  in, software to compile once and reuse across runs.
- **A base image built elsewhere** — kernels, driver stacks, and anything large enough to be worth
  building once and distributing.

Run working directory and outputs
=================================

Each run executes in its own working directory with a fixed layout, managed by the orchestration
framework's ``InstantiationEnvironment``:

.. code-block:: text

  <workdir>/
    global_input -> <global input directory>   # symlink, if configured
    input_artifacts/                           # unpacked input artifacts
    tmp/
      imgs/                # per-host image copies/overlays, built and generated images
      checkpoints/         # simulator checkpoints (if enabled)
      shm/                 # shared-memory queues connecting the simulators
      proxies/             # proxy state for distributed runs
    output/
      output.<simulator>-<id>/   # per-simulator output directories
      out.json                   # collected output of the whole simulation

The image cache, when configured, deliberately lives **outside** the working directory: what it
holds outlives the run.

After a run completes, the collected simulator output is available as JSON (``output/out.json``).
When running through the SimBricks Cloud, this output is what the Backend stores and what the CLI
and client library retrieve; additionally, Fragments can declare *output artifacts* (files to
collect after execution) and *input artifacts* (files to ship to the Runner before execution).

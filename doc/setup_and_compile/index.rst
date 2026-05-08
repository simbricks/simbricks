..
  Copyright 2021 Max Planck Institute for Software Systems, and
  National University of Singapore
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

.. _sec-setup-compile:

===================================
Advanced Setup & Building
===================================

While the SimBricks Cloud offering provides the fastest, zero-friction path to
running virtual prototypes, advanced workflows may require you to compile custom
simulators, build modified disk images, or prepare environments for self-hosted
cloud runners. 

Depending on your goals—whether developing a new integration or provisioning a
self-hosted execution node for your paid plan—there are several ways to set up
an environment to build and manage these SimBricks artifacts.

.. toctree::
   :maxdepth: 2

   pre-built-docker
   build-docker
   build-dev-container
   deb-package
   bare-metal


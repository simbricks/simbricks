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

API
###################################

The full API documentation extracted by doxygen can be found
`here <https://tas.readthedocs.io/en/latest/_static/doxygen/>`_.


TAS Low-Level Application API
******************************

.. doxygenfunction:: flextcp_init

Contexts
=========================

.. doxygenstruct:: flextcp_context
.. doxygenfunction:: flextcp_context_create
.. doxygenfunction:: flextcp_context_poll
.. doxygenfunction:: flextcp_block


Connections
=========================

.. doxygenstruct:: flextcp_connection
.. doxygenfunction:: flextcp_connection_open
.. doxygenfunction:: flextcp_connection_close
.. doxygenfunction:: flextcp_connection_rx_done
.. doxygenfunction:: flextcp_connection_tx_alloc
.. doxygenfunction:: flextcp_connection_tx_alloc2
.. doxygenfunction:: flextcp_connection_tx_send
.. doxygenfunction:: flextcp_connection_tx_close
.. doxygenfunction:: flextcp_connection_tx_possible
.. doxygenfunction:: flextcp_connection_move

Listeners
=========================

.. doxygenstruct:: flextcp_listener
.. doxygendefine:: FLEXTCP_LISTEN_REUSEPORT
.. doxygenfunction:: flextcp_listen_open
.. doxygenfunction:: flextcp_listen_accept

Events
=========================

.. doxygenenum:: flextcp_event_type

.. doxygenstruct:: flextcp_event
  :members:

TAS Sockets API
******************************


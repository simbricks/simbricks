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


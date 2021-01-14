###################################
Developer Guide
###################################


******************************
Code Structure
******************************

  * ``tas/``: service implementation

    + ``tas/fast``: TAS fast path

    + ``tas/slow``: TAS slow path

  * ``lib/``: client libraries

    + ``lib/tas``: lowlevel TAS client library (interface:
      ``lib/tas/include/tas_ll.h``)

    + ``lib/sockets``: socket emulation layer

  * ``tools/``: debugging tools

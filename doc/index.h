/**
 * @mainpage SimBricks Overview
 *
 * SimBricks is a modular full-system simulation framework that connects
 * battle-tested component simulators (hosts, NICs, other devices, memory, and
 * networks) into complete virtual prototypes.
 *
 * This Doxygen documentation covers the SimBricks core C/C++ libraries found
 * in `lib/simbricks/` of the main repository (distributed as the
 * `simbricks-lib` conda package):
 *
 *    - Base protocol: connection setup, message transfer, and time
 *      synchronization (`lib/simbricks/base`).
 *    - Network protocol: Ethernet packet exchange layered on the base
 *      protocol (`lib/simbricks/network`).
 *    - PCIe protocol: transaction-level PCIe communication between hosts and
 *      devices (`lib/simbricks/pcie`).
 *    - Memory protocol: simplified memory read/write interface
 *      (`lib/simbricks/mem`).
 *    - NIC helpers: `lib/simbricks/nicif` (thin C helper for NIC simulators,
 *      deprecated) and `lib/simbricks/nicbm` (C++ helper library for
 *      behavioral NIC models).
 *    - Parameter parsing and interface establishment helpers
 *      (`lib/simbricks/parser`).
 *    - AXI helpers for connecting RTL device simulations
 *      (`lib/simbricks/axi`).
 *
 * For the user-facing documentation, including the Python orchestration
 * framework, see https://simbricks.readthedocs.io/ .
 */

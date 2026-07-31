Currently, SimBricks includes the following simulators:
***********************************************************

Each simulator integration lives in its own *component repository* and is distributed as a set of
installable packages (see :ref:`sec-conda-packages` for details on the packages and the
``sys-py`` / ``sim-py`` / ``sim-bin`` naming scheme).

.. list-table::
   :header-rows: 1
   :widths: 20 25 25 30

   * - Simulator
     - Simulates
     - Component Repository
     - Main Packages
   * - :qemu:`\ `
     - Fast host simulator
     - :component-qemu:`\ `
     - ``simbricks-qemu-sim-bin``, ``simbricks-qemu-sim-py``
   * - :gem5:`\ `
     - Flexible and detailed host simulator
     - :component-gem5:`\ `
     - ``simbricks-gem5-sim-bin``, ``simbricks-gem5-sim-py``
   * - :ns3:`\ `
     - Flexible simulator for networks
     - :component-ns3:`\ `
     - ``simbricks-ns3-sim-bin``, ``simbricks-ns3-sim-py``
   * - Basic network simulators (switch, wire, tap, packet generator)
     - Simple Ethernet networks
     - :component-net-base:`\ `
     - ``simbricks-net-base-sim-bin``, ``simbricks-net-base-sim-py``
   * - Basic memory simulators (memory, interconnect, terminal)
     - Simple (disaggregated) memory
     - :component-mem-base:`\ `
     - ``simbricks-mem-base-sim-bin``, ``simbricks-mem-base-sim-py``
   * - Intel i40e behavioral model
     - Intel X710 40G NIC
     - :component-i40e:`\ `
     - ``simbricks-i40e-sim-bm-bin``, ``simbricks-i40e-sim-bm-py``, ``simbricks-i40e-sys-py``
   * - Intel e1000 behavioral model
     - Intel e1000 1G NIC
     - :component-e1000:`\ `
     - ``simbricks-e1000-sim-bm-bin``, ``simbricks-e1000-sim-bm-py``, ``simbricks-e1000-sys-py``
   * - :corundum:`\ ` (via :verilator:`\ `)
     - Open-source FPGA-based NIC, simulated from its Verilog RTL
     - :component-corundum:`\ `
     - ``simbricks-corundum-sim-rtl-bin``, ``simbricks-corundum-sim-rtl-py``, ``simbricks-corundum-sys-py``
   * - :femu:`\ `
     - NVMe SSD simulator
     - :component-femu:`\ `
     - ``simbricks-femu-sim-bin``, ``simbricks-femu-sim-py``

Further simulators have been integrated with SimBricks in the past and can be integrated again with
moderate effort, among them :simics:`\ ` (fast, closed-source host simulator supporting modern x86
ISA extensions like AVX), :omnet:`\ ` (flexible network simulator), and the :tofino:`\ ` for Tofino
P4 switches. If you are interested in one of these, or want to integrate your own simulator, check
out :ref:`sec-simulator-integration` or reach out on :slack:`Slack`.

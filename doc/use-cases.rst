
Concrete use-cases for SimBricks:
**************************************

Modern hardware design increasingly relies on specialized accelerators and 
heterogeneous architectures. However, simulating these components in isolation 
often masks critical system-level bottlenecks, such as PCIe interconnect
limitations, memory controller inefficiencies, or network latency. SimBricks
addresses this visibility gap by providing a framework for comprehensive
full-system virtual prototyping, allowing engineers to validate custom hardware
behavior within a complete system context prior to physical tape-out.

The SimBricks architecture provides a modular simulation infrastructure that
connects custom hardware models with virtualized off-the-shelf components,
including standard CPUs, NICs, and network switches. By synchronizing these
discrete simulators into a unified, deterministic environment, SimBricks enables
developers to boot real operating systems, execute unmodified software stacks,
and analyze end-to-end data flow across hardware-software boundaries. This
hardware-software co-design approach supports a wide range of use cases:

- Evaluating HW accelerators, from early design with simple behavioral models,
  to simulating complete Verilog implementations, both as part of complete
  systems with many instances of the accelerator and machines running full-blown
  operating systems and real applications
- Testing network protocols, topologies, and communication stacks for real
  workloads in a potentially large system (we ran up to 1000 hosts so far)
- Rapid RTL prototyping for FPGAs, no waiting for synthesis or fiddling with
  timing initially
- Our paper :simbricks-paper:`\ ` provides a more detailed discussion of technical details and use-cases
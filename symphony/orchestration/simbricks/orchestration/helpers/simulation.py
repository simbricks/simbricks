# Copyright 2024 Max Planck Institute for Software Systems, and
# National University of Singapore
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from simbricks.orchestration import system
from simbricks.orchestration.simulation import base as sim_base
from simbricks.utils import base as utils_base


def add_specs(simulator: sim_base.Simulator, *specifications) -> None:
    utils_base.has_expected_type(obj=simulator, expected_type=sim_base.Simulator)
    for spec in specifications:
        utils_base.has_expected_type(obj=spec, expected_type=system.Component)
        simulator.add(comp=spec)


def enable_sync_simulation(
    simulation: sim_base.Simulation, amount: int | None = None, ratio: utils_base.Time = None
) -> None:
    utils_base.has_expected_type(obj=simulation, expected_type=sim_base.Simulation)
    set_period: bool = amount is not None and ratio is not None
    if set_period:
        utils_base.has_expected_type(obj=amount, expected_type=int)
        utils_base.has_expected_type(obj=ratio, expected_type=utils_base.Time)

    for chan in simulation.get_all_channels():
        chan._synchronized = True
        if set_period:
            chan.set_sync_period(amount=amount, ratio=ratio)


def disalbe_sync_simulation(simulation: sim_base.Simulation) -> None:
    utils_base.has_expected_type(obj=simulation, expected_type=sim_base.Simulation)

    for chan in simulation.get_all_channels(lazy=False):
        chan._synchronized = False


def simple_simulation(
    system: system.System,
    sync=False,
    compmap=dict[type[system.Component], type[sim_base.Simulator]]
):
  """Create simple simulation from system. Uses a map from component type to
  simulator type and then creates one simulator per component."""
  # FIXME: name from system, but system has no name
  simulation = sim_base.Simulation(
      name="netperf_sysconf", system=system
  )

  for comp in system._all_components.values():
    if comp in simulation._sys_sim_map:
      continue

    for (ct,st) in compmap.items():
      if isinstance(comp, ct):
        simulator = st(simulation)
        simulator.add(comp)
        if comp.name:
          simulator.name = comp.name

    if not sync:
      disalbe_sync_simulation(simulation=simulation)

  return simulation
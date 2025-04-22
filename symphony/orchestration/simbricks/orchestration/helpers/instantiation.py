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

from simbricks.utils import base as utils_base
from simbricks.orchestration.simulation import base as sim_base
from simbricks.orchestration.instantiation import base as inst
from simbricks.orchestration.instantiation import fragment as frag


def simple_instantiation(
    simulation: sim_base.Simulation,
) -> inst.Instantiation:
    """Create simple instantiation from a simulation.
    By default, a single Fragment is created as part of which all Simulators are executed"""

    utils_base.has_expected_type(simulation, sim_base.Simulation)
    instance = inst.Instantiation(simulation)
    fragment = frag.Fragment()
    fragment.add_simulators(*simulation.all_simulators())
    instance.fragments = [fragment]
    return instance

import simbricks.splitsim.specification as spec
import simbricks.splitsim.impl as impl
import typing as tp

"""
RunObj class stores a mapping between a specification instance and the simulator instance

"""

class RunObj(object):
    def __init__(self) -> None:
        self.sim_inst: impl.Simulator = None
        self.spec_inst: spec.SimObject = None

"""
Allobj class stores all the mappings for an experiment
"""
class AllObj(object):
    def __init__(self) -> None:
        self.all_obj: tp.List[RunObj] = []




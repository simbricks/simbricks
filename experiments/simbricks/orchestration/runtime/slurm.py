# Copyright 2021 Max Planck Institute for Software Systems, and
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

import os
import pickle
import shutil
import string
import typing as tp

import simbricks.orchestration.experiments as exps


def create_batch_script(
    exp: exps.Experiment,
    container: str,
    slurmdir: str,
    repodir: str,
    runtime: str,
    num_nodes: int,
    auto_dist: bool
) -> None:
    """Create a batch script in `slurmdir` suitable for submission via Slurm's
    sbatch and that will run the provided `experiment`"""
    # pickle experiment
    os.makedirs(slurmdir, exist_ok=True)
    with open(os.path.join(slurmdir, f'{exp.name}.exp'), 'wb') as f:
        pickle.dump(exp, f)

    # write out slurm batch script
    templatedir = os.path.join(repodir, 'experiments/simbricks/utils/slurm/')
    with open(
        os.path.join(templatedir, 'grid_submit.sh.template'),
        'r',
        encoding='utf-8'
    ) as f:
        batch_script_template = string.Template(f.read())

    runtime = '' if runtime == 'sequential' else f'--{runtime}'
    auto_dist = '--auto_dist' if auto_dist else ''

    batch_script = batch_script_template.substitute(
        NUMNODES=(
            tp.cast(exps.DistributedExperiment, exp).num_hosts
            if isinstance(exp, exps.DistributedExperiment) else num_nodes
        ),
        MEM_PER_NODE=exp.resreq_mem(),
        CORES_PER_TASK=exp.resreq_cores(),
        JOBNAME=exp.name,
        CONTAINER=container,
        SIMBRICKS_RUN_ARGS=f'{runtime} {auto_dist} --pickled',
        EXPERIMENT=f'{exp.name}.exp'
    )

    with open(
        os.path.join(slurmdir, f'{exp.name}-grid_submit.sh'),
        'w',
        encoding='utf-8'
    ) as f:
        f.write(batch_script)

    # copy further required files to slurmdir
    shutil.copy(os.path.join(templatedir, 'make_hosts.sh'), slurmdir)
    shutil.copy(os.path.join(templatedir, 'prepcontainer.sh'), slurmdir)
    shutil.copy(os.path.join(templatedir, 'runmain.sh'), slurmdir)
    shutil.copy(os.path.join(templatedir, 'runworker.sh'), slurmdir)
    shutil.copy(os.path.join(templatedir, 'modify_oci.py'), slurmdir)
    shutil.copy(os.path.join(templatedir, 'kvm-group.patch'), slurmdir)

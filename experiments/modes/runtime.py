import modes.experiments as exp

class Run(object):
    def __init__(self, experiment, env, outpath):
        self.experiment = experiment
        self.env = env
        self.outpath = outpath
        self.output = None

class Runtime(object):
    def add_run(self, run):
        pass

    def start(self):
        pass

class LocalSimpleRuntime(Runtime):
    def __init__(self):
        self.runnable = []
        self.complete = []

    def add_run(self, run):
        self.runnable.append(run)

    def start(self):
        for run in self.runnable:
            run.output = exp.run_exp_local(run.experiment, run.env)
            self.complete.append(run)

            with open(run.outpath, 'w') as f:
                f.write(run.output.dumps())

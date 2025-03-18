from simbricks.runner.main_runner.plugins import plugin
from simbricks.utils import load_mod

class RunnerPluginLoadError(Exception):
    pass

def load_plugin(path: str) -> plugin.FragmentRunnerPlugin:
    module = load_mod.load_module(path)
    if "runner_plugin" not in module.__dict__:
        raise RunnerPluginLoadError(f"Plugin {path} does not provide global variable runner_plugin")
    if not issubclass(module.runner_plugin, plugin.FragmentRunnerPlugin):
        raise RunnerPluginLoadError(f"Plugin {path} does not have the correct type")
    return module.runner_plugin

def load_plugins(paths: list[str]) -> dict[str, plugin.FragmentRunnerPlugin]:
    plugins = {}
    for path in paths:
        plugin = load_plugin(path)
        name = plugin.name()
        if name in plugins:
            raise KeyError(f"Plugin {name} already exists")
        plugins[name] = plugin
    
    return plugins
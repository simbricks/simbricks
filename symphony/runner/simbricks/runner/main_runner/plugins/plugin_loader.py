import importlib

from simbricks.runner.main_runner.plugins import plugin
from simbricks.utils import load_mod

class RunnerPluginLoadError(Exception):
    pass

def load_plugin(path: str) -> type[plugin.FragmentRunnerPlugin]:
    module = None

    # try to import module
    try:
        module = importlib.import_module(path)
    except Exception:
        pass

    # try to load from file if importing failed
    if module is None:
        module = load_mod.load_module(path)

    assert module is not None

    if "runner_plugin" not in module.__dict__:
        raise RunnerPluginLoadError(f"Plugin {path} does not provide global variable runner_plugin")
    if not issubclass(module.runner_plugin, plugin.FragmentRunnerPlugin):
        raise RunnerPluginLoadError(f"Plugin {path} does not have the correct type")
    return module.runner_plugin

def load_plugin_from_file(path: str) -> type[plugin.FragmentRunnerPlugin]:
    module = load_mod.load_module(path)
    if "runner_plugin" not in module.__dict__:
        raise RunnerPluginLoadError(f"Plugin {path} does not provide global variable runner_plugin")
    if not issubclass(module.runner_plugin, plugin.FragmentRunnerPlugin):
        raise RunnerPluginLoadError(f"Plugin {path} does not have the correct type")
    return module.runner_plugin

def load_plugins_from_files(paths: list[str]) -> dict[str, type[plugin.FragmentRunnerPlugin]]:
    plugins = {}
    for path in paths:
        plugin = load_plugin_from_file(path)
        name = plugin.name()
        if name in plugins:
            raise KeyError(f"Plugin {name} already exists")
        plugins[name] = plugin
    
    return plugins
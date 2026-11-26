"""Load pure integration modules without executing the HA entry point."""
import importlib.util
from pathlib import Path
import sys
import types
ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "bkw_test_package"
module = types.ModuleType(PACKAGE)
module.__path__ = [str(ROOT / "custom_components/bkw_dynamic_tariffs")]
sys.modules[PACKAGE] = module

def load(name):
    fullname = PACKAGE + "." + name
    if fullname in sys.modules:
        return sys.modules[fullname]
    spec = importlib.util.spec_from_file_location(fullname,Path(module.__path__[0]) / (name+".py"))
    imported = importlib.util.module_from_spec(spec)
    sys.modules[fullname] = imported
    spec.loader.exec_module(imported)
    return imported

"""Import the Home Assistant free modules without running the package __init__.

The integration's __init__.py imports Home Assistant, which is not installed
in a plain checkout. const / history / panel_data deliberately have no such
imports, so they are loaded here under a synthetic package name.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

PACKAGE = "transip_dns_pure"
ROOT = Path(__file__).resolve().parent.parent


def load() -> types.ModuleType:
    if PACKAGE in sys.modules:
        return sys.modules[PACKAGE]

    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT)]
    sys.modules[PACKAGE] = package

    for name in ("const", "history", "panel_data"):
        spec = importlib.util.spec_from_file_location(
            f"{PACKAGE}.{name}", ROOT / f"{name}.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"{PACKAGE}.{name}"] = module
        spec.loader.exec_module(module)
        setattr(package, name, module)

    return package

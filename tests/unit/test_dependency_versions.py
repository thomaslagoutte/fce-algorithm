"""FR-019: the installed environment matches this layer's pin.

Scoped down per research.md R11 — this is a dependency-version check, not a run
manifest. Reads the declared pins from pyproject.toml itself (not duplicated as a
hardcoded literal here) so a deliberate upgrade is a one-line pyproject.toml edit,
not a two-place edit.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import numpy
import qiskit
import qiskit_aer
from packaging.requirements import Requirement

_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _declared_pin(package: str) -> str:
    data = tomllib.loads(_PYPROJECT.read_text())
    for dep in data["project"]["dependencies"]:
        req = Requirement(dep)
        if req.name == package:
            # Pins in pyproject.toml are exact ("==x.y.z"); take the version literal.
            (spec,) = list(req.specifier)
            assert spec.operator == "=="
            return spec.version
    raise AssertionError(f"{package} not found in pyproject.toml dependencies")


def test_qiskit_version_matches_pin() -> None:
    assert qiskit.__version__ == _declared_pin("qiskit")


def test_qiskit_aer_version_matches_pin() -> None:
    assert qiskit_aer.__version__ == _declared_pin("qiskit-aer")


def test_numpy_satisfies_qiskit_and_aer_constraints() -> None:
    # Verified in research.md R2: qiskit 2.3.1 requires numpy<3,>=1.21;
    # qiskit-aer 0.17.2 requires numpy>=1.16.3.
    installed = Requirement(f"numpy=={numpy.__version__}")
    (installed_spec,) = list(installed.specifier)
    version = installed_spec.version
    assert Requirement("numpy<3,>=1.21").specifier.contains(version)
    assert Requirement("numpy>=1.16.3").specifier.contains(version)

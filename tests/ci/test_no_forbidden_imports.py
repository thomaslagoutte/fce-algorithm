"""FR-014, FR-015: CI fails the build if any production module imports
`Statevector`, `Operator`, `expm`, or `fourierlearn.reference` — except
`reference.py` itself.

The scanner is AST-based (never executes or imports the scanned code), so it can
never accidentally trip its own prohibition.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

FORBIDDEN_NAMES = {"Statevector", "Operator", "expm"}
_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "fourierlearn"
_EXEMPT_MODULE = "reference.py"


def _scan_module(path: Path) -> set[str]:
    """Return the set of forbidden symbol names imported by the module at `path`."""
    tree = ast.parse(path.read_text(), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                full_name = alias.name
                bound_name = alias.asname or alias.name.split(".")[0]
                if full_name == "fourierlearn.reference" or full_name.endswith(".reference"):
                    found.add("reference")
                if bound_name in FORBIDDEN_NAMES:
                    found.add(bound_name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imported_name = alias.name
                if imported_name in FORBIDDEN_NAMES:
                    found.add(imported_name)
                if imported_name == "reference" and module.endswith("fourierlearn"):
                    found.add("reference")
                if module == "fourierlearn.reference" or module.endswith(".reference"):
                    found.add("reference")
    return found


def find_violations(src_root: Path, exempt_module: str = _EXEMPT_MODULE) -> dict[str, set[str]]:
    """Scan every *.py file under `src_root`, excluding `exempt_module`, and return
    {relative_path: forbidden_names_found} for any file with a violation."""
    violations: dict[str, set[str]] = {}
    for path in sorted(src_root.rglob("*.py")):
        if path.name == exempt_module:
            continue
        found = _scan_module(path)
        if found:
            violations[str(path.relative_to(src_root))] = found
    return violations


# --- Core assertions against the real, clean tree (FR-014, FR-015) --------------


def test_clean_tree_reports_no_violations() -> None:
    violations = find_violations(_SRC_ROOT)
    assert violations == {}, f"unexpected forbidden imports: {violations}"


def test_reference_module_itself_is_not_scanned() -> None:
    reference_path = _SRC_ROOT / "reference.py"
    assert reference_path.exists()
    # reference.py legitimately imports Statevector — confirm the scanner would
    # find it if not exempted, then confirm find_violations() exempts it correctly.
    assert "Statevector" in _scan_module(reference_path)
    assert "reference.py" not in find_violations(_SRC_ROOT)


# --- Guard-validation: prove the guard actually fires (explicit requirement) -----


def test_guard_fires_on_a_throwaway_forbidden_import(tmp_path: Path) -> None:
    throwaway = tmp_path / "_throwaway_ci_check.py"
    throwaway.write_text(
        textwrap.dedent(
            """
            from qiskit.quantum_info import Statevector

            def use_it():
                return Statevector.from_label("0")
            """
        )
    )
    violations = find_violations(tmp_path, exempt_module=_EXEMPT_MODULE)
    assert "_throwaway_ci_check.py" in violations
    assert "Statevector" in violations["_throwaway_ci_check.py"]

    throwaway.unlink()
    violations_after_removal = find_violations(tmp_path, exempt_module=_EXEMPT_MODULE)
    assert violations_after_removal == {}


def test_guard_fires_on_each_of_the_four_forbidden_symbols(tmp_path: Path) -> None:
    cases = {
        "operator_case.py": "from qiskit.quantum_info import Operator\n",
        "expm_case.py": "from scipy.linalg import expm\n",
        "reference_case.py": "from fourierlearn import reference\n",
        "reference_from_case.py": "from fourierlearn.reference import coefficients\n",
    }
    for filename, content in cases.items():
        (tmp_path / filename).write_text(content)

    violations = find_violations(tmp_path, exempt_module=_EXEMPT_MODULE)
    assert violations["operator_case.py"] == {"Operator"}
    assert violations["expm_case.py"] == {"expm"}
    assert violations["reference_case.py"] == {"reference"}
    assert violations["reference_from_case.py"] == {"reference"}

"""FR-014, FR-015: CI fails the build if any production module imports
`Statevector`, `Operator`, `expm`, or `fourierlearn.reference` — except
`reference.py` itself, and (Spec 6 FR-011/FR-012, Spec 8) any module named
in `_NARROWLY_EXEMPT_FROM_REFERENCE_ONLY`, each independently justified,
which is exempt from the `reference` prohibition only.

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

# Constitution Clarifications (Spec 6, 2026-08-21): the generalization-check
# mechanism (Constitution §8.2) must compare a fitted model's prediction
# against genuinely EXACT ground-truth dynamics -- never a finite-shot
# measurement or a finer-Trotter approximation, because neither can
# distinguish a real capability from an artifact of interpolating
# imperfect training labels (verified computationally: specs/006-experiment-
# models-layer/research.md R1 constructs a genuine overfitting artifact via
# null-space injection and confirms the check only correctly returns
# "refuted" when compared against the true oracle, not an approximation).
# `_exact_dynamics.py` is narrowly authorized to import `fourierlearn.reference`
# for that one purpose.
#
# Spec 8 (Constitution §11.6) adds a second, independently justified module:
# `_containment_oracle_check.py`, whose sole purpose is extracting the
# ansatz's true frequency support Omega via the oracle, to empirically
# verify Omega <= Lambda before any Lambda-restricted extraction is trusted
# (Hard Prohibition #6) -- also never used for training or feature
# construction.
#
# Neither module is exempted from the Statevector/Operator/expm prohibition,
# since neither has any legitimate reason to import those directly -- each
# only calls reference.py's own already-exempted functions. This tuple is
# the single, scalable place a future spec's own narrowly-justified module
# name is added -- the mechanism (a tuple, checked via `in`) already
# supports any number of entries without a further signature change; only
# this tuple's own contents grow.
_NARROWLY_EXEMPT_FROM_REFERENCE_ONLY: tuple[str, ...] = (
    "_exact_dynamics.py",
    "_containment_oracle_check.py",
)


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


def find_violations(
    src_root: Path,
    exempt_module: str = _EXEMPT_MODULE,
    narrow_exempt_modules: tuple[str, ...] = _NARROWLY_EXEMPT_FROM_REFERENCE_ONLY,
) -> dict[str, set[str]]:
    """Scan every *.py file under `src_root`, excluding `exempt_module` entirely
    and waiving only the `reference` finding for any module named in
    `narrow_exempt_modules` (Spec 6 FR-011/FR-012, Spec 8 -- each such module
    may still be flagged for Statevector/Operator/expm), and return
    {relative_path: forbidden_names_found} for any file with a remaining
    violation.

    `narrow_exempt_modules` has a safe default (the widened
    `_NARROWLY_EXEMPT_FROM_REFERENCE_ONLY` tuple) so every pre-existing call
    site (positional or `exempt_module=`-only keyword) continues to behave
    exactly as before this parameter existed. The mechanism scales to any
    number of future narrowly-exempt modules by growing this tuple alone --
    no further signature or comparison-logic change is needed."""
    violations: dict[str, set[str]] = {}
    for path in sorted(src_root.rglob("*.py")):
        if path.name == exempt_module:
            continue
        found = _scan_module(path)
        if path.name in narrow_exempt_modules:
            found = found - {"reference"}
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


# --- Spec 6 FR-011/FR-012: the narrow, explicitly justified exemption for
# `_exact_dynamics.py` (generalization check) ------------------------------------


def test_narrow_exemption_does_not_widen_to_other_modules(tmp_path: Path) -> None:
    """A module named anything other than `_exact_dynamics.py` that imports
    `fourierlearn.reference` MUST still be rejected -- proving the exemption
    is narrow, not a general widening of the rule."""
    (tmp_path / "some_other_experiment_module.py").write_text(
        "from fourierlearn import reference\n"
    )
    violations = find_violations(tmp_path, exempt_module=_EXEMPT_MODULE)
    assert violations["some_other_experiment_module.py"] == {"reference"}


def test_narrow_exemption_still_rejects_statevector_and_operator(tmp_path: Path) -> None:
    """The narrowly-exempt module itself is waived for `reference` only --
    it MUST still be flagged if it also imports Statevector/Operator/expm
    directly, since it has no legitimate reason to (it only calls
    reference.py's own already-exempted function)."""
    module_name = _NARROWLY_EXEMPT_FROM_REFERENCE_ONLY[0]  # "_exact_dynamics.py"
    (tmp_path / module_name).write_text(
        "from fourierlearn import reference\n"
        "from qiskit.quantum_info import Statevector\n"
    )
    violations = find_violations(tmp_path, exempt_module=_EXEMPT_MODULE)
    assert violations[module_name] == {"Statevector"}


def test_narrow_exemption_waives_only_reference_for_the_named_module(tmp_path: Path) -> None:
    """Sanity check: the named module importing ONLY `reference` (its sole
    authorized use) produces zero violations."""
    module_name = _NARROWLY_EXEMPT_FROM_REFERENCE_ONLY[0]  # "_exact_dynamics.py"
    (tmp_path / module_name).write_text(
        "from fourierlearn import reference\n"
    )
    violations = find_violations(tmp_path, exempt_module=_EXEMPT_MODULE)
    assert module_name not in violations


def test_narrow_exemption_generalizes_to_a_second_module(tmp_path: Path) -> None:
    """Guardrail 1 (Spec 8): the SAME two checks above, independently
    reproduced for the tuple's SECOND entry (`_containment_oracle_check.py`)
    -- proving the widened mechanism genuinely generalizes to any exempt
    module, not merely special-cased for exactly one hardcoded name."""
    module_name = _NARROWLY_EXEMPT_FROM_REFERENCE_ONLY[1]  # "_containment_oracle_check.py"

    (tmp_path / module_name).write_text("from fourierlearn import reference\n")
    violations = find_violations(tmp_path, exempt_module=_EXEMPT_MODULE)
    assert module_name not in violations, "reference-only import must be waived for this module too"

    (tmp_path / module_name).write_text(
        "from fourierlearn import reference\n"
        "from qiskit.quantum_info import Operator\n"
    )
    violations = find_violations(tmp_path, exempt_module=_EXEMPT_MODULE)
    assert violations[module_name] == {"Operator"}, "Operator must still be flagged for this module too"

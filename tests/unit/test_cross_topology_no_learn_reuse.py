"""Spec 12 T002 — FR-003/SC-002 (Critical Mandate 2, this round): an AST-
based scanner (mirroring `tests/ci/test_no_forbidden_imports.py`'s own
technique, but its own file — that file's scope is a project-wide
invariant, `Statevector`/`Operator`/`expm`/`reference`, unrelated to this
one-module-vs-one-module non-reuse boundary against `learn.py`) confirming
`src/fourierlearn/cross_topology.py` never imports `learn.py`'s `estimate_
y`, `TrainingRow`, `build_sensing_matrix`, `LassoRegressionBackend`, or
`fit_model`.

**This test file runs UNCONDITIONALLY in the default `pytest tests/`
suite. No `@pytest.mark.skip`, `@pytest.mark.slow`, or any other
conditional marker may be applied to it or to any test function inside
it** (this round's own Critical Mandate 2) — and this repository has no
such marker mechanism configured at all (`pyproject.toml`'s
`[tool.pytest.ini_options]` has only `testpaths`, confirmed during Spec
11), so there is no marker this test could even be given.
"""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_LEARN_SYMBOLS = frozenset(
    {"estimate_y", "TrainingRow", "build_sensing_matrix", "LassoRegressionBackend", "fit_model"}
)

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "fourierlearn"
_TARGET_MODULE = "cross_topology.py"


def _scan_module_for_learn_reuse(path: Path) -> set[str]:
    """Return the set of forbidden `learn.py` symbol names imported by the
    module at `path` — via `import fourierlearn.learn` + attribute access,
    `from fourierlearn.learn import X`, or `from fourierlearn import learn`
    + attribute access. AST-based: never executes or imports the scanned
    code, so it can never accidentally trip on its own analysis."""
    tree = ast.parse(path.read_text(), filename=str(path))
    found: set[str] = set()
    learn_module_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "fourierlearn.learn":
                    learn_module_aliases.add(alias.asname or alias.name.split(".")[-1])
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "fourierlearn.learn":
                for alias in node.names:
                    if alias.name in FORBIDDEN_LEARN_SYMBOLS:
                        found.add(alias.name)
            elif module == "fourierlearn":
                for alias in node.names:
                    if alias.name == "learn":
                        learn_module_aliases.add(alias.asname or alias.name)

    if learn_module_aliases:
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id in learn_module_aliases and node.attr in FORBIDDEN_LEARN_SYMBOLS:
                    found.add(node.attr)

    return found


def test_cross_topology_module_never_imports_learn_flipped_direction_symbols() -> None:
    path = _SRC_ROOT / _TARGET_MODULE
    assert path.is_file(), f"expected {path} to exist"
    violations = _scan_module_for_learn_reuse(path)
    assert not violations, (
        f"{_TARGET_MODULE} imports/uses learn.py's flipped-direction symbols: {violations} "
        "(FR-003 forbids this — see spec.md Clarifications and research.md R1)"
    )


def test_forbidden_symbol_set_is_exactly_the_five_named_in_spec() -> None:
    """Guardrail on the guardrail: confirms this test's own forbidden-set
    constant has not silently drifted from FR-003's exact, named list."""
    assert FORBIDDEN_LEARN_SYMBOLS == {
        "estimate_y",
        "TrainingRow",
        "build_sensing_matrix",
        "LassoRegressionBackend",
        "fit_model",
    }

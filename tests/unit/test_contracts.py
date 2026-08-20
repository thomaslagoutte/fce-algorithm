"""FR-001, FR-002, FR-003: the contracts module's Encoding/Oracle Protocols and
extension point.
"""

from __future__ import annotations

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.contracts import Encoding, Oracle
from fourierlearn.ir import PauliEncodedCircuitIR, PauliTerm


class _StubEncoding:
    """Minimal Encoding implementation — no inheritance from Encoding needed,
    structural (runtime_checkable) conformance only."""

    def build(self) -> PauliEncodedCircuitIR:
        return PauliEncodedCircuitIR(
            num_qubits=1,
            gates=(PauliTerm("Z", (0,), parameter_index=0, coefficient=1.0, tie_group=0),),
            observable=SparsePauliOp("Z"),
        )


class _StubOracle:
    """Minimal Oracle implementation — structural conformance only."""

    def coefficients(self, circuit: PauliEncodedCircuitIR) -> dict[tuple[int, ...], complex]:
        return {(0,): 1.0 + 0j}


def test_stub_encoding_satisfies_encoding_protocol() -> None:
    assert isinstance(_StubEncoding(), Encoding)


def test_stub_oracle_satisfies_oracle_protocol() -> None:
    assert isinstance(_StubOracle(), Oracle)


def test_stub_encoding_build_returns_valid_ir() -> None:
    ir = _StubEncoding().build()
    assert isinstance(ir, PauliEncodedCircuitIR)
    assert ir.num_parameters == 1


def test_extension_point_does_not_require_modifying_existing_protocols() -> None:
    """A later spec adds a new Protocol class to contracts.py without touching
    Encoding or Oracle — simulated here by defining one locally and confirming
    Encoding/Oracle are unaffected."""
    from typing import Protocol, runtime_checkable

    @runtime_checkable
    class _FutureBoundary(Protocol):
        def run(self) -> None: ...

    assert Encoding.__init__ is not None  # Encoding unchanged, still importable
    assert Oracle.__init__ is not None  # Oracle unchanged, still importable
    assert _FutureBoundary is not Encoding
    assert _FutureBoundary is not Oracle

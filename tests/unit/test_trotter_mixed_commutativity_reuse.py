"""Mixed Fixed/Encoded Trotter Frontend — FR-004/FR-010/SC-004.

The encoded portion of `mixed_trotter_frontend` MUST route through
`pauli_pqc.build_ir` unchanged: a parameterized (encoded) group whose terms
do not commute across the same tie group MUST raise the IDENTICAL error
`build_ir` itself raises for that input — never a distinct, locally
reimplemented check.
"""

from __future__ import annotations

import pytest
from qiskit.quantum_info import SparsePauliOp

from fourierlearn.encodings.pauli_pqc import PauliUpload, build_ir
from fourierlearn.encodings.trotter import CouplingGroup, CouplingGroupTerm, mixed_trotter_frontend


def _noncommuting_group() -> CouplingGroup:
    return CouplingGroup(
        "J", (CouplingGroupTerm("X", (0,), 1.0), CouplingGroupTerm("Z", (0,), 1.0))
    )


def test_noncommuting_encoded_group_raises_identical_error_to_direct_build_ir_call() -> None:
    observable = SparsePauliOp("Z")
    tau, r = 0.5, 2
    group = _noncommuting_group()

    direct_uploads = [
        PauliUpload(
            pauli=term.pauli,
            qubits=term.qubits,
            parameter_label=group.label,
            tie_group=0,
            coefficient=-term.weight * tau / (3.141592653589793 * r),
        )
        for term in group.terms
    ]
    with pytest.raises(ValueError) as direct_excinfo:
        build_ir(num_qubits=1, uploads=direct_uploads, observable=observable)

    with pytest.raises(ValueError) as mixed_excinfo:
        mixed_trotter_frontend(
            num_qubits=1, group_specs=[group], tau=tau, r=r, observable=observable
        )

    assert type(direct_excinfo.value) is type(mixed_excinfo.value)
    assert str(direct_excinfo.value) == str(mixed_excinfo.value)
    assert "non-commuting" in str(mixed_excinfo.value)

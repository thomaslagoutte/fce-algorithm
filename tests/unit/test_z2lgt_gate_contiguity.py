"""T004 — Constitution §11.9/§11.10: the commuting family F={Z_v}∪{X_e}
used by Theorem 6.1's containment derivation must be applied as one
contiguous, uninterrupted block, asserted directly on the compiled IR's
own gate tuple -- never only in a comment."""

from __future__ import annotations

from qiskit.quantum_info import SparsePauliOp

from fourierlearn.ir import PauliTerm
from fourierlearn.z2lgt import Z2LGTEdge, Z2LGTGraph, build_z2_lgt_model, to_circuit_ir


def test_mass_and_electric_gates_precede_every_hopping_gate() -> None:
    graph = Z2LGTGraph(num_matter_sites=2, edges=(Z2LGTEdge(site_i=0, site_j=1),))
    model = build_z2_lgt_model(
        graph,
        mass_couplings={0: 1.0, 1: -1.0},
        electric_couplings={0: 1.0},
        hopping_couplings={0: 1.0},
    )
    ir = to_circuit_ir(model, tau=1.0, r=1, observable=SparsePauliOp("I" * model.num_sites))

    pauli_terms = [g for g in ir.gates if isinstance(g, PauliTerm)]
    is_hopping = [t.pauli in ("XZX", "YZY") for t in pauli_terms]
    # The commuting family F (mass+electric, both single-qubit Z/X) must
    # form one contiguous block preceding every hopping gate -- i.e. once
    # a hopping gate appears, no F-gate may appear after it.
    first_hopping_index = is_hopping.index(True)
    assert not any(is_hopping[:first_hopping_index]), "no hopping gate before the F-block ends"
    assert all(is_hopping[first_hopping_index:]), "F-block (mass/electric) must not be interrupted by hopping"

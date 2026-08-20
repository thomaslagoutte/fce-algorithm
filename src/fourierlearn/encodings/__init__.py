"""Encodings layer — FR-001..FR-013.

Two frontends lowering a domain-familiar circuit description into the
Foundation Layer's `PauliEncodedCircuitIR`: `pauli_pqc.build_ir` (an ordered
list of Pauli-string uploads) and `trotter.trotter_frontend` (one or more
Hamiltonian coupling groups, a fixed evolution time, and a fixed Trotter step
count), the latter delegating to the former (Constitution §9.4).
"""

from __future__ import annotations

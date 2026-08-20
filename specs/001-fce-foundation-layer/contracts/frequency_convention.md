# Contract: Frequency Convention Module (`src/fourierlearn/frequency.py`)

Not a `Protocol` — this module has exactly one implementation, ever (spec FR-008: "a
single frequency-convention module MUST be the sole source of truth"). This document
fixes its public function signatures and pinned semantics so every consumer across
every future layer imports the same behavior rather than reimplementing any part of
it (Constitution §6.1).

## Public surface

```python
def pre_parity_range(r_j: int, upload_count: int) -> range:
    """The canonical pre-parity integer domain for one coordinate:
    l in {-2 * r_j * upload_count, ..., 2 * r_j * upload_count}.
    """

def to_post_parity(l: int) -> int:
    """l -> l / 2. Raises ValueError on odd `l` (Constitution §10.1 — no plausible
    wrong answer on a degenerate input); never silently truncates."""

def to_pre_parity(m: int) -> int:
    """Inverse of `to_post_parity`: m -> 2 * m."""

def decode_twos_complement(bits: "Sequence[int]") -> int:
    """Standard two's-complement decoding of a fixed-width bit sequence into a
    signed integer, MSB-first."""

def coordinate_order(labels: "Sequence[str]") -> "tuple[str, ...]":
    """The one canonical ordering of frequency-vector coordinates. Every function
    that builds or indexes a multi-dimensional frequency array (the oracle's grid
    axes, a later encoding's parameter list, a later learner's feature order) MUST
    order its axes this way."""

def dft_frequencies(num_points: int) -> "np.ndarray":
    """The FFT-bin-index-to-signed-`l` mapping: for `numpy.fft.fft`/`fftn`'s bin `k`
    (0-indexed), returns `k` for `k <= num_points // 2` and `k - num_points`
    otherwise — equivalent to `numpy.fft.fftfreq(num_points) * num_points` rounded to
    int. Requires `num_points` odd (raises otherwise) — always true for the oracle's
    `4*r_j*L+1`-point grids. Any function reading an FFT output array by frequency
    (the oracle's coefficient indexing) MUST call this rather than inlining
    `fftfreq`/`fftshift` arithmetic itself — that would be exactly the independent
    frequency-indexing definition FR-009 forbids, and another place a sign could
    silently flip alongside FR-021's gate-convention risk."""

def register_width(uploads: int, r_j: int) -> int:
    """Number of bits needed to address the pre-parity range `pre_parity_range(r_j,
    uploads)` in two's complement:
    ceil(log2(4 * r_j * uploads + 1)).

    Directly sourced, not derived: `docs/references/equivariant FCE Z2LGT report.pdf`,
    §5.3 ("Register sizing", extracted page 13) states this exact formula as the
    "Frequency register width per coordinate" (research.md R12).

    Unit-tested directly here against hand-computed values (spec FR-010). The
    *behavioral* regression test — under-sizing a real, constructed register and
    confirming the resulting aliasing is caught — is deferred to Spec 3 (Circuit
    Construction), per the TODO recorded in spec.md's Assumptions, since no register
    exists to under-size until circuits are built.
    """
```

## Pinned sign convention (spec FR-008, FR-021)

`l = Λ - Λ'`: the pre-parity integer accumulates `+1` per even-parity contribution and
`-1` per odd-parity one, so `l` carries the same sign as the exponent in `e^{iπ c α
l}`. No function anywhere in the codebase may introduce an independent sign for a
frequency — every sign-bearing quantity is either this `l` directly, or produced by
one of the functions above.

**This convention includes the IR's own gate-construction mapping.** `PauliTerm.to_gate()`
(`contracts/ir_types.py`) is the one place this layer turns `e^{iπcαP}` into a
concrete Qiskit gate, via `PauliEvolutionGate(P, time=-π c α)` — the `-π` factor
exists specifically because `PauliEvolutionGate(P, time=t)` implements `e^{-itP}`,
verified in-session against the installed Qiskit version rather than assumed
(research.md R6). A sign flip here has the *same effect* as a sign flip in `l` itself
(`l ↔ -l`) but is invisible on any real-coefficient test, so it is covered by its own
dedicated `Operator`-equivalence test (spec FR-021/SC-009), not folded into the
oracle's coefficient-comparison tests alone.

## What this module does *not* define

- Qiskit's own little-endian qubit-index convention (used inside `reference.py`'s
  state construction, research.md R6) is a separate concern from "coordinate
  ordering" here, which is about frequency-vector axis order, not qubit order. The
  two are never to be conflated (research.md R7).
- The concrete meaning of `Λ`/`Λ'` (which physical quantity is "even-parity" vs.
  "odd-parity") is fixed by whichever encoding produces the IR — this module only
  fixes the arithmetic performed on the resulting integer, since that is the part
  this foundation layer can pin before any concrete encoding exists.

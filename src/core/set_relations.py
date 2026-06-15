"""Set Relations: subset, complement, Z-relation, K-relation, set complex, nexus set."""

from itertools import combinations
from music21 import chord


def complement(pc_set: list[int]) -> list[int]:
    """Return the literal complement (remaining 12 pcs) of a pc-set."""
    return sorted(set(range(12)) - set(pc_set))


def _normalize(pcs: list[int]) -> tuple:
    """Canonical sorted-tuple representation of a pc-set (deduped)."""
    return tuple(sorted(set(pcs)))


def _tn_equivalent_key(pcs: list[int]) -> tuple:
    """Return a canonical key for Tn equivalence (invariant under transposition).
    The key is the sorted interval pattern starting from 0."""
    s = sorted(set(pcs))
    if not s:
        return ()
    return tuple(sorted((x - s[0]) % 12 for x in s))


def _tni_equivalent_key(pcs: list[int]) -> tuple:
    """Return a canonical key for TnI equivalence (invariant under Tn and inversion).
    The key is the lexicographically smaller of the Tn key and inverted Tn key."""
    tn = _tn_equivalent_key(pcs)
    # Inversion: map each pc x → (12 - x) % 12, then compute Tn key
    inv = tuple(sorted((12 - x) % 12 for x in pcs))
    tn_inv = _tn_equivalent_key(inv)
    return min(tn, tn_inv)


def is_tn_or_tni_equivalent(a: list[int], b: list[int]) -> bool:
    """Check Tn/TnI equivalence (same set class) using canonical keys."""
    return _tni_equivalent_key(a) == _tni_equivalent_key(b)


def interval_vector(pc_set: list[int]) -> list[int]:
    """Return the interval vector of a pc-set (ic1 through ic6 counts)."""
    return list(chord.Chord(pc_set).intervalVector)


def _precompute_iv(universe: list[list[int]]) -> dict:
    """Precompute interval vectors for all sets in the universe."""
    return {_normalize(s): interval_vector(s) for s in universe}


def z_relations(target: list[int], universe: list[list[int]],
                iv_cache: dict = None) -> list[list[int]]:
    """Find sets in the universe that are Z-related to target (same IV, not Tn/TnI)."""
    t_key = _tni_equivalent_key(target)
    if iv_cache is None:
        t_iv = interval_vector(target)
    else:
        t_iv = iv_cache.get(_normalize(target), interval_vector(target))
    result = []
    for s in universe:
        n = _normalize(s)
        if n == _normalize(target):
            continue
        if _tni_equivalent_key(s) == t_key:
            continue
        if iv_cache is not None:
            s_iv = iv_cache.get(n)
        else:
            s_iv = interval_vector(s)
        if s_iv == t_iv:
            result.append(s)
    return result


def subset_superset_relations(target: list[int], universe: list[list[int]]):
    """Find subsets and supersets of target in the universe."""
    t_set = set(target)
    subsets = []
    supersets = []
    for s in universe:
        s_set = set(s)
        if s_set == t_set:
            continue
        if s_set.issubset(t_set):
            subsets.append(s)
        elif t_set.issubset(s_set):
            supersets.append(s)
    return subsets, supersets


def k_relations(target: list[int], universe: list[list[int]]) -> list[list[int]]:
    """K-relation: set X is included in BOTH target and complement(target)."""
    comp = set(complement(target))
    t_set = set(target)
    result = []
    for s in universe:
        s_set = set(s)
        if s_set.issubset(t_set) and s_set.issubset(comp):
            result.append(s)
    return result


def invariant_containments(target: list[int], universe: list[list[int]]) -> list[list[int]]:
    """Sets in universe that contain target exactly (invariance, T=0)."""
    t_set = set(target)
    return [s for s in universe if t_set.issubset(set(s)) and set(s) != t_set]


def set_complex_around(target: list[int], universe: list[list[int]],
                       iv_cache: dict = None) -> dict:
    """Compute the set complex around target: all related sets grouped by relation type."""
    subs, supers = subset_superset_relations(target, universe)
    return {
        "target": target,
        "complement": complement(target),
        "interval_vector": interval_vector(target),
        "subsets": subs,
        "supersets": supers,
        "z_related": z_relations(target, universe, iv_cache),
        "k_related": k_relations(target, universe),
        "invariants": invariant_containments(target, universe),
    }


def nexus_set(universe: list[list[int]], progress_callback=None) -> dict:
    """Find the nexus set(s): maximally related to all others in the universe.

    Returns ALL candidates that tie for the highest score (not just the first).
    """
    iv_cache = _precompute_iv(universe)
    # Precompute TnI keys for Z-relation check
    tn_cache = {_normalize(s): _tni_equivalent_key(s) for s in universe}

    best_candidates = []
    best_score = -1

    total = len(universe)
    for idx, target in enumerate(universe):
        if progress_callback:
            progress_callback(idx, total)
        cpx = set_complex_around(target, universe, iv_cache)
        score = (len(cpx["subsets"]) + len(cpx["supersets"]) +
                 len(cpx["z_related"]) + len(cpx["k_related"]) +
                 len(cpx["invariants"]))
        if score > best_score:
            best_score = score
            best_candidates = [(target, cpx)]
        elif score == best_score:
            best_candidates.append((target, cpx))

    return {
        "nexus_candidates": [c[0] for c in best_candidates],
        "score": best_score,
        "complexes": [c[1] for c in best_candidates],
    }

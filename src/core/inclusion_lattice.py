"""Inclusion lattice: visualize subset relationships in a pitch-class set with Forte classification."""

from itertools import combinations
from music21 import chord


def get_forte_class(pc_list: list[int]) -> str:
    """Get the Forte class name for a list of pitch classes."""
    return chord.Chord(pc_list).forteClass


def generate_all_subsets(pc_set: list[int], min_size: int = 3, max_size: int = 6) -> list[tuple]:
    """Generate all subsets of a pitch-class set within the given size range."""
    mother = sorted(set(pc_set))
    all_subs = []
    max_k = min(max_size + 1, len(mother) + 1)
    for k in range(min_size, max_k):
        for c in combinations(mother, k):
            all_subs.append(tuple(sorted(c)))
    return all_subs


def build_inclusion_graph(subsets: list[tuple]):
    """Build a NetworkX directed graph from subsets with inclusion (superset→subset) edges.

    Only compares subsets of adjacent sizes (k vs k+1) to avoid O(n²) blowup.
    """
    import networkx as nx

    G = nx.DiGraph()
    for s in subsets:
        G.add_node(s)

    # Group by size; only edges between adjacent levels are possible
    by_size = {}
    for s in subsets:
        by_size.setdefault(len(s), []).append(s)

    # Pre-compute sets once
    set_cache = {s: set(s) for s in subsets}

    for size in sorted(by_size):
        for small in by_size.get(size, []):
            small_set = set_cache[small]
            for large in by_size.get(size + 1, []):
                if small_set.issubset(set_cache[large]):
                    G.add_edge(large, small)

    levels = {}
    for node in G.nodes():
        lvl = len(node)
        levels.setdefault(lvl, []).append(node)

    return G, levels


def compute_layout(levels: dict, y_gap: float = 1.3, x_gap: float = 2.2) -> dict:
    """Compute a layered layout for the inclusion lattice graph."""
    pos = {}
    y = 0
    for lvl in sorted(levels.keys(), reverse=True):
        nodes = levels[lvl]
        x = -(len(nodes) - 1) * x_gap / 2
        for node in nodes:
            pos[node] = (x, y)
            x += x_gap
        y -= y_gap
    return pos


def build_labels(graph, pc_set: list[int] = None) -> dict:
    """Build node labels with pitch-class string and Forte class."""
    labels = {}
    for node in graph.nodes():
        pitch_str = "".join(map(str, node))
        forte_str = get_forte_class(list(node))
        labels[node] = f"{pitch_str}\n{forte_str}"
    return labels

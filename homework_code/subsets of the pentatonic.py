import numpy as np
from itertools import combinations
from music21 import chord

arr5_35 = np.array([0,2,4,7,9])
print(arr5_35)

arr_tetrachords = np.array(list(combinations(arr5_35, 4))) #combinations() r-length tuples, in sorted order, no repeated elements
print(arr_tetrachords)

arr_triads = np.array(list(combinations(arr5_35, 3)))
print(arr_triads)

all_subsets = list(arr_tetrachords) + list(arr_triads)

def to_int(pcs):
    return [int(x) for x in pcs]

all_forte = []
all_pcs = []

for s in all_subsets:
    pcs = to_int(s)
    c = chord.Chord(pcs)
    all_pcs.append(pcs)
    all_forte.append(c.forteClass)

# Transpose to NumPy array
forte_np = np.array(all_forte)
pcs_np = np.array(all_pcs, dtype=object)

unique_forte, idx = np.unique(forte_np, return_index=True)
final_pcs = pcs_np[idx]


for pcs in final_pcs:
    c = chord.Chord(list(pcs))
    print(f"{pcs} -> normalOrder: {c.normalOrder} | Prime: {c.primeForm} | Forte: {c.forteClass}")
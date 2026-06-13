from music21 import pitch, chord

collections = [
    [6,8,11,1,4],
    [7,10,0,3,5],
    [2,5,7,9,0],
    [7,9,0],
    [6,3,8,11],
    [0,7,2,9],
    [4,11,2,9],
    [0,7,5,2],
    [0,1,5,10],
    [0,7,2,10]
]

for pcs in collections:
    c = chord.Chord(pcs)
    print(f"{pcs} -> Forte: {c.normalOrder} | Prime Form: {c.primeForm} | Forte Class: {c.forteClass}")

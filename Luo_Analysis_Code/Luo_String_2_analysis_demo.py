from music21 import converter,note,stream,pitch,instrument

# local address of my file
file_path = r"C:\Music 21\Corpus\My local corpus\_Luo String Quartet No 2 m1-m2.musicxml"
score = converter.parse(file_path)


vlnPart = score.getElementById('Viola')
mRange = vlnPart.measures(1, 9)
mRange.show()

print(', '.join([str(p) for p in mRange.pitches]))

print(', '.join([str(p.pitchClass) for p in mRange.pitches]))

for n in mRange.recurse().notes:
    if n.tie is None or n.tie.type == 'start':
        n.lyric = n.pitch.pitchClassString
mRange.show()















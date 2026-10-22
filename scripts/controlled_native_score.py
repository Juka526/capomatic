"""Create a controlled source-object PDF, not a claimed ordinary-OMR fixture.

Korean lyrics are actual source alpha layers. They are never OCR-rewritten.
The MusicXML reference and all source geometry are retained in the PDF.
"""
import argparse
import json
from pathlib import Path

from music21 import clef, key, meter, note, stream
from backend.omr_v3.native_pdf import font_hashes, source_pdf


def make_fixture(fifths=0):
    part = stream.Part()
    pitches = {0: ['C5', 'E5', 'A4', 'F4'], 5: ['B4', 'D#5', 'G#4', 'E4']}[fifths]
    for i, pitch in enumerate(pitches, 1):
        measure = stream.Measure(number=i)
        if i == 1:
            measure.insert(0, clef.TrebleClef())
            measure.insert(0, key.KeySignature(fifths))
            measure.insert(0, meter.TimeSignature('4/4'))
        measure.insert(0, note.Note(pitch, quarterLength=4))
        part.append(measure)
    xml_path = stream.Score([part]).write('musicxml')
    xml = xml_path.read_bytes()
    profile = {'size': [1600, 700], 'interline': 24, 'staff_top': 180,
               'staff_span': [50, 1520], 'bar_x': [420, 695, 970, 1245, 1520],
               'note_x': [550, 825, 1100, 1375], 'font_sha256': font_hashes(),
               'lyrics': [
                   {'text': '주님을 사랑해요', 'xy': [440, 370], 'font_size': 34,
                    'extenders': [[800, 415, 1420, 415]]},
                   {'text': '우리 함께 노래해요', 'xy': [440, 455], 'font_size': 34,
                    'extenders': [[860, 500, 1420, 500]]},
               ]}
    return source_pdf([profile], [xml]), profile, xml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=False)
    data, profile, xml = make_fixture()
    (args.out/'source.pdf').write_bytes(data)
    (args.out/'source.musicxml').write_bytes(xml)
    (args.out/'source-layout.json').write_text(json.dumps(profile, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

"""Small independent .omr/MusicXML examples using pinned Audiveris JAXB fields."""

from pathlib import Path
import zipfile


def sheet_xml():
    lines = ''.join(
        f'<line><point x="20" y="{y}"/><point x="300" y="{y+2}"/></line>'
        for y in (80, 90, 100, 110, 120)
    )
    return f'''<sheet><picture width="400" height="300"/>
    <scale><interline main="10"/></scale><page id="1"><system id="1">
    <stack id="1" left="20" right="300" duration="1/2">
      <slot id="2" x-offset="180" time-offset="1/4"/>
      <slot id="1" x-offset="80" time-offset="0"/>
    </stack><part id="1"><staff id="1"><lines>{lines}</lines></staff>
    <measure id="1"><head-chords>10 20</head-chords><keys>70</keys><clefs>72</clefs>
      <voice id="1"><slots>
        <entry><key>2</key><value chord="20" status="BEGIN"/></entry>
        <entry><key>1</key><value chord="10" status="BEGIN"/></entry>
      </slots></voice></measure></part>
    <sig><inters>
      <head id="1" staff="1" pitch="3" shape="NOTEHEAD_BLACK" grade="0.7" ctx-grade="0.9">
        <bounds x="95" y="111" w="10" h="8"/><pivot x="100" y="115"/></head>
      <head id="2" staff="1" pitch="2" shape="NOTEHEAD_BLACK" grade="0.8">
        <bounds x="195" y="106" w="10" h="8"/></head>
      <head-chord id="10" staff="1"/><head-chord id="20" staff="1"/>
      <stem id="11" staff="1"><median><p1 x="105" y="70"/><p2 x="105" y="115"/></median></stem>
      <stem id="21" staff="1"><top x="205" y="72"/><bottom x="205" y="110"/></stem>
      <beam id="30" height="4"><median><p1 x="105" y="70"/><p2 x="205" y="72"/></median></beam>
      <beam-hook id="31" height="4"><median><p1 x="105" y="77"/><p2 x="120" y="77"/></median></beam-hook>
      <beam-group id="32"/>
      <alter id="40" staff="1" shape="SHARP"><bounds x="80" y="105" w="6" h="17"/></alter>
      <augmentation-dot id="41" staff="1"><bounds x="110" y="111" w="3" h="3"/></augmentation-dot>
      <flag id="42"><bounds x="104" y="70" w="8" h="12"/></flag>
      <ledger id="43" staff="1" height="1"><median><p1 x="92" y="130"/><p2 x="110" y="130"/></median></ledger>
      <slur id="50" tie="true"><curve x1="100" y1="120" ctrlx1="125" ctrly1="140" ctrlx2="175" ctrly2="140" x2="200" y2="115"/></slur>
      <lyric-line id="60" role="Lyrics"/><lyric-item id="61" value="word" staff="1"><bounds x="92" y="126" w="30" h="10"/></lyric-item>
      <sentence id="62" role="Title"/><word id="63" value="Title"><bounds x="100" y="20" w="70" h="15"/><location x="100" y="32"/></word>
      <word id="64" value="Copyright"><bounds x="100" y="270" w="70" h="10"/></word>
      <sentence id="65" role="ChordName"/><word id="66" value="D"><bounds x="90" y="50" w="10" h="10"/></word>
      <key id="70" staff="1" fifths="2"/><key-alter id="71" staff="1" shape="SHARP"><bounds x="40" y="75" w="10" h="30"/></key-alter>
      <clef id="72" staff="1" shape="G_CLEF"><bounds x="20" y="70" w="15" h="60"/></clef>
      <time-whole id="73" staff="1" shape="TIME_TWO_FOUR"><bounds x="60" y="80" w="15" h="40"/></time-whole>
    </inters><relations>
      <relation source="10" target="1"><containment/></relation>
      <relation source="20" target="2"><containment/></relation>
      <relation source="1" target="11"><head-stem/></relation>
      <relation source="2" target="21"><head-stem/></relation>
      <relation source="30" target="11"><beam-stem/></relation>
      <relation source="30" target="21"><beam-stem/></relation>
      <relation source="31" target="11"><beam-stem/></relation>
      <relation source="32" target="30"><containment/></relation>
      <relation source="32" target="31"><containment/></relation>
      <relation source="40" target="1"><alter-head/></relation>
      <relation source="41" target="1"><augmentation/></relation>
      <relation source="42" target="11"><flag-stem/></relation>
      <relation source="50" target="1"><slur-head side="LEFT"/></relation>
      <relation source="50" target="2"><slur-head side="RIGHT"/></relation>
      <relation source="60" target="61"><containment/></relation>
      <relation source="62" target="63"><containment/></relation>
      <relation source="65" target="66"><containment/></relation>
      <relation source="70" target="71"><containment/></relation>
    </relations></sig></system></page></sheet>'''


def book(tmp_path, xml=None, name='score.omr'):
    path = tmp_path / name
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('sheet#1/sheet#1.xml', xml if xml is not None else sheet_xml())
    return path


def musicxml(tmp_path, pitches=('F#4', 'G4'), name='source.musicxml'):
    from music21 import clef, key, meter, note, stream

    score = stream.Score()
    part = stream.Part(id='P1')
    measure = stream.Measure(number=1)
    measure.append([clef.TrebleClef(), key.KeySignature(2), meter.TimeSignature('2/4')])
    for p in pitches:
        measure.append(note.Note(p, quarterLength=1))
    part.append(measure)
    score.append(part)
    path = tmp_path / name
    score.write('musicxml', fp=str(path))
    return path


def transposed(tmp_path, source, semitones):
    from music21 import converter
    from backend.omr_v3.transpose import transpose_score

    score = converter.parse(str(source))
    transpose_score(score, semitones)
    target = tmp_path / 'target.musicxml'
    score.write('musicxml', fp=str(target))
    return target

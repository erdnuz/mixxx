"""evaluate.py against a minimal Mixxx-like database."""
import json, os, sqlite3, sys, tempfile
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from stemprep.evaluate import base_label, marked_cues, score


def test_evaluate():
    assert base_label("Drop 2") == "DROP" and base_label("breakdown") == "BREAKDOWN"
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        track = d / "Artist - Song.mp3"
        track.write_bytes(b"x")
        # analysis: 120 BPM (bar = 2 s); drop at 60 s, breakdown at 90 s, extra drop at 150 s
        (d / "Artist - Song.mp3.structure.json").write_text(json.dumps({
            "bpm": 120, "sections": [
                {"start": 0, "end": 60, "label": "Intro"},
                {"start": 60, "end": 90, "label": "Drop"},
                {"start": 90, "end": 150, "label": "Breakdown"},
                {"start": 150, "end": 180, "label": "Drop 2"}]}))
        db = d / "mixxxdb.sqlite"
        con = sqlite3.connect(db)
        con.executescript("""
            CREATE TABLE track_locations (id INTEGER PRIMARY KEY, location TEXT);
            CREATE TABLE library (id INTEGER PRIMARY KEY, location INTEGER, samplerate INTEGER);
            CREATE TABLE crates (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE crate_tracks (crate_id INTEGER, track_id INTEGER);
            CREATE TABLE cues (id INTEGER PRIMARY KEY, track_id INTEGER, type INTEGER,
                               position REAL, length REAL, hotcue INTEGER, label TEXT, color INTEGER);
        """)
        con.execute("INSERT INTO track_locations VALUES (1, ?)", (str(track),))
        con.execute("INSERT INTO library VALUES (1, 1, 44100)")
        con.execute("INSERT INTO crates VALUES (1, 'stemprep checked')")
        con.execute("INSERT INTO crate_tracks VALUES (1, 1)")
        sp = lambda seconds: seconds * 44100 * 2  # engine samples
        con.executemany("INSERT INTO cues (track_id, type, position, hotcue, label) VALUES (1,1,?,?,?)", [
            (sp(61.0), 0, "DROP"),        # within a bar of 60: found
            (sp(120.0), 1, "BREAKDOWN"),  # 30 s off: missed
            (sp(150.5), 2, "drop 2"),     # found
            (sp(10.0), 3, "my cue"),      # not a section label: ignored
        ])
        con.execute("INSERT INTO cues (track_id, type, position, hotcue, label) VALUES (1,0,?,-1,'DROP')",
                    (sp(5.0),))  # not a hot cue: ignored
        con.commit()
        con.close()

        cues = marked_cues(db, "stemprep checked")
        assert sorted(l for _, l in cues[str(track)]) == ["BREAKDOWN", "DROP", "DROP"]
        report = score(cues)
        assert report["DROP"] == {"found": 2, "of": 2, "recall": 1.0, "extra": 0}
        assert report["BREAKDOWN"]["found"] == 0 and report["BREAKDOWN"]["extra"] == 1


if __name__ == "__main__":
    test_evaluate()
    print("ok")

"""Playlist tracking with a stand-in for spotDL (no network needed)."""
import os, sys, tempfile
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from stemprep.playlists import PlaylistStore, sync_playlist, write_m3u

URL = "https://open.spotify.com/playlist/abc123?si=xyz"


def song(i):
    return SimpleNamespace(song_id=f"id{i}", name=f"Title {i}", artists=[f"Artist {i}"])


class FakeDownloader:
    def __init__(self):
        self.songs = [song(1), song(2), song(3)]
        self.downloaded = []

    def fetch(self, url):
        return "130 fweak", list(self.songs)

    def download(self, songs, folder):
        folder.mkdir(parents=True, exist_ok=True)
        out = {}
        for s in songs:
            # an mp3 that was already there counts, like SpotifyDownloader.find_existing
            existing = folder / f"Artist {s.song_id[2:]} - {s.name}.mp3"
            if existing.exists():
                out[s.song_id] = existing
                continue
            p = folder / f"Artist {s.song_id[2:]} - {s.name}.m4a"
            p.write_bytes(b"x")
            self.downloaded.append(s.song_id)
            out[s.song_id] = p
        return out


def test_sync():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        downloads = root / "Downloads"
        # a track the user already had from an earlier spotDL download
        (downloads / "130 fweak").mkdir(parents=True)
        (downloads / "130 fweak" / "Artist 2 - Title 2.mp3").write_bytes(b"x")

        store = PlaylistStore(root)
        entry = store.add(URL)
        assert entry["id"] == "playlist:abc123" and entry["url"] == URL.split("?")[0]
        assert store.add(URL) is entry  # no duplicates

        dl = FakeDownloader()
        r = sync_playlist(entry, dl, downloads)
        store.save()
        assert entry["folder"] == "130 fweak"
        assert dl.downloaded == ["id1", "id3"]  # the mp3 was adopted, not downloaded
        assert [f.name for f in r.files] == [
            "Artist 1 - Title 1.m4a", "Artist 2 - Title 2.mp3", "Artist 3 - Title 3.m4a"]
        assert r.new == []  # first sync: nothing is "new"

        # Spotify: track 2 removed, track 4 added
        dl.songs = [song(1), song(3), song(4)]
        dl.downloaded = []
        store = PlaylistStore(root)  # reload from disk
        entry = store.find("130 fweak")
        r = sync_playlist(entry, dl, downloads)
        assert dl.downloaded == ["id4"]  # known tracks aren't looked up again
        assert [p.name for p in r.new] == ["Artist 4 - Title 4.m4a"]
        assert [t["id"] for t in r.removed] == ["id2"]
        assert (downloads / "130 fweak" / "Artist 2 - Title 2.mp3").exists()  # kept
        assert [t["id"] for t in entry["tracks"]] == ["id1", "id3", "id4", "id2"]

        # removed again on the next sync: not reported twice
        r = sync_playlist(entry, dl, downloads)
        assert r.removed == [] and r.new == []

        m3u = root / "Stems" / "130 fweak" / "130 fweak.m3u8"
        stem = root / "Stems" / "130 fweak" / "Mr. X - Song.stem.mp4"
        write_m3u(m3u, [stem])
        assert m3u.read_text(encoding="utf-8").splitlines() == [
            "#EXTM3U", "#EXTINF:-1,Mr. X - Song", "Mr. X - Song.stem.mp4"]

        assert store.remove("playlist:abc123") is None  # by link only, not raw id
        assert store.remove(URL) is entry and store.playlists == []


if __name__ == "__main__":
    test_sync()
    print("ok")

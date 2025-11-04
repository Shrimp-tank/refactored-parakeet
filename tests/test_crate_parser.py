import struct
from pathlib import Path

from serato_rekordbox_sync.crate_parser import (
    SeratoCuePoint,
    SeratoTrack,
    iter_crates,
    load_crate,
)


def _serato_string(value: str) -> bytes:
    data = value.encode("utf-8")
    return struct.pack(">I", len(data)) + data


def _chunk(chunk_type: str, payload: bytes) -> bytes:
    return chunk_type.encode("ascii") + struct.pack(">I", len(payload)) + payload


def _build_crate(tracks: list[tuple]):
    parts: list[bytes] = []
    for track in tracks:
        name, path, *rest = track
        payload = _chunk("pnam", _serato_string(name)) + _chunk("pfil", _serato_string(str(path)))
        if rest:
            payload += _chunk("pcue", _encode_cues(rest[0]))
        parts.append(_chunk("OTRK", payload))
    return b"".join(parts)


def _write_crate(tmp_path: Path, name, tracks: list[tuple]) -> Path:
    if isinstance(name, Path):
        crate_path = tmp_path / name
    else:
        crate_path = tmp_path / name
    if crate_path.suffix != ".crate":
        crate_path = crate_path.with_suffix(".crate")
    crate_path.parent.mkdir(parents=True, exist_ok=True)
    crate_path.write_bytes(_build_crate(tracks))
    return crate_path


def _encode_cues(cues: list[float]) -> bytes:
    payload = struct.pack(">I", len(cues))
    for index, position in enumerate(cues):
        payload += struct.pack(">I", index)
        payload += struct.pack(">f", float(position))
    return payload


def test_load_crate_reads_tracks(tmp_path):
    music_dir = tmp_path / "music"
    track_a = music_dir / "track_a.mp3"
    track_b = music_dir / "track_b.mp3"

    crate_path = _write_crate(
        tmp_path,
        "Example",
        [
            ("Track A", track_a),
            ("Track B", track_b),
        ],
    )

    tracks = load_crate(crate_path)
    assert [t.title for t in tracks] == ["Track A", "Track B"]
    assert [t.path for t in tracks] == [track_a, track_b]
    assert all(isinstance(t, SeratoTrack) for t in tracks)


def test_iter_crates_returns_sorted_names(tmp_path):
    _write_crate(tmp_path, "Zulu", [])
    _write_crate(tmp_path, "Alpha", [])

    crates = list(iter_crates(tmp_path))
    assert [name for name, _ in crates] == [("Alpha",), ("Zulu",)]


def test_iter_crates_includes_subfolders(tmp_path):
    nested = Path("Main/Sub")
    _write_crate(tmp_path, Path("Main"), [])
    _write_crate(tmp_path, nested / "Deep", [])

    crates = list(iter_crates(tmp_path))
    assert ("Main",) in [name for name, _ in crates]
    assert ("Main", "Sub", "Deep") in [name for name, _ in crates]


def test_load_crate_reads_cues(tmp_path):
    track = tmp_path / "track.mp3"
    crate = _write_crate(tmp_path, "CueTest", [("Track", track, [1.25, 5.5])])

    tracks = load_crate(crate)
    assert len(tracks[0].cue_points) == 2
    assert isinstance(tracks[0].cue_points[0], SeratoCuePoint)
    assert tracks[0].cue_points[0].position == 1.25

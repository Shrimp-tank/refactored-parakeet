"""Utilities for parsing Serato crate files.

The Serato crate format is a simple chunk-based binary format. Each chunk
starts with a four-character type followed by a 32-bit big-endian length and
the payload. Most chunks we care about are nested under an ``OTRK`` chunk which
represents a single track reference.

The parser here focuses on extracting the file path (`pfil`) and optional track
name (`pnam`). It gracefully skips over unknown chunks so that it can continue
to function even if Serato introduces new metadata fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

import logging
import struct

logger = logging.getLogger(__name__)


@dataclass
class SeratoCuePoint:
    """A single cue point extracted from Serato metadata."""

    index: int
    position: float
    name: Optional[str] = None


@dataclass
class SeratoTrack:
    """A minimal representation of a track entry in a crate."""

    path: Path
    title: Optional[str] = None
    cue_points: List[SeratoCuePoint] = field(default_factory=list)


Chunk = Tuple[str, bytes]


def _read_chunks(data: bytes) -> Iterator[Chunk]:
    """Yield chunks from a binary blob.

    Each chunk begins with a four-byte ASCII identifier and a four-byte
    big-endian unsigned integer that gives the payload length.
    """

    offset = 0
    data_len = len(data)
    while offset + 8 <= data_len:
        chunk_type = data[offset : offset + 4].decode("ascii", errors="ignore")
        length = struct.unpack(">I", data[offset + 4 : offset + 8])[0]
        payload_start = offset + 8
        payload_end = payload_start + length
        if payload_end > data_len:
            logger.warning(
                "Chunk %s extends beyond end of buffer (len=%s, offset=%s)",
                chunk_type,
                length,
                offset,
            )
            break
        payload = data[payload_start:payload_end]
        yield chunk_type, payload
        offset = payload_end


def _decode_serato_string(payload: bytes) -> str:
    """Decode a string stored in a Serato payload.

    Strings are stored as a 32-bit length followed by that many bytes of UTF-8
    data. Some files include a trailing null byte which is stripped.
    """

    if not payload:
        return ""
    if len(payload) < 4:
        return payload.decode("utf-8", errors="ignore").rstrip("\x00")
    strlen = struct.unpack(">I", payload[:4])[0]
    text = payload[4 : 4 + strlen]
    return text.decode("utf-8", errors="ignore").rstrip("\x00")


def _parse_track_chunk(payload: bytes) -> Optional[SeratoTrack]:
    track: Dict[str, str] = {}
    cue_points: List[SeratoCuePoint] = []
    for chunk_type, chunk_payload in _read_chunks(payload):
        if chunk_type in {"pnam", "pfil"}:
            track[chunk_type] = _decode_serato_string(chunk_payload)
        elif chunk_type == "pcue":
            cue_points = _parse_cue_points(chunk_payload)
    path = track.get("pfil")
    if not path:
        return None
    return SeratoTrack(path=Path(path), title=track.get("pnam"), cue_points=cue_points)


def _parse_cue_points(payload: bytes) -> List[SeratoCuePoint]:
    """Decode cue point metadata from a ``pcue`` chunk."""

    if len(payload) < 4:
        return []
    count = struct.unpack(">I", payload[:4])[0]
    cue_points: List[SeratoCuePoint] = []
    offset = 4
    for _ in range(count):
        if offset + 8 > len(payload):
            break
        index = struct.unpack(">I", payload[offset : offset + 4])[0]
        position_raw = struct.unpack(">f", payload[offset + 4 : offset + 8])[0]
        cue_points.append(SeratoCuePoint(index=index, position=float(position_raw)))
        offset += 8
    return cue_points


def load_crate(path: Path) -> List[SeratoTrack]:
    """Load a Serato crate file.

    Parameters
    ----------
    path:
        Path to a ``.crate`` file.
    """

    with path.open("rb") as fh:
        raw = fh.read()

    tracks: List[SeratoTrack] = []
    for chunk_type, payload in _read_chunks(raw):
        if chunk_type == "OTRK":
            track = _parse_track_chunk(payload)
            if track:
                tracks.append(track)
    return tracks


def iter_crates(crate_root: Path) -> Iterable[Tuple[Tuple[str, ...], Path]]:
    """Iterate over crate files inside ``crate_root``.

    Yields tuples of ``(crate_name, file_path)`` where ``crate_name`` is derived
    from the filename without the ``.crate`` suffix.
    """

    for crate_path in sorted(crate_root.glob("**/*.crate")):
        relative = crate_path.relative_to(crate_root)
        parts = list(relative.parts)
        if not parts:
            continue
        parts[-1] = Path(parts[-1]).stem
        yield tuple(parts), crate_path

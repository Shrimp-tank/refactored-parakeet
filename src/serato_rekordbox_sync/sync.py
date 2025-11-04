"""High level conversion orchestration."""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Set, Tuple

from .crate_parser import iter_crates, load_crate
from .rekordbox_xml import Playlist, RekordboxXMLBuilder


logger = logging.getLogger(__name__)


@dataclass
class Converter:
    crate_root: Path
    output: Path
    product_name: str = "serato-rekordbox-sync"
    version: str = "0.2.0"

    def convert_once(self, *, write: bool = True) -> "ConversionSummary":
        """Convert the current crate tree into Rekordbox XML.

        Parameters
        ----------
        write:
            When ``True`` (default) the resulting XML document is written to
            ``self.output``.  Passing ``False`` performs a dry-run and only
            returns the calculated summary without touching the filesystem.

        Returns
        -------
        ConversionSummary
            Counts describing the playlists and tracks that were processed.
        """

        playlists, folder_paths = self._load_playlists()
        builder = RekordboxXMLBuilder(self.product_name, self.version)
        tree = builder.build(playlists, folder_paths)
        if write:
            RekordboxXMLBuilder.serialize(tree, self.output)
        return self._summarize(playlists)

    def watch(
        self,
        interval: int = 30,
        *,
        stop_event: "threading.Event | None" = None,
        on_summary: "callable[[ConversionSummary], None] | None" = None,
    ) -> None:
        last_snapshot: Dict[Path, float] | None = None
        while True:
            snapshot = self._snapshot()
            if snapshot != last_snapshot:
                summary = self.convert_once()
                logger.info("Wrote %s", summary.output)
                log_summary(summary)
                if on_summary:
                    on_summary(summary)
            last_snapshot = snapshot
            if stop_event is not None:
                if stop_event.wait(interval):
                    break
            else:
                time.sleep(interval)

    def _snapshot(self) -> Dict[Path, float]:
        return {path: path.stat().st_mtime for _, path in iter_crates(self.crate_root)}

    def _load_playlists(self) -> Tuple[Dict[Tuple[str, ...], Playlist], Set[Tuple[str, ...]]]:
        playlists: Dict[Tuple[str, ...], Playlist] = {}
        folder_paths: Set[Tuple[str, ...]] = set()
        tracks_by_path: Dict[Tuple[str, ...], list] = {}

        for crate_path, crate_file in iter_crates(self.crate_root):
            tracks = load_crate(crate_file)
            tracks_by_path[crate_path] = tracks
            for depth in range(1, len(crate_path)):
                folder_paths.add(crate_path[:depth])

        crate_paths = list(tracks_by_path.keys())

        for crate_path, tracks in tracks_by_path.items():
            has_children = any(
                other != crate_path
                and len(other) > len(crate_path)
                and other[: len(crate_path)] == crate_path
                for other in crate_paths
            )
            if has_children:
                folder_paths.add(crate_path)
            if not tracks and has_children:
                # Represent this crate purely as a folder so Rekordbox mirrors the Serato hierarchy.
                continue
            parent_path: Tuple[str, ...]
            if has_children and tracks:
                parent_path = crate_path
            else:
                parent_path = crate_path[:-1]
            playlists[crate_path] = Playlist(name=crate_path[-1], tracks=tracks, parent_path=parent_path)

        return playlists, folder_paths

    def _summarize(self, playlists: Dict[Tuple[str, ...], Playlist]) -> "ConversionSummary":
        playlist_counts = {
            " / ".join(path): len(playlist.tracks) for path, playlist in playlists.items()
        }
        total_tracks = sum(playlist_counts.values())
        return ConversionSummary(output=self.output, playlist_counts=playlist_counts, track_count=total_tracks)


@dataclass
class ConversionSummary:
    """Metadata describing the most recent conversion."""

    output: Path
    playlist_counts: Dict[str, int]
    track_count: int

    @property
    def playlist_count(self) -> int:
        return len(self.playlist_counts)


def log_summary(summary: ConversionSummary) -> None:
    """Log a short textual summary for human-readable output."""

    for line in summary_lines(summary):
        logger.info(line)


def summary_lines(summary: ConversionSummary) -> Iterable[str]:
    """Return formatted lines describing a conversion summary."""

    yield f"Playlists exported: {summary.playlist_count}"
    yield f"Total tracks: {summary.track_count}"
    if summary.playlist_counts:
        yield "Breakdown:"
        for name, count in summary.playlist_counts.items():
            yield f"  • {name} ({count} tracks)"

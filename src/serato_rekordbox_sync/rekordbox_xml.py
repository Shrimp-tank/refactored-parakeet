"""Helpers for constructing Rekordbox XML documents."""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple
from xml.etree import ElementTree as ET

from .crate_parser import SeratoCuePoint, SeratoTrack


@dataclass
class Playlist:
    name: str
    tracks: List[SeratoTrack]
    parent_path: Tuple[str, ...]


class RekordboxXMLBuilder:
    """Build a Rekordbox-compatible XML document from playlists."""

    def __init__(self, product_name: str = "serato-rekordbox-sync", version: str = "0.2.0") -> None:
        self.product_name = product_name
        self.version = version

    def build(
        self,
        playlists: Dict[Tuple[str, ...], Playlist],
        folder_paths: Iterable[Tuple[str, ...]] = (),
    ) -> ET.ElementTree:
        root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
        ET.SubElement(
            root,
            "PRODUCT",
            Name=self.product_name,
            Version=self.version,
            Company="OpenAI",
        )
        all_tracks = self._collect_unique_tracks(playlists)
        collection = ET.SubElement(root, "COLLECTION", Entries=str(len(all_tracks)))
        for track_id, track in all_tracks.items():
            attrs = {
                "TrackID": str(track_id),
                "Name": track.title or track.path.stem,
                "Location": self._to_file_url(track.path),
            }
            track_elem = ET.SubElement(collection, "TRACK", attrs)
            self._append_cues(track_elem, track.cue_points)

        playlists_node = ET.SubElement(root, "PLAYLISTS")
        root_node = ET.SubElement(playlists_node, "NODE", Type="0", Name="ROOT")
        folder_nodes: Dict[Tuple[str, ...], ET.Element] = {}
        normalized_folders: Set[Tuple[str, ...]] = {tuple(path) for path in folder_paths}

        for playlist in playlists.values():
            for depth in range(1, len(playlist.parent_path) + 1):
                normalized_folders.add(playlist.parent_path[:depth])

        def ensure_folder(path: Tuple[str, ...]) -> ET.Element:
            if not path:
                return root_node
            if path in folder_nodes:
                return folder_nodes[path]
            parent = ensure_folder(path[:-1])
            folder_node = ET.SubElement(parent, "NODE", Type="0", Name=path[-1])
            folder_nodes[path] = folder_node
            return folder_node

        for folder_path in sorted(normalized_folders):
            ensure_folder(folder_path)

        for path, playlist in sorted(playlists.items()):
            parent = ensure_folder(playlist.parent_path)
            playlist_node = ET.SubElement(parent, "NODE", Type="1", Name=playlist.name, Count=str(len(playlist.tracks)))
            for track in playlist.tracks:
                track_id = self._track_id_for_path(all_tracks, track.path)
                if track_id is not None:
                    ET.SubElement(playlist_node, "TRACK", Key=str(track_id))
        return ET.ElementTree(root)

    @staticmethod
    def _to_file_url(path: Path) -> str:
        # Rekordbox expects URLs such as file://localhost/Users/... where the path is encoded.
        absolute = path.expanduser().resolve()
        quoted = urllib.parse.quote(str(absolute).replace("\\", "/"))
        if not quoted.startswith("/"):
            quoted = f"/{quoted}"
        return f"file://localhost{quoted}"

    @staticmethod
    def _collect_unique_tracks(playlists: Dict[Tuple[str, ...], Playlist]) -> Dict[int, SeratoTrack]:
        unique: Dict[Path, int] = {}
        result: Dict[int, SeratoTrack] = {}
        next_id = 1
        for playlist in playlists.values():
            for track in playlist.tracks:
                key = track.path.resolve()
                if key not in unique:
                    unique[key] = next_id
                    result[next_id] = track
                    next_id += 1
        return result

    @staticmethod
    def _track_id_for_path(all_tracks: Dict[int, SeratoTrack], path: Path) -> int | None:
        target = path.resolve()
        for track_id, track in all_tracks.items():
            if track.path.resolve() == target:
                return track_id
        return None

    @staticmethod
    def _append_cues(track_elem: ET.Element, cues: List[SeratoCuePoint]) -> None:
        for cue in sorted(cues, key=lambda c: (c.index, c.position)):
            attrs = {
                "Name": cue.name or f"Hot Cue {cue.index + 1}",
                "Type": "0",
                "Start": f"{cue.position:.6f}",
                "Num": str(cue.index),
                "Red": "255",
                "Green": "255",
                "Blue": "255",
            }
            ET.SubElement(track_elem, "POSITION_MARK", attrs)

    @staticmethod
    def serialize(tree: ET.ElementTree, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        tree.write(output, encoding="utf-8", xml_declaration=True)

import xml.etree.ElementTree as ET
from pathlib import Path

from serato_rekordbox_sync.sync import ConversionSummary, Converter

from .test_crate_parser import _write_crate


def _make_tracks(tmp_path: Path, names: list[str]) -> list[tuple[str, Path]]:
    return [(name, tmp_path / f"{name}.mp3") for name in names]


def test_convert_once_writes_xml(tmp_path):
    crate_root = tmp_path / "crates"
    crate_root.mkdir()

    _write_crate(crate_root, "Evening", _make_tracks(tmp_path, ["Song One", "Song Two"]))
    _write_crate(crate_root, "WarmUp", _make_tracks(tmp_path, ["Intro"]))

    output = tmp_path / "rekordbox.xml"

    converter = Converter(crate_root=crate_root, output=output)
    summary = converter.convert_once()

    assert isinstance(summary, ConversionSummary)
    assert summary.playlist_count == 2
    assert summary.track_count == 3
    assert summary.playlist_counts["Evening"] == 2
    assert summary.playlist_counts["WarmUp"] == 1
    assert output.exists()

    tree = ET.parse(output)
    root = tree.getroot()
    playlist_nodes = root.findall(".//NODE[@Type='1']")
    assert {node.attrib["Name"] for node in playlist_nodes} == {"Evening", "WarmUp"}

    track_nodes = root.findall(".//COLLECTION/TRACK")
    assert len(track_nodes) == 3
    locations = {node.attrib["Location"] for node in track_nodes}
    assert all(location.startswith("file://localhost") for location in locations)


def test_convert_once_dry_run(tmp_path):
    crate_root = tmp_path / "crates"
    crate_root.mkdir()
    _write_crate(crate_root, "Test", _make_tracks(tmp_path, ["Song"]))

    output = tmp_path / "rekordbox.xml"
    converter = Converter(crate_root=crate_root, output=output)

    summary = converter.convert_once(write=False)

    assert summary.track_count == 1
    assert not output.exists()


def test_nested_crates_create_folders(tmp_path):
    crate_root = tmp_path / "crates"
    crate_root.mkdir()

    _write_crate(crate_root, Path("Main"), _make_tracks(tmp_path, ["Song"]))
    _write_crate(crate_root, Path("Main/Sub/Peak"), _make_tracks(tmp_path, ["Hit"]))

    output = tmp_path / "rekordbox.xml"
    converter = Converter(crate_root=crate_root, output=output)
    converter.convert_once()

    tree = ET.parse(output)
    root = tree.getroot()
    folder = next(
        node for node in root.findall(".//NODE") if node.attrib.get("Type") == "0" and node.attrib.get("Name") == "Main"
    )
    main_playlist = next(
        node for node in folder.findall("NODE")
        if node.attrib.get("Type") == "1" and node.attrib.get("Name") == "Main"
    )
    assert main_playlist.attrib.get("Count") == "1"
    subfolder = next(
        node for node in folder.findall("NODE")
        if node.attrib.get("Type") == "0" and node.attrib.get("Name") == "Sub"
    )
    playlist = next(
        node for node in subfolder.findall("NODE")
        if node.attrib.get("Type") == "1" and node.attrib.get("Name") == "Peak"
    )
    assert playlist.attrib.get("Count") == "1"


def test_parent_folder_without_tracks_becomes_folder_only(tmp_path):
    crate_root = tmp_path / "crates"
    crate_root.mkdir()

    # Only the nested crate has tracks; the parent folder should not generate an empty playlist.
    _write_crate(crate_root, Path("Folder/Child"), _make_tracks(tmp_path, ["Song"]))

    output = tmp_path / "rekordbox.xml"
    converter = Converter(crate_root=crate_root, output=output)
    converter.convert_once()

    tree = ET.parse(output)
    root = tree.getroot()
    folder = next(
        node for node in root.findall(".//NODE") if node.attrib.get("Type") == "0" and node.attrib.get("Name") == "Folder"
    )
    playlists = [node for node in folder.findall("NODE") if node.attrib.get("Type") == "1"]
    assert [node.attrib["Name"] for node in playlists] == ["Child"]


def test_cue_points_written_to_xml(tmp_path):
    crate_root = tmp_path / "crates"
    crate_root.mkdir()

    track_path = tmp_path / "song.mp3"
    _write_crate(crate_root, "Cue", [("Song", track_path, [0.5, 2.25])])

    output = tmp_path / "rekordbox.xml"
    converter = Converter(crate_root=crate_root, output=output)
    converter.convert_once()

    tree = ET.parse(output)
    track_node = tree.find(".//COLLECTION/TRACK")
    cues = track_node.findall("POSITION_MARK")
    assert len(cues) == 2
    assert {cue.attrib["Start"] for cue in cues} == {"0.500000", "2.250000"}

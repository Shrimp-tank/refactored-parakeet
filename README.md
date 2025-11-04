# Serato ↔︎ Rekordbox Sync

A lightweight desktop helper that mirrors your Serato crate structure inside Rekordbox without ever touching the command line. It reads the `.crate` files that Serato stores under `_Serato_` and produces a Rekordbox-compatible XML file that keeps playlists, folders, and cue points aligned.

## What you get

- ✅ A macOS app you can double-click – no Terminal knowledge required.
- ✅ Rekordbox folders that mirror the way Serato crates and subcrates nest.
- ✅ Playlists containing every track referenced in the crates, including cue points.
- ✅ An optional background watcher that keeps the XML export up to date while Serato is open.

The tool never edits or moves your audio files. It simply reads Serato's metadata and writes Rekordbox XML.

## Quick start (macOS, no command line)

1. **Build the app once:** In Finder, open the repository folder and double-click `packaging/Build Mac App.command`. A short Terminal window will appear while the bundle is assembled. When it finishes you will see `Serato Rekordbox Sync.app` inside the new `dist` folder.
2. **Install:** Drag `dist/Serato Rekordbox Sync.app` into your Applications folder (or keep it anywhere you like).
3. **Run:** Double-click `Serato Rekordbox Sync.app`. macOS may warn that the app was downloaded from the internet – choose *Open* to continue.

The bundle uses the system Python that ships with recent versions of macOS and includes everything else it needs. If you rebuild the project in the future, just double-click the `.command` file again to refresh the app.

### Where is the “repository folder”?

The folder you need to open in step&nbsp;1 above depends on how you grabbed the project:

- **Downloaded from GitHub (ZIP):** The folder lives wherever your browser saved downloads (usually `Downloads`). Look for a file named `serato-rekordbox-sync-main.zip`, double-click it, and macOS will create a folder with the same name. That folder is the repository.
- **GitHub Desktop:** Open GitHub Desktop, right-click the project, and choose **Show in Finder**. The Finder window that appears is the repository folder.
- **Other Git tools:** If you cloned the repository with another Git app, use that tool’s “open in Finder” option. The folder that contains `README.md`, `packaging`, and `src` is the right place.

Once you have that folder open in Finder, you can double-click `packaging/Build Mac App.command` to build the macOS app.

### Putting the project on GitHub (no Terminal required)

If you would like to keep the code in your own GitHub account, there are two simple options that avoid the command line entirely.

#### Option A: Publish directly from Codex

When Codex is connected to your GitHub account, the editor shows a **Create PR** button after you commit changes. Clicking it opens a guided flow:

1. **Commit your changes:** Use the built-in source control panel or the "Commit" button inside Codex. Give the commit a short description (for example, `Initial project import`).
2. **Press "Create PR":** The button appears near the top of the interface. Choose the GitHub repository you want to publish to, or create a new repository when prompted.
3. **Fill in the PR details:** Codex asks for a title and summary. It uploads the commit(s) to GitHub for you and opens a pull request automatically.
4. **Merge on GitHub:** Follow the link Codex provides to review and merge the pull request in your browser. After merging, the code is stored in your GitHub repository.

This route is great when you are already working inside Codex and want to push changes without switching tools.

#### Option B: Use GitHub Desktop

Prefer a native app? GitHub Desktop can publish the folder in just a few clicks:

1. **Create an empty repository online:** Visit [github.com/new](https://github.com/new), sign in, name your repository (for example `serato-rekordbox-sync`), and leave the rest of the options at their defaults. Do **not** add a README or other files—GitHub Desktop will upload everything from your folder.
2. **Open GitHub Desktop:** Choose **File → Add Local Repository…**, click **Choose…**, and pick the same folder that contains this README.
3. When prompted that "This directory does not appear to be a Git repository," click **Create a repository**, confirm the name, and choose the GitHub account you want to use.
4. Click **Publish repository** in the top-right corner of GitHub Desktop. In the dialog that appears, select the repository you created in step&nbsp;1 (or create a new one on the fly) and press **Publish Repository**.
5. After the upload finishes, the code and future commits you make in GitHub Desktop will appear on your GitHub profile automatically.

## Using the desktop app

1. **Crate location:** The app automatically points to `~/Music/_Serato_/Subcrates`, which is the standard Serato location. Use **Change…** if your library lives elsewhere.
2. **Where to save the XML:** Pick any writable folder (for example the Desktop). Rekordbox will read the XML file directly from here.
3. **Convert once:** Click **Convert once** to scan all crates immediately and generate the XML.
4. **Stay in sync:** Use **Start watching** to leave the app running in the background; it will regenerate the XML automatically whenever Serato updates its crates.
5. **Dry runs:** Tick **Dry run** to see a textual summary without writing anything to disk.

Every run prints a clear summary inside the window so you can confirm playlist counts before importing the XML into Rekordbox.

## How crates map to Rekordbox folders and playlists

- Every Serato crate becomes a Rekordbox playlist with the same name. Cue points stored in the crate are transferred into the playlist entries.
- Crates that contain nested subcrates appear as Rekordbox folders. If the parent crate also contains tracks, the app creates a playlist with the same name inside that folder so nothing is lost.
- Empty parent crates (ones that only exist to group other crates) become folders only. This matches Rekordbox's behaviour where clicking a folder shows the combined contents of the playlists underneath it.

This mapping ensures that browsing folders in Rekordbox feels the same as navigating crates in Serato.

## Importing into Rekordbox

1. Open Rekordbox and switch to *Performance* mode.
2. Choose **File → Import → Rekordbox XML…** and pick the exported XML file.
3. The playlists appear in the *XML* panel. Drag any playlist or folder into your Rekordbox collection if you want a permanent copy.

Whenever you rebuild the XML (either manually or via the watcher) you can re-import the file and Rekordbox will update the playlists in place.

## Troubleshooting

- **The app cannot find Serato crates:** Confirm that `_Serato_` is located in your Music folder. If you store crates on an external drive, point the app at that folder instead.
- **Tracks appear greyed out in Rekordbox:** Rekordbox needs to see the files at the paths stored in the crates. If you moved the audio files, update the crates inside Serato first and then reconvert.
- **Gatekeeper blocked the app:** Because the bundle is generated locally it is unsigned. Right-click the app, choose *Open*, and macOS will allow it.

## Advanced (optional) command line usage

The desktop experience is the primary way to use the project. If you want to automate the workflow further, you can still install the Python package and access the original CLI tools:

```bash
pip install .
serato-rekordbox-sync convert --help
```

## Development notes

To run the automated tests or contribute changes:

```bash
pip install -r requirements-dev.txt
pytest
```

The tests include small generated crate fixtures so you can explore how the parser interprets Serato's binary format.


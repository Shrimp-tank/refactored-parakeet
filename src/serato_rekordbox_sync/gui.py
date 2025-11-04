"""Simple desktop UI for the Serato ↔︎ Rekordbox synchroniser."""
from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from .sync import Converter, summary_lines


DEFAULT_CRATE_ROOT = Path.home() / "Music" / "_Serato_" / "Subcrates"
DEFAULT_OUTPUT = Path.home() / "Music" / "_Serato_" / "rekordbox-export.xml"


class SyncApp:
    """Small Tkinter application that wraps the converter."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Serato ↔︎ Rekordbox Sync")
        self.root.geometry("720x520")

        self.crate_var = tk.StringVar(value=str(DEFAULT_CRATE_ROOT))
        self.output_var = tk.StringVar(value=str(DEFAULT_OUTPUT))
        self.dry_run_var = tk.BooleanVar(value=False)
        self.interval_var = tk.IntVar(value=30)

        self.watch_thread: threading.Thread | None = None
        self.stop_event: threading.Event | None = None

        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        form = tk.Frame(self.root, padx=16, pady=16)
        form.pack(fill=tk.X)

        tk.Label(form, text="Serato crate folder:").grid(row=0, column=0, sticky="w")
        crate_entry = tk.Entry(form, textvariable=self.crate_var, width=60)
        crate_entry.grid(row=0, column=1, sticky="we", padx=(8, 8))
        tk.Button(form, text="Browse…", command=self._pick_crate_root).grid(row=0, column=2)

        tk.Label(form, text="Rekordbox XML output:").grid(row=1, column=0, sticky="w", pady=(12, 0))
        output_entry = tk.Entry(form, textvariable=self.output_var, width=60)
        output_entry.grid(row=1, column=1, sticky="we", padx=(8, 8), pady=(12, 0))
        tk.Button(form, text="Browse…", command=self._pick_output).grid(row=1, column=2, pady=(12, 0))

        options = tk.Frame(self.root, padx=16)
        options.pack(fill=tk.X, pady=(8, 0))

        tk.Checkbutton(options, text="Dry run (do not write XML)", variable=self.dry_run_var).pack(anchor="w")

        interval_frame = tk.Frame(options)
        interval_frame.pack(anchor="w", pady=(8, 0))
        tk.Label(interval_frame, text="Watch interval (seconds):").pack(side=tk.LEFT)
        interval_entry = tk.Entry(interval_frame, textvariable=self.interval_var, width=6)
        interval_entry.pack(side=tk.LEFT, padx=(8, 0))

        buttons = tk.Frame(self.root, padx=16, pady=12)
        buttons.pack(fill=tk.X)

        self.convert_button = tk.Button(buttons, text="Convert once", command=self._convert_now)
        self.convert_button.pack(side=tk.LEFT)

        self.watch_button = tk.Button(buttons, text="Start watching", command=self._toggle_watch)
        self.watch_button.pack(side=tk.LEFT, padx=(12, 0))

        self.log = tk.Text(self.root, wrap="word", state="disabled", padx=16, pady=16)
        self.log.pack(fill=tk.BOTH, expand=True)

    def run(self) -> None:
        self._append_log("Ready. Set the folders above and click Convert once to begin.\n")
        self.root.mainloop()

    # UI helpers -----------------------------------------------------------------
    def _pick_crate_root(self) -> None:
        path = filedialog.askdirectory(initialdir=self.crate_var.get() or str(DEFAULT_CRATE_ROOT))
        if path:
            self.crate_var.set(path)

    def _pick_output(self) -> None:
        path = filedialog.asksaveasfilename(
            initialdir=str(Path(self.output_var.get()).expanduser().parent),
            defaultextension=".xml",
            filetypes=[("Rekordbox XML", "*.xml"), ("All files", "*.*")],
        )
        if path:
            self.output_var.set(path)

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert(tk.END, text)
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def _show_error(self, message: str) -> None:
        messagebox.showerror("Serato ↔︎ Rekordbox Sync", message)
        self._append_log(f"Error: {message}\n")

    # Conversion -----------------------------------------------------------------
    def _convert_now(self) -> None:
        self._append_log("Starting conversion…\n")
        thread = threading.Thread(target=self._run_conversion, args=(self.dry_run_var.get(),), daemon=True)
        thread.start()

    def _run_conversion(self, dry_run: bool) -> None:
        try:
            converter = self._build_converter()
        except ValueError as exc:  # Validation failure
            self.root.after(0, self._show_error, str(exc))
            return
        try:
            summary = converter.convert_once(write=not dry_run)
        except Exception as exc:  # pragma: no cover - surfaced to the user
            self.root.after(0, self._show_error, str(exc))
            return
        self.root.after(0, self._handle_summary, summary, dry_run)

    def _build_converter(self) -> Converter:
        crate_root = Path(self.crate_var.get()).expanduser()
        if not crate_root.exists():
            raise ValueError(f"Crate folder does not exist: {crate_root}")
        output = Path(self.output_var.get()).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        return Converter(crate_root=crate_root, output=output)

    def _handle_summary(self, summary, dry_run: bool = False) -> None:
        if dry_run:
            self._append_log("Dry run complete – XML was not written.\n")
        else:
            self._append_log(f"Finished writing {summary.output}\n")
        for line in summary_lines(summary):
            self._append_log(f"{line}\n")

    # Watch mode -----------------------------------------------------------------
    def _toggle_watch(self) -> None:
        if self.watch_thread and self.watch_thread.is_alive():
            self._stop_watch()
        else:
            self._start_watch()

    def _start_watch(self) -> None:
        try:
            converter = self._build_converter()
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self.stop_event = threading.Event()
        interval = max(5, self.interval_var.get())
        self._append_log(f"Watching for changes every {interval} seconds…\n")
        self.convert_button.configure(state=tk.DISABLED)
        self.watch_button.configure(text="Stop watching")

        def _watch() -> None:
            try:
                converter.watch(
                    interval=interval,
                    stop_event=self.stop_event,
                    on_summary=lambda summary: self.root.after(0, self._handle_summary, summary, False),
                )
            except Exception as exc:  # pragma: no cover - surfaced to the user
                self.root.after(0, self._show_error, str(exc))
            finally:
                self.root.after(0, self._watch_finished)

        self.watch_thread = threading.Thread(target=_watch, daemon=True)
        self.watch_thread.start()

    def _stop_watch(self) -> None:
        if self.stop_event:
            self.stop_event.set()

    def _watch_finished(self) -> None:
        self.watch_thread = None
        self.convert_button.configure(state=tk.NORMAL)
        self.watch_button.configure(text="Start watching")
        self._append_log("Stopped watching.\n")

    def _on_close(self) -> None:
        if self.stop_event:
            self.stop_event.set()
        self.root.destroy()


def main() -> None:
    app = SyncApp()
    app.run()


if __name__ == "__main__":  # pragma: no cover - manual launch
    main()

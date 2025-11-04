"""Command line interface for Serato ↔︎ Rekordbox conversion."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .sync import Converter, log_summary

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert Serato crate files to Rekordbox XML")
    parser.add_argument("command", choices=["convert", "watch"], help="Operation to perform")
    parser.add_argument(
        "--crate-root",
        type=Path,
        default=_default_crate_root(),
        help="Directory containing .crate files (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_default_output(),
        help="Destination Rekordbox XML file (default: %(default)s)",
    )
    parser.add_argument("--product-name", default="serato-rekordbox-sync", help="Product name to embed in XML")
    parser.add_argument("--version", default="0.1.0", help="Version string to embed in XML")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds for watch mode")
    parser.add_argument("--dry-run", action="store_true", help="Load crates and report summary without writing XML")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    converter = Converter(crate_root=args.crate_root, output=args.output, product_name=args.product_name, version=args.version)

    try:
        if args.command == "convert":
            logger.info("Converting crates from %s -> %s", args.crate_root, args.output)
            summary = converter.convert_once(write=not args.dry_run)
            if args.dry_run:
                logger.info("Dry run complete – XML was not written")
            else:
                logger.info("Finished writing %s", summary.output)
            log_summary(summary)
            return 0
        if args.command == "watch":
            logger.info("Watching %s for changes (interval %ss)", args.crate_root, args.interval)
            converter.watch(interval=args.interval)
            return 0
    except KeyboardInterrupt:
        logger.info("Stopped by user")
        return 0
    parser.error(f"Unknown command {args.command}")
    return 1


def _default_crate_root() -> Path:
    return Path.home() / "Music" / "_Serato_" / "Subcrates"


def _default_output() -> Path:
    return Path.home() / "Music" / "_Serato_" / "rekordbox-export.xml"


if __name__ == "__main__":
    raise SystemExit(main())

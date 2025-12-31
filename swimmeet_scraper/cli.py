from __future__ import annotations

import argparse
import importlib.util
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

yaml_spec = importlib.util.find_spec("yaml")
if yaml_spec is not None:
    import yaml  # type: ignore
else:  # pragma: no cover - optional dependency
    yaml = None

from .scraper import SwimMeetScraper, SwimMeetScraperError, build_compilation_url


DEFAULT_BASE_URL = "https://www.swimmeet.com"
DEFAULT_TIMEOUT = 10.0


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch swim meet results and write them to CSV.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for the swim meet data service.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Request timeout in seconds.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Fetch a single event.")
    _add_event_arguments(fetch_parser)
    fetch_parser.add_argument("--out", required=True, help="Output CSV path.")

    fetch_all_parser = subparsers.add_parser("fetch-all", help="Fetch events defined in a config file.")
    fetch_all_parser.add_argument("--config", required=True, help="Path to YAML or JSON config file.")
    fetch_all_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned downloads without fetching data.",
    )

    return parser


def _add_event_arguments(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument("--season", required=True, help="Season identifier (e.g. 2024-2025).")
    subparser.add_argument("--phase", required=True, help="Season phase (e.g. prelims, finals).")
    subparser.add_argument("--gender", required=True, help="Gender category (e.g. girls, boys).")
    subparser.add_argument("--division", required=True, help="Division identifier (e.g. d1).")
    subparser.add_argument("--event-slug", required=True, help="Event slug (e.g. 50-freestyle).")
    subparser.add_argument("--state", required=True, help="State abbreviation or name.")


def _load_config(path: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required to load YAML configs. Install with `pip install pyyaml`. ")
        loaded = yaml.safe_load(text)
    else:
        loaded = json.loads(text)

    defaults: Dict[str, Any] = {}
    if isinstance(loaded, dict):
        defaults = {key: value for key, value in loaded.items() if key in {"state", "folder"}}
        if "events" not in loaded:
            raise ValueError("Config mapping must include an 'events' list.")
        events = loaded.get("events", [])
    else:
        events = loaded

    if not isinstance(events, list):
        raise ValueError("Config must be a list of events or contain an 'events' list.")

    normalized: List[Dict[str, Any]] = []
    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"Config entry {idx} is not a mapping: {event!r}")
        normalized.append(event)
    return defaults, normalized


def _build_output_filename(
    *, season: str, phase: str, gender: str, division: str, event_slug: str
) -> str:
    sanitized = [part.replace(" ", "-") for part in (season, phase, gender, division, event_slug)]
    return f"{'-'.join(sanitized)}.csv"


def _resolve_event(event: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    resolved = {**defaults, **event}
    return resolved


def _build_output_path(event: Dict[str, Any]) -> Path:
    folder = Path(event.get("folder") or "_data")
    filename = _build_output_filename(
        season=event["season"],
        phase=event["phase"],
        gender=event["gender"],
        division=event["division"],
        event_slug=event["event_slug"],
    )
    return folder / filename


def handle_fetch(args: argparse.Namespace) -> int:
    scraper = SwimMeetScraper(base_url=args.base_url, timeout=args.timeout)
    try:
        scraper.scrape_to_csv(
            out_path=args.out,
            season=args.season,
            phase=args.phase,
            gender=args.gender,
            division=args.division,
            event_slug=args.event_slug,
            state=args.state,
            timeout=args.timeout,
        )
    except SwimMeetScraperError as exc:
        logging.error("Failed to fetch event: %s", exc)
        return 1
    return 0


def handle_fetch_all(args: argparse.Namespace) -> int:
    try:
        defaults, events = _load_config(Path(args.config))
    except Exception as exc:
        logging.error("Could not read config: %s", exc)
        return 1

    scraper = SwimMeetScraper(base_url=args.base_url, timeout=args.timeout)
    exit_code = 0
    for event in events:
        resolved = _resolve_event(event, defaults)
        missing = _missing_fields(resolved)
        if missing:
            logging.error("Skipping event with missing fields %s: %s", ", ".join(sorted(missing)), event)
            exit_code = 1
            continue

        out_path = _build_output_path(resolved)
        url = build_compilation_url(
            args.base_url,
            season=resolved["season"],
            phase=resolved["phase"],
            gender=resolved["gender"],
            division=resolved["division"],
            event_slug=resolved["event_slug"],
            state=resolved["state"],
        )

        if args.dry_run:
            logging.info("[dry-run] Would fetch %s -> %s", url, out_path)
            continue

        try:
            scraper.scrape_to_csv(
                out_path=str(out_path),
                season=resolved["season"],
                phase=resolved["phase"],
                gender=resolved["gender"],
                division=resolved["division"],
                event_slug=resolved["event_slug"],
                state=resolved["state"],
                timeout=args.timeout,
            )
        except SwimMeetScraperError as exc:
            logging.error("Failed to fetch %s: %s", event.get("event_slug"), exc)
            exit_code = 1
    return exit_code


def _missing_fields(event: Dict[str, Any]) -> Iterable[str]:
    required = {"season", "phase", "gender", "division", "event_slug", "state"}
    return {field for field in required if field not in event}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    if args.command == "fetch":
        return handle_fetch(args)
    if args.command == "fetch-all":
        return handle_fetch_all(args)

    parser.error("No command provided")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

from __future__ import annotations

import csv
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree


logger = logging.getLogger(__name__)


def build_compilation_url(
    base_url: str,
    season: str,
    phase: str,
    gender: str,
    division: str,
    event_slug: str,
    state: str,
    *,
    folder: str = "compilation",
) -> str:
    """Build a deterministic URL for fetching compiled event data."""

    safe_parts = [
        quote(part.strip("/"), safe="-")
        for part in (state, season, folder, phase)
    ]
    filename = quote(f"{gender}-{division}-{event_slug}".replace(" ", "-"), safe="-")
    return "/".join([base_url.rstrip("/")] + safe_parts + [filename + ".html"])


class SwimMeetScraperError(Exception):
    """Raised when scraping a swim meet event fails."""


@dataclass
class SwimMeetScraper:
    """Scrape swim meet event results from a JSON/CSV endpoint."""

    base_url: str = "https://www.swimmeet.com"
    timeout: float = 10.0

    def _build_url(
        self,
        season: str,
        phase: str,
        gender: str,
        division: str,
        event_slug: str,
        state: str,
    ) -> str:
        return build_compilation_url(
            self.base_url,
            season=season,
            phase=phase,
            gender=gender,
            division=division,
            event_slug=event_slug,
            state=state,
        )

    def _parse_payload(self, payload: bytes, content_type: str) -> List[Dict[str, Any]]:
        content_type = content_type.lower() if content_type else ""
        text = payload.decode("utf-8")

        if "xml" in content_type or "<xml" in text.lower():
            return self._parse_xml_content(text)

        if "json" in content_type or text.strip().startswith("{") or text.strip().startswith("["):
            try:
                parsed: Any = json.loads(text)
            except json.JSONDecodeError as exc:
                raise SwimMeetScraperError("Response was not valid JSON") from exc

            if isinstance(parsed, dict):
                if "results" in parsed and isinstance(parsed["results"], list):
                    return [self._ensure_row_dict(item) for item in parsed["results"]]
                return [self._ensure_row_dict(parsed)]
            if isinstance(parsed, list):
                return [self._ensure_row_dict(item) for item in parsed]
            raise SwimMeetScraperError("JSON payload was not a list or dict")

        # assume CSV
        reader = csv.DictReader(text.splitlines())
        if reader.fieldnames is None:
            raise SwimMeetScraperError("CSV payload missing headers")
        return [self._ensure_row_dict(row) for row in reader]

    def _parse_xml_content(self, text: str) -> List[Dict[str, Any]]:
        match = re.search(r"<xml[^>]*>(.*?)</xml>", text, re.IGNORECASE | re.DOTALL)
        if not match:
            raise SwimMeetScraperError("XML block not found in response")

        try:
            root = ElementTree.fromstring(match.group(0))
        except ElementTree.ParseError as exc:
            raise SwimMeetScraperError("Response contained invalid XML") from exc

        rows: List[Dict[str, Any]] = []
        for results in root.findall(".//results"):
            for result in results.findall("result"):
                row = {key: result.attrib.get(key, "") for key in ("rk", "nm", "gr", "sc", "ti", "mt", "auto")}
                rows.append(row)

        if not rows:
            raise SwimMeetScraperError("XML payload did not include any results")

        return rows

    def _ensure_row_dict(self, row: Any) -> Dict[str, Any]:
        if not isinstance(row, dict):
            raise SwimMeetScraperError("Result row must be a mapping")
        return {str(key): value for key, value in row.items()}

    def fetch_event(
        self,
        season: str,
        phase: str,
        gender: str,
        division: str,
        event_slug: str,
        state: str,
        timeout: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        url = self._build_url(season, phase, gender, division, event_slug, state)
        logger.info("Fetching %s", url)

        request = Request(url, headers={"Accept": "application/json, text/csv;q=0.9, */*;q=0.8"})
        try:
            with urlopen(request, timeout=timeout or self.timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                payload = response.read()
        except HTTPError as exc:
            logger.error("HTTP error while fetching %s: %s", url, exc)
            raise SwimMeetScraperError(f"HTTP error while fetching {url}: {exc}") from exc
        except URLError as exc:
            logger.error("Network error while fetching %s: %s", url, exc)
            raise SwimMeetScraperError(f"Network error while fetching {url}: {exc}") from exc
        except Exception as exc:  # pragma: no cover - safety net
            logger.exception("Unexpected error while fetching %s", url)
            raise SwimMeetScraperError(f"Unexpected error while fetching {url}: {exc}") from exc

        try:
            return self._parse_payload(payload, content_type)
        except SwimMeetScraperError:
            raise
        except Exception as exc:  # pragma: no cover - safety net
            logger.exception("Failed to parse response from %s", url)
            raise SwimMeetScraperError(f"Failed to parse response from {url}: {exc}") from exc

    def scrape_to_csv(
        self,
        out_path: str,
        season: str,
        phase: str,
        gender: str,
        division: str,
        event_slug: str,
        state: str,
        timeout: Optional[float] = None,
    ) -> str:
        rows = self.fetch_event(season, phase, gender, division, event_slug, state, timeout=timeout)

        if not rows:
            logger.warning("No rows returned for %s/%s/%s/%s/%s", state, season, phase, gender, event_slug)

        fieldnames = self._collect_fieldnames(rows)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

        with open(out_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, "") for key in fieldnames})

        logger.info("Wrote %d rows to %s", len(rows), out_path)
        return out_path

    def _collect_fieldnames(self, rows: Iterable[Dict[str, Any]]) -> List[str]:
        fieldnames: List[str] = []
        for row in rows:
            for key in row.keys():
                if key not in fieldnames:
                    fieldnames.append(key)
        return fieldnames

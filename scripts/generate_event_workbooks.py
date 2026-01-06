from __future__ import annotations

import argparse
import io
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Mapping, Sequence, Tuple

import pandas as pd
import requests

REPO_OWNER = "bergsfam"
REPO_NAME = "swim_times"
DATA_FOLDER = "_data"
CONTENT_API = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"
FILENAME_PATTERN = re.compile(
    r"(?P<season>\d{4}-\d{4})-(?P<phase>[^-]+)-(?P<gender>[^-]+)-(?P<division>d[12])-(?P<event>.+)\.csv"
)


@dataclass(frozen=True)
class EventKey:
    gender: str
    division: str
    event: str

    def filename_stem(self) -> str:
        return f"{self.gender}-{self.division}-{self.event}"


@dataclass
class EventSource:
    key: EventKey
    files: List[Tuple[str, str]]  # list of (season, download_url)


class GithubDataClient:
    def __init__(self, owner: str, repo: str, folder: str) -> None:
        self.owner = owner
        self.repo = repo
        self.folder = folder
        self.session = requests.Session()

    def list_csv_files(self) -> Iterable[Mapping[str, str]]:
        url = CONTENT_API.format(owner=self.owner, repo=self.repo, path=self.folder)
        response = self.session.get(url)
        response.raise_for_status()
        for item in response.json():
            if item.get("type") == "file" and item.get("name", "").endswith(".csv"):
                yield item

    def fetch_csv(self, download_url: str) -> pd.DataFrame:
        response = self.session.get(download_url)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text), usecols=["rk", "ti", "mt", "auto"])


def group_files_by_event(files: Iterable[Mapping[str, str]]) -> Sequence[EventSource]:
    grouped: defaultdict[EventKey, List[Tuple[str, str]]] = defaultdict(list)
    for file_info in files:
        match = FILENAME_PATTERN.match(file_info["name"])
        if not match:
            continue
        season = match.group("season")
        key = EventKey(
            gender=match.group("gender"),
            division=match.group("division"),
            event=match.group("event"),
        )
        grouped[key].append((season, file_info["download_url"]))
    return [EventSource(key, sorted(files, key=lambda pair: pair[0])) for key, files in grouped.items()]


def merge_event(event: EventSource, client: GithubDataClient) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for season, download_url in event.files:
        df = client.fetch_csv(download_url)
        df = df.rename(
            columns={
                "ti": f"{season}_ti",
                "mt": f"{season}_mt",
                "auto": f"{season}_auto",
            }
        )
        frames.append(df)

    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="rk", how="outer")

    ti_columns = [column for column in merged.columns if column.endswith("_ti")]
    merged["avg_ti"] = merged[ti_columns].mean(axis=1)
    return merged


def write_workbook(event: EventSource, dataframe: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{event.key.filename_stem()}.xlsx"
    dataframe.to_excel(output_path, index=False)
    return output_path


def build_workbooks(output_dir: Path) -> list[Path]:
    client = GithubDataClient(REPO_OWNER, REPO_NAME, DATA_FOLDER)
    csv_files = list(client.list_csv_files())
    events = group_files_by_event(csv_files)

    created_paths: list[Path] = []
    for event in events:
        dataframe = merge_event(event, client)
        path = write_workbook(event, dataframe, output_dir)
        created_paths.append(path)
    return created_paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Excel workbooks for swim events")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("excel_outputs"),
        help="Directory where Excel workbooks will be written",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    created_paths = build_workbooks(args.output_dir)
    for path in created_paths:
        print(f"Created {path}")


if __name__ == "__main__":
    main()

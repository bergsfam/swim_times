from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from math import nan
from pathlib import Path
from typing import Iterable, List, Mapping, Sequence, Tuple

import pandas as pd

DATA_FOLDER = "_data"
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
    files: List[Tuple[str, str]]  # list of (season, csv_path)


class LocalDataClient:
    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def list_csv_files(self) -> Iterable[Mapping[str, str]]:
        for path in sorted(self.folder.glob("*.csv")):
            yield {"name": path.name, "path": str(path)}

    def fetch_csv(self, csv_path: str) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        return df.reindex(columns=["rk", "ti", "mt", "auto"])


def group_files_by_event(
    files: Iterable[Mapping[str, str]], phase: str | None
) -> Sequence[EventSource]:
    grouped: defaultdict[EventKey, List[Tuple[str, str]]] = defaultdict(list)
    for file_info in files:
        match = FILENAME_PATTERN.match(file_info["name"])
        if not match:
            continue
        if phase and match.group("phase") != phase:
            continue
        season = match.group("season")
        key = EventKey(
            gender=match.group("gender"),
            division=match.group("division"),
            event=match.group("event"),
        )
        grouped[key].append((season, file_info["path"]))
    return [EventSource(key, sorted(files, key=lambda pair: pair[0])) for key, files in grouped.items()]


def merge_event(event: EventSource, client: LocalDataClient, max_rank: int) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    season_order = [season for season, _ in event.files]
    for season, csv_path in event.files:
        df = client.fetch_csv(csv_path)
        df["rk"] = pd.to_numeric(df["rk"], errors="coerce")
        df = _dedupe_ranks(df)
        df[f"{season}_rank"] = df["rk"]
        df = df.rename(
            columns={
                "ti": f"{season}_time",
                "mt": f"{season}_district",
                "auto": f"{season}_AQ",
            }
        )
        frames.append(df)

    merged = frames[0]
    for frame in frames[1:]:
        merged = merged.merge(frame, on="rk", how="outer")

    time_columns = [column for column in merged.columns if column.endswith("_time")]
    for column in time_columns:
        merged[column] = merged[column].map(parse_time_value)
    merged["avg_time"] = merged[time_columns].mean(axis=1)
    for column in time_columns + ["avg_time"]:
        merged[column] = merged[column].map(format_time_value)
    merged = merged[merged["rk"] <= max_rank]
    merged["rank"] = merged["rk"]
    merged = merged.drop(columns=["rk"])

    ordered_columns: list[str] = []
    header_pairs: list[tuple[str, str]] = []
    non_empty = merged.notna().any()
    if "rank" in merged.columns:
        ordered_columns.append("rank")
        header_pairs.append(("", "rank"))

    for label, suffix in (
        ("district", "district"),
        ("AQ", "AQ"),
        ("time", "time"),
    ):
        for season in season_order:
            column_name = f"{season}_{suffix}"
            if column_name in merged.columns and bool(non_empty.get(column_name, False)):
                ordered_columns.append(column_name)
                header_pairs.append((season, label))

    if "avg_time" in merged.columns:
        ordered_columns.append("avg_time")
        header_pairs.append(("Average", "time"))

    merged = merged[ordered_columns]
    merged.columns = [label for _, label in header_pairs]
    merged.attrs["header_pairs"] = header_pairs
    return merged


def _dedupe_ranks(df: pd.DataFrame) -> pd.DataFrame:
    if "rk" not in df.columns:
        return df
    non_null = df["rk"].notna()
    if not non_null.any():
        return df
    duplicates = df.loc[non_null, "rk"].duplicated()
    if not duplicates.any():
        return df
    dup_ranks = df.loc[non_null, "rk"]
    df = df.copy()
    df.loc[non_null, "rk"] = dup_ranks + dup_ranks.groupby(dup_ranks).cumcount()
    return df


def parse_time_value(value: object) -> float:
    if pd.isna(value):
        return nan
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return nan
    if ":" in text:
        try:
            minutes_text, seconds_text = text.split(":", maxsplit=1)
            minutes = int(minutes_text)
            seconds = float(seconds_text)
            return minutes * 60 + seconds
        except ValueError:
            return nan
    try:
        return float(text)
    except ValueError:
        return nan


def format_time_value(value: object) -> str:
    if pd.isna(value):
        return ""
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return ""
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    if minutes:
        return f"{minutes}:{remainder:05.2f}"
    return round(remainder, 2)


def write_workbook(event: EventSource, dataframe: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{event.key.filename_stem()}.xlsx"
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Sheet1")
        worksheet = writer.sheets["Sheet1"]
        header_pairs: list[tuple[str, str]] = dataframe.attrs.get("header_pairs", [])
        if header_pairs:
            worksheet.insert_rows(1)
            for column_index, (season, _) in enumerate(header_pairs, start=1):
                worksheet.cell(row=1, column=column_index, value=season)
    return output_path


def build_workbooks(output_dir: Path, max_rank: int, phase: str | None) -> list[Path]:
    data_dir = Path(DATA_FOLDER)
    client = LocalDataClient(data_dir)
    csv_files = list(client.list_csv_files())
    events = group_files_by_event(csv_files, phase)

    created_paths: list[Path] = []
    for event in events:
        dataframe = merge_event(event, client, max_rank)
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
    parser.add_argument(
        "--max-rank",
        type=int,
        default=32,
        help="Maximum rk value to include",
    )
    parser.add_argument(
        "--phase",
        help="Restrict to a single phase (e.g. prelims, finals).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    created_paths = build_workbooks(args.output_dir, args.max_rank, args.phase)
    for path in created_paths:
        print(f"Created {path}")


if __name__ == "__main__":
    main()

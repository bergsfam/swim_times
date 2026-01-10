from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def load_sheet(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_excel(path)


def combine_workbooks(prelims_dir: Path, finals_dir: Path, output_dir: Path) -> list[Path]:
    prelims_files = {path.name: path for path in prelims_dir.glob("*.xlsx")}
    finals_files = {path.name: path for path in finals_dir.glob("*.xlsx")}

    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []

    for filename in sorted(set(prelims_files) | set(finals_files)):
        prelims_path = prelims_files.get(filename)
        finals_path = finals_files.get(filename)

        prelims_df = load_sheet(prelims_path) if prelims_path else pd.DataFrame()
        finals_df = load_sheet(finals_path) if finals_path else pd.DataFrame()

        output_path = output_dir / filename
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            finals_df.to_excel(writer, index=False, sheet_name="district_finals")
            prelims_df.to_excel(writer, index=False, sheet_name="state_prelims")
        created.append(output_path)

    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine district finals and state prelims workbooks into a single file per event."
    )
    parser.add_argument(
        "--prelims-dir",
        type=Path,
        default=Path("excel_outputs/state_prelims"),
        help="Directory containing state prelims workbooks.",
    )
    parser.add_argument(
        "--finals-dir",
        type=Path,
        default=Path("excel_outputs/district_finals"),
        help="Directory containing district finals workbooks.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("excel_outputs/combined"),
        help="Directory for combined workbooks.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    created = combine_workbooks(args.prelims_dir, args.finals_dir, args.output_dir)
    for path in created:
        print(f"Created {path}")


if __name__ == "__main__":
    main()

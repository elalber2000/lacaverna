#!/usr/bin/env python3

import csv
import json
from pathlib import Path

from utils import ROOT_PATH


def json_to_csv(input_path: str | Path, output_path: str | Path) -> None:
    input_file = Path(input_path)
    output_file = Path(output_path)

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    with input_file.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Expected the JSON root to be a list of objects.")

    rows = []

    for i, item in enumerate(data):
        rows.append(
            {
                "id": len(data)-i,
                "title": item["title"],
                "description": item["description"],
                "link": item["link"],
                "img_link": item["img_link"],
                # CSV has no native list type, so store these as JSON strings.
                "tags": json.dumps(item["tags"], ensure_ascii=False),
                "img_meta": item["img_meta"],

                # Fill later
                "date": "",       # date, expected YYYY-MM-DD
                "embedding": "",  # JSON string later, e.g. [0.1, 0.2]
            }
        )

    fieldnames = [
        "id",
        "title",
        "description",
        "link",
        "img_link",
        "tags",
        "img_meta",
        "date",
        "embedding",
    ]

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_file}")


if __name__ == "__main__":
    json_to_csv(
        ROOT_PATH / "old" / "posts.json",
        ROOT_PATH / "data" / "posts.csv",
    )
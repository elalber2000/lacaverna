"""Trace the small, flat-color book PNGs into clean SVG paths."""

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
BOOKS_DIR = ROOT / "assets" / "books"
PNG_DIR = BOOKS_DIR / "png"
PALETTE = np.array([0, 52, 103, 177])


def contour_paths(mask: np.ndarray, epsilon: float = 0.65, skip_largest: bool = False) -> list[str]:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if skip_largest and contours:
        largest = max(contours, key=cv2.contourArea)
        contours = [contour for contour in contours if contour is not largest]

    paths = []
    for contour in contours:
        if cv2.contourArea(contour) < 1:
            continue
        points = cv2.approxPolyDP(contour, epsilon, True)[:, 0, :]
        if len(points) < 3:
            continue
        paths.append("M " + " L ".join(f"{x:g} {y:g}" for x, y in points) + " Z")
    return paths


def vectorize(source: Path, destination: Path) -> None:
    image = cv2.imread(str(source), cv2.IMREAD_UNCHANGED)
    gray = image[:, :, 0]
    alpha = image[:, :, 3]
    height, width = gray.shape
    labels = np.argmin(
        np.abs(gray[:, :, None].astype(int) - PALETTE[None, None, :]), axis=2
    )
    labels[alpha == 0] = -1

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
    ]

    # One shared silhouette prevents seams between color layers.
    for path in contour_paths(alpha, epsilon=0.65):
        svg.append(
            f'<path fill="rgb(103,103,103)" stroke="rgb(0,0,0)" '
            f'stroke-width="0.65" stroke-linejoin="round" d="{path}"/>'
        )

    # Add only the interior light/dark regions; the silhouette owns the outside edge.
    for label, color in ((3, 177), (1, 52), (0, 0)):
        mask = np.where(labels == label, 255, 0).astype(np.uint8)
        for path in contour_paths(mask, epsilon=0.65, skip_largest=label == 0):
            svg.append(f'<path fill="rgb({color},{color},{color})" d="{path}"/>')

    svg.append("</svg>")
    destination.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main() -> None:
    sources = sorted(PNG_DIR.glob("book_*.png"), key=lambda path: int(path.stem.split("_")[-1]))
    for index, source in enumerate(sources, start=1):
        destination = BOOKS_DIR / f"book{index}.svg"
        vectorize(source, destination)
        print(f"{source.name} -> {destination.name}")

    svg_files = sorted(
        BOOKS_DIR.glob("book*.svg"),
        key=lambda path: int(path.stem.removeprefix("book")),
    )
    directory_index = ["<!doctype html>", "<html><body>"]
    directory_index.extend(f'<a href="{path.name}">{path.name}</a><br>' for path in svg_files)
    directory_index.extend(["</body></html>", ""])
    (BOOKS_DIR / "index.html").write_text("\n".join(directory_index), encoding="utf-8")


if __name__ == "__main__":
    main()

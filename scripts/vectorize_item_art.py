"""Convert the monochrome item PNGs into transparent, path-based SVGs."""

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
ITEMS_DIR = ROOT / "assets" / "items"
PNG_DIR = ITEMS_DIR / "png"
NAMES = ("about", "music", "travel", "quotes", "books", "codigo", "movies")
PRESERVE_BLACK_BOXES = {
    # The portrait's dark canvas is enclosed by its frame and is part of the art.
    "about": (66, 68, 304, 350),
}


def contours(mask: np.ndarray, epsilon: float = 0.35) -> list[str]:
    found, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    paths = []
    for contour in found:
        if cv2.contourArea(contour) < 1:
            continue
        points = cv2.approxPolyDP(contour, epsilon, True)[:, 0, :]
        if len(points) >= 3:
            paths.append("M " + " L ".join(f"{x:g} {y:g}" for x, y in points) + " Z")
    return paths


def vectorize(source: Path, destination: Path) -> None:
    image = cv2.imread(str(source), cv2.IMREAD_UNCHANGED)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape

    # The supplied art is grayscale on black. Remove only the near-black region
    # connected to the canvas edge so enclosed dark details remain artwork.
    black = np.where(gray <= 15, 1, 0).astype(np.uint8)
    _, components = cv2.connectedComponents(black, connectivity=8)
    border_labels = np.unique(
        np.concatenate((components[0, :], components[-1, :], components[:, 0], components[:, -1]))
    )
    background = np.isin(components, border_labels)
    alpha = np.where(background, 0, 255).astype(np.uint8)
    if source.stem in PRESERVE_BLACK_BOXES:
        x1, y1, x2, y2 = PRESERVE_BLACK_BOXES[source.stem]
        preserved_region = alpha[y1:y2, x1:x2]
        preserved_region[gray[y1:y2, x1:x2] <= 15] = 255
    quantized = (gray // 8) * 8
    quantized[gray <= 15] = 0

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
    ]

    # A narrow dark outline keeps the silhouette legible against the page.
    for path in contours(alpha):
        svg.append(
            f'<path d="{path}" fill="none" stroke="#111" stroke-width="1.5" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )

    black_mask = np.where((quantized == 0) & (alpha > 0), 255, 0).astype(np.uint8)
    for path in contours(black_mask):
        svg.append(f'<path d="{path}" fill="rgb(0,0,0)"/>')

    for shade in range(248, 15, -8):
        mask = np.where((quantized == shade) & (alpha > 0), 255, 0).astype(np.uint8)
        for path in contours(mask):
            svg.append(f'<path d="{path}" fill="rgb({shade},{shade},{shade})"/>')

    svg.append("</svg>")
    destination.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main() -> None:
    for name in NAMES:
        source = PNG_DIR / f"{name}.png"
        destination = ITEMS_DIR / f"{name}.svg"
        vectorize(source, destination)
        print(f"{source.name} -> {destination.name}")


if __name__ == "__main__":
    main()

# Book artwork

The original PNG book spines are stored in `png/` as `book_1.png` through
`book_n.png`. The browser uses the generated `book1.svg`, `book2.svg`, etc.
files from this directory.

The regeneration script also writes `index.html`. That generated directory
index lets the browser discover every SVG on static hosting without a separate
hand-written manifest.

To remove a black background from a new source PNG before tracing it:

```sh
convert input.png -alpha on -bordercolor black -border 1 -fuzz 10% \
  -fill none -draw 'matte 0,0 floodfill' -shave 1x1 output.png
```

Then rename the cleaned file to the next `book_N.png` number and regenerate the
SVGs after changing or adding a PNG:

```sh
python3 scripts/vectorize_book_art.py
```

The script uses OpenCV and NumPy to:

1. Quantize the antialiased grayscale artwork to its four intended colors.
2. Trace the alpha silhouette into a shared smooth path.
3. Trace the interior light and dark regions as additional SVG paths.
4. Write the results as `book1.svg` through `book_n.svg`.

The PNGs are deliberately not deleted; they remain the source files for future
traces in `assets/books/png/`.

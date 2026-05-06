import csv
import logging
import os
import random
import re
import unicodedata
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image

from utils import ROOT_PATH, configure_logging


configure_logging()

FIELDS = [
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

POSTS_PATH = Path(ROOT_PATH) / "data" / "posts.csv"
ARCHIVE_IMG_DIR = Path(ROOT_PATH) / "assets" / "archive"
IMG_LINK_PREFIX = "../assets/archive"

STOPWORDS = {
    "a", "un", "una", "unos", "unas", "el", "la", "los", "las", "lo", "y", "o", "u",
    "pero", "si", "luego", "entonces", "sino", "de", "del", "al", "en", "por", "para",
    "con", "sin", "sobre", "bajo", "entre", "hacia", "hasta", "como", "que", "quien",
    "quienes", "cual", "cuales", "cuando", "donde", "adonde", "cuanto", "cuantos",
    "porqué", "porque", "contra", "segun", "según", "durante", "mediante", "tras",
    "más", "menos", "muy", "poco", "mucho", "tan", "tampoco", "ya", "aún", "aun",
    "sea", "fue", "son", "sera", "será", "este", "esta", "estos", "estas", "esos",
    "esas", "mi", "mis", "tu", "tus", "su", "sus", "nuestro", "nuestra", "nuestros",
    "nuestras", "le",
}

STOPWORDS_RE = re.compile(
    r"\b(?:" + "|".join(map(re.escape, STOPWORDS)) + r")\b",
    re.IGNORECASE,
)

PALETTE = {
    "dark": np.array([23, 23, 23]),
    "blue": np.array([155, 98, 78]),
    "lightblue": np.array([184, 117, 94]),
    "white": np.array([237, 232, 229]),
}


def get_img_link(text):
    normalized = unicodedata.normalize("NFD", text)
    text = "".join(
        char for char in normalized
        if unicodedata.category(char) != "Mn"
    )

    text = STOPWORDS_RE.sub("", text)
    text = re.sub(r"[^\w ]+", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    text = text.strip("_").lower()

    if not text:
        text = "post"

    return f"{IMG_LINK_PREFIX}/{text}.png"


def img_link_to_path(img_link):
    if not img_link:
        return None

    clean = img_link.strip()

    if clean.startswith("../"):
        clean = clean[3:]

    return Path(ROOT_PATH) / clean


def load_posts(path):
    if not path.exists() or path.stat().st_size == 0:
        logging.warning("No existing posts CSV found: %s", path)
        return []

    logging.info("Loading posts from %s", path)

    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [
            {field: row.get(field, "") for field in FIELDS}
            for row in reader
        ]


def save_posts(path, posts):
    path.parent.mkdir(parents=True, exist_ok=True)

    logging.info("Saving %d posts to %s", len(posts), path)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(posts)


def used_met_object_ids(posts):
    ids = set()

    for post in posts:
        img_meta = post.get("img_meta", "")
        ids.update(re.findall(r"\[(\d+)\]", img_meta))

    return ids


def apply_gradient_map(gray, gradient, thresholds):
    norm = gray.astype(np.float32) / 255.0
    edges = np.quantile(norm, thresholds)

    palette = np.stack(
        [
            gradient["dark"],
            gradient["blue"],
            gradient["lightblue"],
            gradient["white"],
        ],
        axis=0,
    )

    bins = np.digitize(norm, edges)
    bins = np.clip(bins, 0, palette.shape[0] - 1)

    return palette[bins].astype(np.uint8)


def stylize_image_array(img_arr, thresholds=(0.25, 0.5, 0.75), blur_ksize=(5, 5)):
    gray = cv2.cvtColor(img_arr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, blur_ksize, 0)
    return apply_gradient_map(blurred, PALETTE, thresholds)


def search_image(query):
    logging.info("Searching Met image for query: %s", query)

    try:
        response = requests.get(
            "https://collectionapi.metmuseum.org/public/collection/v1/search",
            params={"q": query},
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        logging.warning("Met image search failed: %s", error)
        return None

    data = response.json()
    object_ids = data.get("objectIDs") or []

    if not object_ids:
        logging.warning("No Met result for query: %s", query)
        return None

    return object_ids[0]


def fetch_met_object(obj_id):
    url = f"https://collectionapi.metmuseum.org/public/collection/v1/objects/{obj_id}"

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except requests.RequestException:
        return None

    return response.json()


def fetch_random_met_image(
    min_val=400000,
    max_val=600000,
    randseed=None,
    used_ids=None,
    max_attempts=1000,
):
    used_ids = used_ids or set()

    for attempt in range(max_attempts):
        if randseed is not None and attempt == 0:
            obj_id = randseed
        else:
            obj_id = random.randint(min_val, max_val)

        if str(obj_id) in used_ids:
            continue

        logging.debug("Trying Met object ID: %s", obj_id)

        data = fetch_met_object(obj_id)

        if not data:
            continue

        object_id = str(data.get("objectID", ""))

        if object_id in used_ids:
            continue

        img_url = data.get("primaryImage")

        if not img_url:
            continue

        meta = {
            "id": data.get("objectID", ""),
            "title": data.get("title", ""),
            "artist": data.get("artistDisplayName", ""),
        }

        logging.info("Found Met object %s: %s", meta["id"], meta["title"])
        return img_url, meta

    raise RuntimeError(f"No valid Met image found after {max_attempts} attempts.")


def process_met_image(
    thresholds=(0.25, 0.5, 0.75),
    blur_ksize=(5, 5),
    randseed=None,
    used_ids=None,
):
    img_url, meta = fetch_random_met_image(
        randseed=randseed,
        used_ids=used_ids,
    )

    logging.info("Downloading image from: %s", img_url)

    response = requests.get(img_url, timeout=30)
    response.raise_for_status()

    img = Image.open(BytesIO(response.content)).convert("RGB")
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    stylized = stylize_image_array(img_cv, thresholds, blur_ksize)

    logging.info("Stylized image generated")
    return stylized, meta


def format_img_meta(meta):
    title = meta.get("title", "")
    object_id = meta.get("id", "")
    artist = meta.get("artist", "")

    if artist:
        return f"'{title}' [{object_id}], {artist}"

    return f"'{title}' [{object_id}]"


def get_doc_images():
    posts = load_posts(POSTS_PATH)

    if not posts:
        logging.warning("No posts to process")
        return

    ARCHIVE_IMG_DIR.mkdir(parents=True, exist_ok=True)

    used_ids = used_met_object_ids(posts)

    for post in posts:
        title = post.get("title", "").strip()

        if not title:
            logging.warning("Skipping post without title")
            continue

        if not post.get("img_link"):
            post["img_link"] = get_img_link(title)

        img_path = img_link_to_path(post["img_link"])

        if img_path and img_path.exists():
            logging.info("Skipping already processed image: %s", post["img_link"])
            continue

        logging.info("Processing: %s", title)

        seed = search_image(title)

        try:
            img, meta = process_met_image(
                randseed=seed,
                used_ids=used_ids,
            )
        except Exception as error:
            logging.warning("Could not process image for %s: %s", title, error)
            continue

        post["img_meta"] = format_img_meta(meta)

        if meta.get("id"):
            used_ids.add(str(meta["id"]))

        img_path.parent.mkdir(parents=True, exist_ok=True)

        ok = cv2.imwrite(str(img_path), img)

        if not ok:
            logging.warning("Could not write image: %s", img_path)
            continue

        logging.info("Wrote image: %s", img_path)

        save_posts(POSTS_PATH, posts)

    logging.info("Done")


if __name__ == "__main__":
    get_doc_images()
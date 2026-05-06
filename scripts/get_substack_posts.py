import csv
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

import feedparser
from bs4 import BeautifulSoup

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

SUBSTACKS = [
    "sancheznoseke",
    "parrotsbasilisks",
]

POSTS_PATH = Path(ROOT_PATH) / "data" / "posts.csv"


def substack_feed_url(source: str) -> str:
    source = source.strip()

    if source.startswith("http://") or source.startswith("https://"):
        parsed = urlparse(source)
        host = parsed.netloc.rstrip("/")
        return f"https://{host}/feed"

    return f"https://{source}.substack.com/feed"


def clean_description(entry, max_chars=-1):
    raw_summary = entry.get("summary", "") or entry.get("description", "")
    text = BeautifulSoup(raw_summary, "html.parser").get_text(" ", strip=True)

    if not text:
        return ""

    first_sentence = text.split(".")[0].strip()
    return first_sentence[:max_chars] if max_chars!=-1 else first_sentence


def fetch_substack_entries(source):
    feed_url = substack_feed_url(source)
    logging.info("Fetching feed: %s", feed_url)

    feed = feedparser.parse(feed_url)
    entries = []

    for entry in feed.entries:
        title = (entry.get("title") or "").strip()

        if not title or title == "Coming soon":
            continue

        link = (entry.get("link") or "").strip()

        if not link:
            continue

        if source == "parrotsbasilisks":
            tags = ["substack", "tecnologia", "ia"]
        else:
            tags = ["narrativa", "artículo", "substack"]

        entries.append(
            {
                "id": "",
                "title": title,
                "description": clean_description(entry),
                "link": link,
                "img_link": "",
                "tags": json.dumps(tags, ensure_ascii=False),
                "img_meta": "",
                "date": "",
                "embedding": "",
            }
        )

    logging.info("Fetched %d entries from %s", len(entries), feed_url)
    return entries


def load_existing_posts(path):
    if not path.exists() or path.stat().st_size == 0:
        logging.info("No existing posts CSV found; starting fresh")
        return []

    logging.info("Loading existing posts from %s", path)

    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = []

        for row in reader:
            normalized = {field: row.get(field, "") for field in FIELDS}
            rows.append(normalized)

        return rows


def next_id(existing):
    ids = []

    for item in existing:
        value = str(item.get("id", "")).strip()

        if value.isdigit():
            ids.append(int(value))

    return max(ids, default=0) + 1


def merge_catalog(existing, new_entries):
    seen_links = {item["link"] for item in existing if item.get("link")}
    seen_titles = {item["title"] for item in existing if item.get("title")}

    new_items = []
    current_id = next_id(existing)

    for item in new_entries:
        if item["link"] in seen_links or item["title"] in seen_titles:
            continue

        item["id"] = str(current_id)
        current_id += 1

        new_items.append(item)
        seen_links.add(item["link"])
        seen_titles.add(item["title"])

    logging.info(
        "Added %d new items; skipped %d duplicates",
        len(new_items),
        len(new_entries) - len(new_items),
    )

    return new_items + existing


def save_posts(path, posts):
    logging.info("Saving %d total entries to %s", len(posts), path)

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(posts)


def get_substack_posts():
    old_posts = load_existing_posts(POSTS_PATH)

    new_posts = []

    for source in SUBSTACKS:
        new_posts.extend(fetch_substack_entries(source))

    all_posts = merge_catalog(old_posts, new_posts)
    save_posts(POSTS_PATH, all_posts)

    logging.info("Done")


if __name__ == "__main__":
    get_substack_posts()
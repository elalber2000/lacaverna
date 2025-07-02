import logging
import feedparser
from bs4 import BeautifulSoup
import json
import re
import unicodedata
from pathlib import Path

from scripts.utils import ROOT_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

STOPWORDS = {
    'a', 'un','una','unos','unas','el','la','los','las','lo','y','o','u','pero','si',
    'luego','entonces','sino','de','del','al','en','por','para','con','sin',
    'sobre','bajo','entre','hacia','hasta','como','que','quien','quienes','cual',
    'cuales','cuando','donde','adonde','cuanto','cuantos','porqué','porque',
    'para','contra','segun','según','durante','mediante','tras','más','menos',
    'muy','poco','mucho','tan','tampoco','ya','aún','aun','sea','fue','son',
    'sera','será','este','esta','estos','estas','esos','esas','mi','mis','tu',
    'tus','su','sus','nuestro','nuestra','nuestros','nuestras', 'le'
}
STOPWORDS_RE = re.compile(
    r'\b(?:' + '|'.join(map(re.escape, STOPWORDS)) + r')\b',
    re.IGNORECASE
)

def get_img_link(text):
    logging.debug(f"Generating img_link for title: {text!r}")
    nkfd = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in nkfd if unicodedata.category(c) != 'Mn')
    text = STOPWORDS_RE.sub('', text)
    text = re.sub(r'[^\w ]+', '', text)
    text = re.sub(r'\s+', '_', text.strip())
    text = re.sub(r'[^\w ]+', '', text)
    text = re.sub(r'\s+', '_', text.strip())
    return f"../Images/Library/{text.lower()}.png"

def fetch_substack_entries(profile):
    feed_url = f"https://{profile}.substack.com/feed"
    logging.info(f"Fetching feed: {feed_url}")
    feed = feedparser.parse(feed_url)
    entries = []

    for entry in feed.entries:
        title = entry.title
        if title == "Coming soon":
            logging.debug("Skipping 'Coming soon' entry")
            continue
        link = entry.link
        description = BeautifulSoup(entry.summary, "html.parser") \
                        .get_text().strip().split(".")[0][:60]
        img_link = get_img_link(title)
        tags = ["narrativa", "artículo", "substack"]
        img_meta = ""

        entries.append({
            "title":        title,
            "description":  description,
            "link":         link,
            "img_link":     img_link,
            "tags":         tags,
            "img_meta":     img_meta
        })

    logging.info(f"Fetched {len(entries)} new entries")
    return entries

def merge_catalog(existing, new_entries, key):
    logging.info(f"Merging catalogs on key: {key}")
    seen = {item[key] for item in existing}
    added = 0
    for item in new_entries:
        if item[key] not in seen:
            existing.append(item)
            seen.add(item[key])
            added += 1
    logging.info(f"Added {added} new items (skipped {len(new_entries)-added} duplicates)")
    return existing

if __name__ == "__main__":
    posts_path = Path(ROOT_DIR) / "posts.json"
    logging.info(f"Loading existing posts from {posts_path}")
    if posts_path.exists() and posts_path.stat().st_size > 0:
        with open(posts_path, "r", encoding="utf-8") as f:
            old_posts = json.load(f)
    else:
        old_posts = []
        logging.info("No existing posts file or file empty; starting fresh")

    new_posts = fetch_substack_entries("sancheznoseke")
    all_posts = merge_catalog(old_posts, new_posts, "title")

    logging.info(f"Saving {len(all_posts)} total entries to {posts_path}")
    with open(posts_path, "w", encoding="utf-8") as f:
        json.dump(all_posts, f, indent=2, ensure_ascii=False)
    logging.info("Done")

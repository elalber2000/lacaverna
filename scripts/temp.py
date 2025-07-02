import json
import logging
from pathlib import Path

from scripts.utils import ROOT_DIR


posts_path = Path(ROOT_DIR) / "posts.json"
logging.info(f"Loading existing posts from {posts_path}")
if posts_path.exists() and posts_path.stat().st_size > 0:
    with open(posts_path, "r", encoding="utf-8") as f:
        posts = json.load(f)

for post in posts:
    if "img_meta" not in post:
        web_path = post["link"].replace("..", ROOT_DIR)
        #print(web_path)
        with open(web_path, "r", encoding="utf-8") as f:
            meta = [i for i in f.read().split("\n") if ' class="img-fluid">' in i][0].split("alt=")[1].split(" class=")[0].replace('"', "'").replace("''", "'")
        post["img_meta"] = meta
        print(json.dumps(post, indent=2, ensure_ascii=False)+",")

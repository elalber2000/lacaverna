import ast
import glob
import logging
import os

import markdown
import pandas as pd
import yaml

from utils import ROOT_PATH, configure_logging

configure_logging()

MD_PATH = f"{ROOT_PATH}/documents/md"
HTML_PATH = f"{ROOT_PATH}/documents"
CSV_PATH = f"{ROOT_PATH}/data/posts.csv"
TEMPLATE_PATH = f"{ROOT_PATH}/sections/doc_template.html"
LOMB_PATH = f"{ROOT_PATH}/assets/lombardics.yaml"


def parse_tags(tags):
    if not tags or pd.isna(tags):
        return []

    try:
        return ast.literal_eval(tags)
    except Exception:
        logging.warning(f"Could not parse tags: {tags}")
        return []


def render_tags(tags):
    parsed_tags = parse_tags(tags)

    if not parsed_tags:
        return ""

    links = [
        f'<a class="bracket-link" href="../sections/archive.html#{tag}">{tag}</a>'
        for tag in parsed_tags
    ]

    return f'<div class="article-tags" aria-label="Tags">\n{"".join(links)}\n</div>'


def image_name_from_path(img_link):
    """
    ../assets/archive/iglesia_villanueva.png -> iglesia_villanueva
    """
    return os.path.splitext(os.path.basename(str(img_link)))[0]


def load_posts_metadata():
    df = pd.read_csv(CSV_PATH).fillna("")
    return df.to_dict(orient="records")


def find_post_metadata(md_path, posts_data):
    """
    Matches documents/md/68.md with id=68.
    """
    filename = os.path.splitext(os.path.basename(md_path))[0]
    post_id = f"{filename}.html"

    matches = [
        post for post in posts_data
        if str(post["link"]) == post_id
    ]

    if not matches:
        logging.error(f"No CSV metadata entry found for {post_id}")
        return None

    return matches[0]


def md_to_html(md_text):
    return markdown.markdown(
        md_text,
        extensions=["extra", "sane_lists", "nl2br"],
    )


def fill_template(template, post, html_body):
    return (
        template
        .replace("{{title}}", str(post["title"]))
        .replace("{{tags}}", render_tags(post["tags"]))
        .replace("{{image}}", image_name_from_path(post["img_link"]))
        .replace("{{img_description}}", str(post["img_meta"]))
        .replace("{{text}}", html_body)
        .replace(
            '<title>Artículo de ejemplo — La Caverna</title>',
            f'<title>{post["title"]} — La Caverna</title>',
        )
        .replace(
            '<meta name="description" content="Artículo de ejemplo para La Caverna." />',
            f'<meta name="description" content="{post["description"]}" />',
        )
    )


def format_body(text: str):
    with open(LOMB_PATH) as f:
        lomb = yaml.safe_load(f)

    lines = text.splitlines()

    if lines and lines[0].startswith("#"):
        lines = lines[1:]

    text = "\n".join(lines).strip()

    ind, first_letter = next(((i, c) for i, c in enumerate(text) if c.isalpha()), (None, None))

    text = text[:ind] + lomb[text[ind].lower()] + text[ind+1:]

    return text


def generate_doc_html():
    os.makedirs(HTML_PATH, exist_ok=True)

    for filename in os.listdir(HTML_PATH):
        if filename.endswith(".html"):
            os.remove(os.path.join(HTML_PATH, filename))

    posts_data = load_posts_metadata()

    for md_path in glob.glob(os.path.join(MD_PATH, "*.md")):
        post = find_post_metadata(md_path, posts_data)
        if not post:
            continue

        with open(md_path, "r", encoding="utf-8") as f:
            html_body = md_to_html(format_body(f.read()))

        with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
            template = f.read()

        html = fill_template(template, post, html_body)

        output_name = f"{os.path.splitext(os.path.basename(md_path))[0]}.html"
        output_path = os.path.join(HTML_PATH, output_name)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        logging.info(f"Wrote: {output_path}")


if __name__ == "__main__":
    generate_doc_html()
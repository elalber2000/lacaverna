import ast
import base64
import logging
import re
from html import escape, unescape
from pathlib import Path

import markdown
import numpy as np
import pandas as pd
import yaml
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

from utils import ROOT_PATH, configure_logging

configure_logging()

ROOT = Path(ROOT_PATH)

MD_PATH = ROOT / "documents" / "md"
HTML_PATH = ROOT / "documents"
CSV_PATH = ROOT / "data" / "posts.csv"
TEMPLATE_PATH = ROOT / "sections" / "doc_template.html"
LOMB_PATH = ROOT / "assets" / "lombardics.yaml"

PostMetadata = dict[str, str]

LOMB_BR_SENTINEL = "\ue000LOMB_BR\ue000"
INDENT_SPACE_SENTINEL = "\ue000LC_INDENT_SPACE\ue000"
INDENT_TAB_SENTINEL = "\ue000LC_INDENT_TAB\ue000"
TAB_WIDTH = 4

HEADING_RE = re.compile(
    r"<(?P<open>h(?P<level>[1-6])\b[^>]*)>(?P<inner>.*?)</h(?P=level)>",
    flags=re.IGNORECASE | re.DOTALL,
)


def parse_tags(tags: object) -> list[str]:
    if tags is None:
        return []

    if not isinstance(tags, str) and pd.isna(tags):
        return []

    raw = str(tags).strip()
    if not raw:
        return []

    try:
        parsed = ast.literal_eval(raw)
    except Exception:
        logging.warning("Could not parse tags: %s", tags)
        return []

    if not isinstance(parsed, list):
        logging.warning("Tags are not a list: %s", tags)
        return []

    return [str(tag) for tag in parsed if tag]


def render_tags(tags: object) -> str:
    parsed_tags = parse_tags(tags)

    if not parsed_tags:
        return ""

    links = [
        f'<a class="bracket-link" href="../sections/archive.html#{escape(tag, quote=True)}">{escape(tag)}</a>'
        for tag in parsed_tags
    ]

    return f'<div class="article-tags" aria-label="Tags">\n{"".join(links)}\n</div>'


def image_name_from_path(img_link: object) -> str:
    """
    ../assets/archive/iglesia_villanueva.png -> iglesia_villanueva
    """
    return Path(str(img_link)).stem


def has_embedding(value: object) -> bool:
    if value is None:
        return False

    if not isinstance(value, str) and pd.isna(value):
        return False

    value = str(value).strip()
    return value not in {"", "[]", "null", "None"}


def unpack_embedding(value: str) -> np.ndarray:
    """
    Decode base64 float32 embedding back into a numpy array.
    Must match the pack_embedding() format from fill_embeddings.py.
    """
    return np.frombuffer(base64.b64decode(str(value)), dtype=np.float32)


def load_posts_metadata() -> pd.DataFrame:
    return pd.read_csv(
        CSV_PATH,
        dtype=str,
        keep_default_na=False,
    )


def load_lombardics() -> dict[str, str]:
    with LOMB_PATH.open("r", encoding="utf-8") as f:
        raw_lomb = yaml.safe_load(f) or {}

    # Use a sentinel first so Markdown does not escape literal HTML.
    return {
        str(key): str(value).replace("\n", LOMB_BR_SENTINEL)
        for key, value in raw_lomb.items()
    }


def find_post_metadata(md_path: Path, posts_df: pd.DataFrame) -> PostMetadata | None:
    """
    Matches md file to CSV row via generated HTML link.
    """
    post_id = f"../documents/{md_path.stem}.html"

    matches = posts_df.loc[posts_df["link"].eq(post_id)]

    if matches.empty:
        logging.error("No CSV metadata entry found for %s", post_id)
        return None

    return {str(key): str(value) for key, value in matches.iloc[0].items()}


def build_related_posts_map(
    posts_df: pd.DataFrame,
    top_k: int = 3,
) -> dict[str, list[PostMetadata]]:
    valid_indices: list[int] = []
    embeddings: list[np.ndarray] = []

    for idx, row in posts_df.iterrows():
        raw_embedding = row.get("embedding", "")

        if not has_embedding(raw_embedding):
            continue

        try:
            embedding = unpack_embedding(str(raw_embedding))

            if embedding.size == 0:
                logging.warning("Empty embedding for row index=%s id=%s", idx, row.get("id"))
                continue

            valid_indices.append(idx)
            embeddings.append(embedding)

        except Exception as exc:
            logging.warning(
                "Could not decode embedding for row index=%s id=%s: %s",
                idx,
                row.get("id"),
                exc,
            )

    if len(embeddings) < 2:
        logging.warning("Not enough valid embeddings to compute related posts.")
        return {}

    dims = [embedding.shape[0] for embedding in embeddings]
    target_dim = max(set(dims), key=dims.count)

    filtered_indices: list[int] = []
    filtered_embeddings: list[np.ndarray] = []

    for idx, embedding in zip(valid_indices, embeddings):
        if embedding.shape[0] != target_dim:
            logging.warning(
                "Skipping embedding with unexpected dim=%s for row index=%s. Expected dim=%s",
                embedding.shape[0],
                idx,
                target_dim,
            )
            continue

        filtered_indices.append(idx)
        filtered_embeddings.append(embedding)

    if len(filtered_embeddings) < 2:
        logging.warning("Not enough same-dimension embeddings to compute related posts.")
        return {}

    related_df = posts_df.loc[filtered_indices].reset_index(drop=True)

    matrix = np.vstack(filtered_embeddings).astype(np.float32)

    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    matrix = matrix / np.maximum(norms, 1e-12)

    similarity = matrix @ matrix.T
    np.fill_diagonal(similarity, -np.inf)

    related_by_link: dict[str, list[PostMetadata]] = {}

    for i, row in related_df.iterrows():
        current_link = str(row.get("link", "")).strip()
        if not current_link:
            continue

        nearest_indices = np.argsort(-similarity[i])[:top_k]

        related_posts: list[PostMetadata] = []

        for j in nearest_indices:
            if not np.isfinite(similarity[i, j]):
                continue

            related_row = related_df.iloc[j]
            related_posts.append(
                {str(key): str(value) for key, value in related_row.items()}
            )

        related_by_link[current_link] = related_posts

    return related_by_link


def render_related_posts(related_posts: list[PostMetadata]) -> str:
    if not related_posts:
        return ""

    titles = [str(post.get("title", "")).strip() for post in related_posts]
    title_width = max(28, *(len(title) for title in titles if title))

    rows: list[str] = []

    for post in related_posts:
        title = str(post.get("title", "")).strip()
        link = str(post.get("link", "")).strip()
        tags = parse_tags(post.get("tags", ""))

        padding = " " * max(1, title_width - len(title) + 2)

        if link:
            title_html = (
                f'<a class="hover-hi" href="{escape(link, quote=True)}">'
                f"{escape(title)}"
                f"</a>"
            )
        else:
            title_html = f'<span class="hover-hi">{escape(title)}</span>'

        tag_links = " ".join(
            f'<a class="bracket-link" href="../sections/archive.html#{escape(tag, quote=True)}">'
            f"{escape(tag)}"
            f"</a>"
            for tag in tags
        )

        rows.append(f"※ {title_html}{padding}{tag_links}".rstrip())

    related_text = "\n".join(rows)

    return f"""</br>
<div class="fleuron" aria-hidden="true">- · ─ * ─ · -</div>
<section class="related-docs" aria-label="Related articles">
<pre>
SEGUIR LEYENDO
────────────────
{related_text}</pre>
</section>"""


def inject_related_html(html: str, related_html: str) -> str:
    if "{{related}}" in html:
        return html.replace("{{related}}", related_html)

    if not related_html:
        return html

    if "</main>" in html:
        return html.replace("</main>", f"{related_html}\n</main>", 1)

    if "</body>" in html:
        return html.replace("</body>", f"{related_html}\n</body>", 1)

    return f"{html}\n{related_html}"


class LombardicParagraphTreeprocessor(Treeprocessor):
    """
    Applies lombardics only inside the first <p> emitted from Markdown.
    It never touches headings, lists, blockquotes, code blocks, etc.
    """

    def __init__(self, md, lomb: dict[str, str]):
        super().__init__(md)
        self.lomb = lomb

    def run(self, root):
        for elem in root.iter():
            if str(elem.tag).lower() != "p":
                continue

            self.replace_first_alpha_inside(elem)
            break

        return root

    def replace_first_alpha_inside(self, elem) -> bool:
        if elem.text:
            elem.text, changed = self.replace_first_alpha(elem.text)
            if changed:
                return True

        for child in list(elem):
            if self.replace_first_alpha_inside(child):
                return True

            if child.tail:
                child.tail, changed = self.replace_first_alpha(child.tail)
                if changed:
                    return True

        return False

    def replace_first_alpha(self, text: str) -> tuple[str, bool]:
        for i, char in enumerate(text):
            if char.isalpha():
                replacement = self.lomb.get(char.lower(), char)
                return text[:i] + replacement + text[i + 1 :], True

        return text, False


class LombardicParagraphExtension(Extension):
    def __init__(self, lomb: dict[str, str]):
        super().__init__()
        self.lomb = lomb

    def extendMarkdown(self, md):
        md.treeprocessors.register(
            LombardicParagraphTreeprocessor(md, self.lomb),
            "lombardic_paragraph_only",
            15,
        )


def strip_leading_md_title(text: str) -> str:
    """
    Remove the first Markdown heading because the template already renders the title.
    """
    lines = text.splitlines()

    if lines and lines[0].lstrip().startswith("#"):
        lines = lines[1:]

    return "\n".join(lines).strip()


def protect_leading_indentation(md_text: str) -> str:
    """
    Preserves leading spaces/tabs in poem-like text.

    HTML collapses leading whitespace. This replaces leading indentation with
    sentinels before Markdown rendering, then md_to_html() converts them to
    non-breaking spaces after rendering.

    Skips fenced code blocks.
    """
    lines = md_text.splitlines()
    protected_lines: list[str] = []

    in_fence = False

    for line in lines:
        stripped = line.lstrip(" \t")

        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            protected_lines.append(line)
            continue

        if in_fence or not stripped:
            protected_lines.append(line)
            continue

        indent_len = len(line) - len(stripped)

        if indent_len == 0:
            protected_lines.append(line)
            continue

        indent = line[:indent_len]

        protected_indent = (
            indent
            .replace(" ", INDENT_SPACE_SENTINEL)
            .replace("\t", INDENT_TAB_SENTINEL)
        )

        protected_lines.append(protected_indent + stripped)

    return "\n".join(protected_lines)


def md_to_html(md_text: str, lomb: dict[str, str]) -> str:
    md_text = strip_leading_md_title(md_text)
    md_text = protect_leading_indentation(md_text)

    html = markdown.markdown(
        md_text,
        extensions=[
            "extra",
            "sane_lists",
            "nl2br",
            LombardicParagraphExtension(lomb),
        ],
    )

    return (
        html
        .replace(LOMB_BR_SENTINEL, "</br>")
        .replace(INDENT_SPACE_SENTINEL, "&nbsp;")
        .replace(INDENT_TAB_SENTINEL, "&nbsp;" * TAB_WIDTH)
    )


def prefix_heading_markers(html: str) -> str:
    """
    Adds §.
    """

    def replace_heading(match: re.Match) -> str:
        open_tag = match.group("open")
        level = int(match.group("level"))
        inner = match.group("inner")

        if level == 1:
            return match.group(0)

        text_only = re.sub(r"<[^>]+>", "", inner)
        text_only = unescape(text_only).strip()

        if text_only.startswith("§"):
            return match.group(0)

        prefix = "§" * (level - 1)
        return f"<{open_tag}>{prefix} {inner}</h{level}>"

    return HEADING_RE.sub(replace_heading, html)


def fill_template(
    template: str,
    post: PostMetadata,
    html_body: str,
    related_html: str,
) -> str:
    html = (
        template
        .replace("{{title}}", escape(post["title"]))
        .replace("{{tags}}", render_tags(post["tags"]))
        .replace("{{image}}", image_name_from_path(post["img_link"]))
        .replace("{{img_description}}", escape(post["img_meta"], quote=True))
        .replace("{{text}}", html_body)
        .replace(
            "<title>Artículo de ejemplo — La Caverna</title>",
            f"<title>{escape(post['title'])} — La Caverna</title>",
        )
        .replace(
            '<meta name="description" content="Artículo de ejemplo para La Caverna." />',
            f'<meta name="description" content="{escape(post["description"], quote=True)}" />',
        )
    )

    html = inject_related_html(html, related_html)
    html = prefix_heading_markers(html)

    return html


def generate_docs() -> None:
    HTML_PATH.mkdir(parents=True, exist_ok=True)

    for html_path in HTML_PATH.glob("*.html"):
        html_path.unlink()

    posts_df = load_posts_metadata()
    related_by_link = build_related_posts_map(posts_df, top_k=3)
    lomb = load_lombardics()

    with TEMPLATE_PATH.open("r", encoding="utf-8") as f:
        template = f.read()

    for md_path in MD_PATH.glob("*.md"):
        post = find_post_metadata(md_path, posts_df)
        if not post:
            continue

        with md_path.open("r", encoding="utf-8") as f:
            html_body = md_to_html(f.read(), lomb)

        related_posts = related_by_link.get(post["link"], [])
        related_html = render_related_posts(related_posts)

        html = fill_template(template, post, html_body, related_html)

        output_path = HTML_PATH / f"{md_path.stem}.html"

        with output_path.open("w", encoding="utf-8") as f:
            f.write(html)

        logging.info("Wrote: %s", output_path)


if __name__ == "__main__":
    generate_docs()
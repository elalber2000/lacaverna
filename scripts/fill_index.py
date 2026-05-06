import ast
import logging
from pathlib import Path
from html import escape

import pandas as pd

from utils import ROOT_PATH, configure_logging

configure_logging()

ROOT = Path(ROOT_PATH)

CSV_PATH = ROOT / "data" / "posts.csv"
INDEX_PATH = ROOT / "index.html"

INDEX_COLUMN = "id"
POPULAR_IDS = [61, 37, 52, 59, 50, 49, 32, 51]

PLACEHOLDER_START = "<!-- PLACEHOLDER_START -->"
PLACEHOLDER_END = "<!-- PLACEHOLDER_END -->"

LEGACY_PLACEHOLDER_START = "<!-- PLACEHOLDER"
LEGACY_PLACEHOLDER_END = "PLACEHOLDER -->"


def load_posts() -> pd.DataFrame:
    return pd.read_csv(
        CSV_PATH,
        dtype=str,
        keep_default_na=False,
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

    return [str(tag).strip() for tag in parsed if str(tag).strip()]


def normalize_link(link: str) -> str:
    link = str(link).strip()

    if link.startswith("../"):
        return link[3:]

    return link


def render_tag_list(tags: object) -> str:
    parsed_tags = parse_tags(tags)

    if not parsed_tags:
        return ""

    items = "\n".join(
        f'              <li><a class="bracket-link" href="sections/archive.html#{escape(tag, quote=True)}">{escape(tag)}</a></li>'
        for tag in parsed_tags
    )

    return f"""            <ul class="tag-list" aria-label="Tags">
{items}
            </ul>"""


def render_article_link(row: pd.Series) -> str:
    title = escape(str(row["title"]).strip())
    link = escape(normalize_link(str(row["link"])), quote=True)
    tag_list = render_tag_list(row.get("tags", ""))

    return f"""          <div class="article-item">
            <a class="article-line" href="{link}">
              <span>{title}</span>
            </a>
{tag_list}
          </div>"""


def render_article_stack(rows: pd.DataFrame) -> str:
    return "\n".join(render_article_link(row) for _, row in rows.iterrows())


def add_numeric_index_column(posts_df: pd.DataFrame) -> pd.DataFrame:
    df = posts_df.copy()
    df["_index_num"] = pd.to_numeric(df[INDEX_COLUMN], errors="coerce")
    return df.dropna(subset=["_index_num"])


def get_newest_posts(posts_df: pd.DataFrame, count: int = 8) -> pd.DataFrame:
    df = add_numeric_index_column(posts_df)

    return (
        df.sort_values("_index_num", ascending=False)
        .head(count)
        .drop(columns=["_index_num"])
    )


def get_popular_posts(posts_df: pd.DataFrame) -> pd.DataFrame:
    df = add_numeric_index_column(posts_df)

    rows = []

    for popular_id in POPULAR_IDS:
        matches = df.loc[df["_index_num"].eq(float(popular_id))]

        if matches.empty:
            logging.warning("Popular post index not found in CSV: %s", popular_id)
            continue

        rows.append(matches.iloc[0].drop(labels=["_index_num"]))

    if not rows:
        return posts_df.iloc[0:0]

    return pd.DataFrame(rows)


def render_featured_section(newest_df: pd.DataFrame, popular_df: pd.DataFrame) -> str:
    newest_links = render_article_stack(newest_df)
    popular_links = render_article_stack(popular_df)

    return f"""    <section class="two-col" aria-label="Destacados">
      <article class="panel">
        <div class="panel-head">
          <h2>NUEVO</h2>
        </div>

        <div class="list-stack">
{newest_links}
        </div>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>POPULAR</h2>
        </div>

        <div class="list-stack">
{popular_links}
        </div>
      </article>
    </section>"""


def wrap_placeholder_content(content: str) -> str:
    return f"{PLACEHOLDER_START}\n{content}\n    {PLACEHOLDER_END}"


def replace_between_markers(html: str, replacement: str) -> str:
    start = html.find(PLACEHOLDER_START)
    end = html.find(PLACEHOLDER_END)

    if start != -1 and end != -1 and end > start:
        end += len(PLACEHOLDER_END)
        return html[:start] + wrap_placeholder_content(replacement) + html[end:]

    legacy_start = html.find(LEGACY_PLACEHOLDER_START)
    if legacy_start == -1:
        raise ValueError(
            f"Could not find placeholder marker: {PLACEHOLDER_START} "
            f"or legacy marker: {LEGACY_PLACEHOLDER_START}"
        )

    legacy_end = html.find(LEGACY_PLACEHOLDER_END, legacy_start)
    if legacy_end == -1:
        raise ValueError(f"Could not find legacy placeholder end: {LEGACY_PLACEHOLDER_END}")

    legacy_end += len(LEGACY_PLACEHOLDER_END)

    return html[:legacy_start] + wrap_placeholder_content(replacement) + html[legacy_end:]


def fill_index() -> None:
    posts_df = load_posts()

    newest_df = get_newest_posts(posts_df, count=8)
    popular_df = get_popular_posts(posts_df)

    with INDEX_PATH.open("r", encoding="utf-8") as f:
        html = f.read()

    featured_section = render_featured_section(newest_df, popular_df)
    html = replace_between_markers(html, featured_section)

    with INDEX_PATH.open("w", encoding="utf-8") as f:
        f.write(html)

    logging.info("Filled homepage placeholders: %s", INDEX_PATH)


if __name__ == "__main__":
    fill_index()
import os
import re
import logging
from pathlib import Path
from html import escape
from typing import Callable

import requests
import feedparser
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, field_validator

from utils import ROOT_PATH, configure_logging


configure_logging()

ROOT = Path(ROOT_PATH)

INFLUENCES_PATH = ROOT / "sections" / "influences.html"

PLACEHOLDER_START = "<!-- PLACEHOLDER_START -->"
PLACEHOLDER_END = "<!-- PLACEHOLDER_END -->"

LEGACY_PLACEHOLDER_START = "<!-- PLACEHOLDER"
LEGACY_PLACEHOLDER_END = "PLACEHOLDER -->"

DEFAULT_LIMIT = 5


class Item(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    url: str = "#"
    by: str = ""
    score: float | int | None = None

    @field_validator("title", "url", "by", mode="before")
    @classmethod
    def clean_string(cls, value: object) -> str:
        return str(value or "").strip()


FAVOURITE_BOOKS = [
    Item(
        title="100 Años de Soledad",
        url="https://www.goodreads.com/book/show/28162111",
        by="G.G. Márquez",
        score=5,
    ),
    Item(
        title="Ficciones",
        url="https://www.goodreads.com/book/show/2223330",
        by="Borges",
        score=5,
    ),
    Item(
        title="Sacred and Terrible Air",
        url="https://www.goodreads.com/book/show/154527611",
        by="R. Kurvitz",
        score=5,
    ),
    Item(
        title="Hombres de Armas",
        url="https://www.goodreads.com/book/show/61607",
        by="T. Pratchett",
        score=5,
    ),
    Item(
        title="La Saga-Fuga de JB",
        url="https://www.goodreads.com/book/show/61714",
        by="T. Ballester",
        score=5,
    ),
]

FAVOURITE_MOVIES = [
    Item(title="Spirited Away", url="https://letterboxd.com/film/spirited-away/"),
    Item(title="On the Silver Globe", url="https://letterboxd.com/film/on-the-silver-globe/"),
    Item(title="A Clockwork Orange", url="https://letterboxd.com/film/a-clockwork-orange/"),
    Item(title="The French Dispatch", url="https://letterboxd.com/film/the-french-dispatch/"),
    Item(title="Synecdoche, New York", url="https://letterboxd.com/film/synecdoche-new-york/"),
]

FAVOURITE_MUSIC = [
    Item(
        title="Surrender",
        url="https://open.spotify.com/track/2ccUQnjjNWT0rsNnsBpsCA",
        by="Cheap Trick",
    ),
    Item(
        title="Cada uno en su lugar",
        url="https://www.youtube.com/watch?v=V35LHkgeZpY",
        by="Crema",
    ),
    Item(
        title="Otra Noche en Miami",
        url="https://open.spotify.com/track/4vCAzANUWDE24URV6wQ4ra",
        by="Bad Bunny",
    ),
    Item(
        title="Fare Schifo",
        url="https://open.spotify.com/track/2MOm69sL4OoDnhCc1lhQBN",
        by="Willie Peyote",
    ),
    Item(
        title="No Estoy",
        url="https://open.spotify.com/track/1kP5YGbeWnYLVlWbuX6rLG",
        by="Kinder Malo",
    ),
]

FAVOURITE_QUOTES = [
    "«Sigue tu visión. Forma células Rebeldes clandestinas en todas partes. A la vez, no tengas miedo a la soledad». (W. Herzog)",
    "«De los 20 a los 30, estrella de rock;\nDe los 30 a los 40, estrella de cine;\nDe los 40 a los 50, director;\ny de los 50 en adelante, escritor». (C. Tangana)",
    "«La Escuela de Cine Rebelde no es para pusilánimes. Es para quienes han viajado a pie, quienes han trabajado como gorilas de clubes sexuales o como vigilantes de manicomio, para quienes estén dispuestos a aprender a forzar cerraduras o falsificar permisos de rodaje en países que no favorecen sus proyectos. En resumen: para quienes tienen sentido de la poesía. Para quienes son peregrinos. Para quienes pueden contar una historia a niños de cuatro años y mantener su atención. Para quienes tienen un fuego ardiendo adentro. Para quienes tienen un sueño». (Werner Herzog)",
    "«El arte es o revolución o plagio». (Gauguin)",
    "«[...] El arte debe su evolución continua a la dualidad apolíneo-dionisíaca [...], sus constantes conflictos y actos periódicos de reconciliación». (Nietzsche)",
]


def load_environment() -> None:
    load_dotenv(ROOT / ".env")


def get_spotify_token() -> str:
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["SPOTIFY_CLIENT_ID"],
            "client_secret": os.environ["SPOTIFY_CLIENT_SECRET"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )

    response.raise_for_status()
    return response.json()["access_token"]


def get_recent_music(limit: int = DEFAULT_LIMIT) -> list[Item]:
    token = get_spotify_token()
    playlist_id = os.environ["SPOTIFY_PLAYLIST_ID"]

    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {"Authorization": f"Bearer {token}"}

    total_response = requests.get(
        url,
        headers=headers,
        params={"fields": "total", "limit": 1},
        timeout=20,
    )
    total_response.raise_for_status()

    total = total_response.json()["total"]
    fetch_count = min(total, 100)
    offset = max(total - fetch_count, 0)

    response = requests.get(
        url,
        headers=headers,
        params={
            "limit": fetch_count,
            "offset": offset,
            "fields": "items(added_at,track(name,artists(name),external_urls.spotify))",
        },
        timeout=20,
    )
    response.raise_for_status()

    items = response.json()["items"]
    items.sort(key=lambda item: item["added_at"], reverse=True)

    return [
        Item(
            title=item["track"]["name"],
            url=item["track"]["external_urls"]["spotify"],
            by=", ".join(artist["name"] for artist in item["track"]["artists"]),
        )
        for item in items[:limit]
        if item.get("track")
    ]


def get_recent_movies(limit: int = DEFAULT_LIMIT) -> list[Item]:
    user = os.environ["LETTERBOXD_USER"]
    feed = feedparser.parse(f"https://letterboxd.com/{user}/rss/")

    movies = []

    for entry in feed.entries[:limit]:
        title = entry.title
        score = None

        if " - " in entry.title:
            title, raw_score = entry.title.rsplit(" - ", 1)
            score = raw_score.count("★") + 0.5 * raw_score.count("½")

        movies.append(
            Item(
                title=title,
                url=entry.link,
                score=score,
            )
        )

    return movies


def get_recent_books(limit: int = DEFAULT_LIMIT) -> list[Item]:
    user_id = os.environ["GOODREADS_USER_ID"]
    feed = feedparser.parse(f"https://www.goodreads.com/user/updates_rss/{user_id}")

    entries = sorted(
        feed.entries,
        key=lambda entry: entry.get("published_parsed") or (),
        reverse=True,
    )

    books = []
    seen_titles = set()

    for entry in entries:
        title_match = re.match(r"^.+? added (.+)$", entry.title)

        if not title_match:
            continue

        title = title_match.group(1).strip()

        if title in seen_titles:
            continue

        seen_titles.add(title)

        author_match = re.search(
            r'class="authorName"[^>]*>(.*?)</a>',
            entry.get("summary", ""),
        )

        score_match = re.search(
            r"gave\s+(\d+)\s+stars",
            entry.get("description", ""),
        )

        books.append(
            Item(
                title=title,
                url=entry.link,
                by=author_match.group(1).strip() if author_match else "",
                score=int(score_match.group(1)) if score_match else None,
            )
        )

        if len(books) >= limit:
            break

    return books


def fetch_or_empty(label: str, fetcher: Callable[[], list[Item]]) -> list[Item]:
    try:
        return fetcher()
    except Exception as error:
        logging.warning("Could not fetch %s: %s", label, error)
        return []


def render_stars(score: float | int | None) -> str:
    if score is None:
        return ""

    full_stars = int(score)
    half_star = "½" if float(score) - full_stars >= 0.5 else ""

    return f" {'★' * full_stars}{half_star}"


def render_item_text(item: Item, section: str) -> str:
    text = item.title

    if item.by:
        text += f" ({item.by})"

    if section in {"books", "movies"}:
        text += render_stars(item.score)

    return text


def render_item_link(item: Item, section: str) -> str:
    href = escape(item.url, quote=True)
    text = escape(render_item_text(item, section))
    target = "" if item.url == "#" else ' target="_blank" rel="noopener noreferrer"'

    return f'<a class="article-line" href="{href}"{target}>{text}</a>'


def render_item_stack(items: list[Item], section: str) -> str:
    if not items:
        return '            <span class="article-line">—</span>'

    return "\n".join(
        f"            {render_item_link(item, section)}"
        for item in items
    )


def render_quote_stack() -> str:
    return "\n".join(
        f'            <p class="article-line">{escape(quote).replace(chr(10), "<br>")}</p>'
        for quote in FAVOURITE_QUOTES
    )


def render_column(title: str, content: str) -> str:
    return f"""          <div>
            <h3>{title}</h3>
{content}
          </div>"""


def render_cluster(
    section: str,
    icon: str,
    title: str,
    newest_items: list[Item],
    favourite_items: list[Item],
) -> str:
    newest_column = render_column("Nuevo", render_item_stack(newest_items, section))
    favourites_column = render_column("Favoritos", render_item_stack(favourite_items, section))

    return f"""      <article class="panel influence-cluster">
        <h2><span class="mono-icon">{icon}</span> {title}</h2>
        <div class="mini-cols">
{newest_column}
{favourites_column}
        </div>
      </article>"""


def render_quotes_cluster() -> str:
    return f"""      <article class="panel influence-cluster">
        <h2><span class="mono-icon">❝</span> Quotes</h2>
        <div class="mini-cols">
{render_column("Favoritos", render_quote_stack())}
        </div>
      </article>"""


def render_influence_grid() -> str:
    recent_books = fetch_or_empty("books", get_recent_books)
    recent_movies = fetch_or_empty("movies", get_recent_movies)
    recent_music = fetch_or_empty("music", get_recent_music)

    return f"""    <section class="influence-grid">
{render_cluster("books", "🕮", "Books", recent_books, FAVOURITE_BOOKS)}

{render_cluster("movies", "🎞︎", "Movies", recent_movies, FAVOURITE_MOVIES)}

{render_cluster("music", "♪", "Music", recent_music, FAVOURITE_MUSIC)}

{render_quotes_cluster()}
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


def fill_influences_placeholder() -> None:
    load_environment()

    with INFLUENCES_PATH.open("r", encoding="utf-8") as f:
        html = f.read()

    influence_grid = render_influence_grid()
    html = replace_between_markers(html, influence_grid)

    with INFLUENCES_PATH.open("w", encoding="utf-8") as f:
        f.write(html)

    logging.info("Filled influences placeholder: %s", INFLUENCES_PATH)


if __name__ == "__main__":
    fill_influences_placeholder()
import os
import re
import html
import logging
from pathlib import Path
from dataclasses import dataclass

import requests
import feedparser
from dotenv import load_dotenv
from utils import ROOT_PATH, configure_logging


configure_logging()

START = "<!-- PLACEHOLDER_START -->"
END = "<!-- PLACEHOLDER_END -->"


@dataclass
class Item:
    title: str
    url: str = "#"
    by: str = ""
    score: float | int | None = None


FAVOURITE_BOOKS = [
    Item(
        "'100 Años de Soledad'",
        "https://www.goodreads.com/book/show/28162111",
        "G. G. Márquez",
        5,
    ),
    Item(
        "'Ficciones'",
        "https://www.goodreads.com/book/show/2223330",
        "Borges",
        5,
    ),
    Item(
        "'Sacred and Terrible Air'",
        "https://www.goodreads.com/book/show/154527611",
        "R. Kurvitz",
        5,
    ),
    Item(
        "'Hombres de Armas'",
        "https://www.goodreads.com/book/show/61607",
        "T. Pratchett",
        5,
    ),
    Item(
        "'La Saga-Fuga de JB'",
        "https://www.goodreads.com/book/show/61714",
        "T. Ballester",
        5,
    ),
]


FAVOURITE_MOVIES = [
    Item("Spirited Away", "https://letterboxd.com/film/spirited-away/", score=5),
    Item("On the Silver Globe", "https://letterboxd.com/film/on-the-silver-globe/", score=5),
    Item("A Clockwork Orange", "https://letterboxd.com/film/a-clockwork-orange/", score=5),
    Item("The French Dispatch", "https://letterboxd.com/film/the-french-dispatch/", score=5),
    Item("Synecdoche, New York", "https://letterboxd.com/film/synecdoche-new-york/", score=5),
]


FAVOURITE_MUSIC = [
    Item(
        "Surrender",
        "https://open.spotify.com/track/2ccUQnjjNWT0rsNnsBpsCA",
        "Cheap Trick",
    ),
    Item(
        "Cada uno en su lugar",
        "https://www.youtube.com/watch?v=V35LHkgeZpY",
        "Crema",
    ),
    Item(
        "Otra Noche en Miami",
        "https://open.spotify.com/track/4vCAzANUWDE24URV6wQ4ra",
        "Bad Bunny",
    ),
    Item(
        "Fare Schifo",
        "https://open.spotify.com/track/2MOm69sL4OoDnhCc1lhQBN",
        "Willie Peyote",
    ),
    Item(
        "No Estoy",
        "https://open.spotify.com/track/1kP5YGbeWnYLVlWbuX6rLG",
        "Kinder Malo",
    ),
]


FAVOURITE_QUOTES = [
    "«Sigue tu visión. Forma células Rebeldes clandestinas en todas partes. A la vez, no tengas miedo a la soledad». (W. Herzog)",
    "«De los 20 a los 30, estrella de rock;\nDe los 30 a los 40, estrella de cine;\nDe los 40 a los 50, director;\ny de los 50 en adelante, escritor». (C. Tangana)",
    "«La Escuela de Cine Rebelde no es para pusilánimes. Es para quienes han viajado a pie, quienes han trabajado como gorilas de clubes sexuales o como vigilantes de manicomio, para quienes estén dispuestos a aprender a forzar cerraduras o falsificar permisos de rodaje en países que no favorecen sus proyectos. En resumen: para quienes tienen sentido de la poesía. Para quienes son peregrinos. Para quienes pueden contar una historia a niños de cuatro años y mantener su atención. Para quienes tienen un fuego ardiendo adentro. Para quienes tienen un sueño». (Werner Herzog)",
    "«El arte es o revolución o plagio». (Gauguin)",
    "«[...] El arte debe su evolución continua a la dualidad apolíneo-dionisíaca [...], sus constantes conflictos y actos periódicos de reconciliación». (Nietzsche)",
]


def escape(value):
    return html.escape(str(value or ""), quote=True)


def stars(score):
    if score is None:
        return ""

    full_stars = int(score)
    has_half = float(score) % 1 == 0.5

    rating = "*" * full_stars

    if has_half:
        rating += "½"

    return rating


def spotify_token():
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


def recent_music(limit):
    token = spotify_token()
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
            by=", ".join(artist["name"] for artist in item["track"]["artists"]),
            url=item["track"]["external_urls"]["spotify"],
        )
        for item in items[:limit]
    ]


def recent_movies(limit):
    feed = feedparser.parse(f"https://letterboxd.com/{os.environ['LETTERBOXD_USER']}/rss/")

    movies = []

    for entry in feed.entries[:limit]:
        raw_title = entry.title

        if " - " in raw_title:
            title, rating = raw_title.rsplit(" - ", 1)
            score = rating.count("★") + 0.5 * rating.count("½")
        else:
            title = raw_title
            score = None

        movies.append(Item(title=title, url=entry.link, score=score))

    return movies


def recent_books(limit):
    feed = feedparser.parse(
        f"https://www.goodreads.com/user/updates_rss/{os.environ['GOODREADS_USER_ID']}"
    )

    books = []
    seen = set()

    for entry in feed.entries:
        match = re.match(r"^.+? added (.+)$", entry.title)
        if not match:
            continue

        title = match.group(1).strip()

        if title in seen:
            continue

        seen.add(title)

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
                by=html.unescape(author_match.group(1)) if author_match else "",
                url=entry.link,
                score=int(score_match.group(1)) if score_match else None,
            )
        )

        if len(books) >= limit:
            break

    return books


def safe_fetch(name, fetcher):
    try:
        return fetcher()
    except Exception as error:
        logging.warning("Could not fetch %s: %s", name, error)
        return []


def render_rating(item, section):
    if section not in {"books", "movies"}:
        return ""

    rating = stars(item.score)

    if not rating:
        return ""

    return f'<span class="influence-rating" aria-label="{escape(str(item.score))} stars">{escape(rating)}</span>'


def render_item_inner(item, section):
    by = f' <span class="influence-by">({escape(item.by)})</span>' if item.by else ""
    rating = render_rating(item, section)

    return f"""<span class="influence-item-main">
              <span class="influence-title">{escape(item.title)}</span>{by}
            </span></br>{rating}"""


def render_link(item, section):
    target = "" if item.url == "#" else ' target="_blank" rel="noopener noreferrer"'

    return (
        f'<a class="article-line influence-item" href="{escape(item.url)}"{target}>'
        f"{render_item_inner(item, section)}"
        f"</a>"
    )


def render_items(items, section):
    if not items:
        return '            <span class="article-line">—</span>'

    return "\n".join(
        f"            {render_link(item, section)}"
        for item in items
    )


def render_quotes():
    items = []

    for quote in FAVOURITE_QUOTES:
        quote_html = escape(quote).replace("\n", "<br>")
        items.append(f'          <p class="quote-line">{quote_html}</p>')

    return "\n".join(items)


def render_column(title, body):
    return f"""          <div>
            <h3>{title}</h3>
{body}
          </div>"""


def render_cluster(section, icon, title, recent, favourites):
    return f"""      <article class="panel influence-cluster">
        <h2><span class="mono-icon">{icon}</span> {title}</h2>
        <div class="mini-cols">
{render_column("Nuevo", render_items(recent, section))}
{render_column("Favoritos", render_items(favourites, section))}
        </div>
      </article>"""


def render_quotes_cluster():
    return f"""      <article class="panel influence-cluster">
        <h2><span class="mono-icon">❝</span> Quotes</h2>
        <div class="quotes-stack">
{render_quotes()}
        </div>
      </article>"""


def render_block(limit):
    books = safe_fetch("books", lambda: recent_books(limit))
    movies = safe_fetch("movies", lambda: recent_movies(limit))
    music = safe_fetch("music", lambda: recent_music(limit))

    return """    <section class="influence-grid">
""" + "\n\n".join([
        render_cluster("books", "🕮", "Books", books, FAVOURITE_BOOKS),
        render_cluster("movies", "🎞︎", "Movies", movies, FAVOURITE_MOVIES),
        render_cluster("music", "♪", "Music", music, FAVOURITE_MUSIC),
        render_quotes_cluster(),
    ]) + """
    </section>"""


def replace_placeholder(source, block):
    pattern = re.compile(
        f"{re.escape(START)}.*?{re.escape(END)}",
        flags=re.DOTALL,
    )

    if not pattern.search(source):
        raise RuntimeError("Placeholder markers not found.")

    return pattern.sub(f"{START}\n\n{block}\n    {END}", source, count=1)


if __name__ == "__main__":
    load_dotenv()

    html_path = ROOT_PATH / "sections" / "influences.html"
    limit = int(os.getenv("INFLUENCES_LIMIT", "5"))

    source = html_path.read_text(encoding="utf-8")
    output = replace_placeholder(source, render_block(limit))

    html_path.write_text(output, encoding="utf-8")
    logging.info("Updated %s", html_path)
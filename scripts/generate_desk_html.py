import os, json, requests, feedparser, re, html
from dotenv import load_dotenv

load_dotenv()

def get_spotify_token():
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     os.getenv("SPOTIFY_CLIENT_ID"),
            "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET")
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    if resp.status_code != 200:
        print("Error accessing spotify token:", resp.status_code, resp.text)
        resp.raise_for_status()
    return resp.json()["access_token"]

def get_spotify_recent(limit=5):
    token        = get_spotify_token()
    playlist_id  = os.environ["SPOTIFY_PLAYLIST_ID"]
    base_url     = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers      = {"Authorization": f"Bearer {token}"}

    total = requests.get(
        base_url,
        headers=headers,
        params={"fields": "total", "limit": 1}
    ).json()["total"]

    fetch_count = min(100, total)
    offset      = max(total - fetch_count, 0)

    params = {
        "fields": "items(added_at,track(name,artists(name),external_urls.spotify))",
        "limit":  fetch_count,
        "offset": offset,
    }
    items = requests.get(base_url, headers=headers, params=params).json()["items"]

    items.sort(key=lambda i: i["added_at"], reverse=True)
    return [
        {
            "title":  it["track"]["name"],
            "artist": ", ".join(a["name"] for a in it["track"]["artists"]),
            "url":    it["track"]["external_urls"]["spotify"],
        }
        for it in items[:limit]
    ]

def get_letterbox_rss(limit=5):
    url = f"https://letterboxd.com/{os.getenv('LETTERBOXD_USER')}/rss/"
    feed = feedparser.parse(url)

    reviews = []
    for e in feed.entries[:limit]:
        title, score = e.title.split(" - ")
        reviews.append(
            {
                "title": title,
                "score": score.count("★") + (0.5 * score.count("½")),
                "url": e.link,
                "description": re.sub(
                    r'(?si)<p><img.*?</p>\s*<p>(.*?)</p>.*',
                    r'\1',
                    e.description
                ).replace("<br />", "\n"),
            }
        )
    return reviews


def get_goodreads_rss(limit=5):
    url = f"https://www.goodreads.com/user/updates_rss/{os.getenv('GOODREADS_USER_ID')}"
    feed = feedparser.parse(url)
    entries = sorted(
        feed.entries,
        key=lambda e: e.published_parsed,
        reverse=False
    )

    reviews = []
    for entry in entries:
        if (
            'Elalber2000 added ' not in entry.title
            or entry.title.replace("Elalber2000 added ", "") in [r["title"] for r in reviews]
        ):
            continue

        clean = re.sub(
            r'(?si)^.*?gave\s+\d+\s+stars\s+to\s+.*?<br\s*/?>\s*',
            '',
            entry.get('description','')
        )
        text = html.unescape(re.sub(r'<[^>]+>', '', clean)).strip()
        m     = re.search(r'gave\s+(\d+)\s+stars', entry.get('description',''))
        score = int(m.group(1)) if m else None

        author = re.search(r'class="authorName"[^>]*>(.*?)</a>', entry.summary)

        reviews.append({
            'title':  entry.title.replace("Elalber2000 added ", ""),
            'artist': author.group(1) if author else "",
            'url':    entry.link,
            'review': text,
            'score':  score,
        })
        if len(reviews) >= limit:
            break
    return reviews


def process_score_str(score: float | str):
    if isinstance(score, str):
        return score
    else:
        return '<p class="stars">' + "★" * int(score) + ("½" if score-int(score)>0 else "") + '</p>'

def process_artist_str(name: str):
    if name == "":
        return 1
    else:
        return f' ({" ".join([i[0].upper()+"." if count<len(name.split(" "))-1 else i for count, i in enumerate(name.split(" "))])})'


def generate_desk_html():
    parent_dir = os.getcwd()
    pattern = r'(<section>\s*<p>Recientes</p>\s*<ul class="tracklist">)(.*?)(</ul>\s*</section>)'

    for section, section_fun in [
        ["music",  get_spotify_recent],
        ["movies", get_letterbox_rss],
        ["books",  get_goodreads_rss],
    ]:
        print(section)
        with open(f"{parent_dir}/Sections/desk/{section}.html", "r", encoding='utf-8') as f:
            html = f.read()

        items = [f'<li><a href="{review["url"]}" target="_blank" class="custom-link">- {review["title"]}{process_artist_str(review.get("artist", ""))}</a>{process_score_str(review.get("score", ""))}</li>'
                     for review in section_fun()]
        replacement = r'\1\n' + "\n".join(items) + r'\n\3'

        new_html = re.sub(pattern, replacement, html, flags=re.DOTALL)
        with open(f"{parent_dir}/Sections/desk/{section}.html", "w", encoding='utf-8') as f:
            html = f.write(new_html)
        

if __name__ == "__main__":
    generate_desk_html()
    #out = {
    #    "music":  get_spotify_recent(),
    #    "movies": get_letterbox_rss(),
    #    "books":  get_goodreads_rss(),
    #}
    #print(json.dumps(out, indent=2, ensure_ascii=False))

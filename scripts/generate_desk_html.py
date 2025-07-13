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

        reviews.append({
            'title':  entry.title.replace("Elalber2000 added ", ""),
            'url':    entry.link,
            'review': text,
            'score':  score,
        })
        if len(reviews) >= limit:
            break
    return reviews

def main():
    out = {
        "music":  get_spotify_recent(),
        #"movies": get_letterbox_rss(),
        #"books":  get_goodreads_rss(),
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
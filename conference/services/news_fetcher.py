import requests
from bs4 import BeautifulSoup
from django.utils.html import strip_tags

BASE_URL = "https://ncpor.res.in"
NEWS_URL = "https://ncpor.res.in/news"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (NCPS Conference Website)"
}

def fetch_official_ncpor_news(limit=7):
    response = requests.get(NEWS_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    news_items = []

    # ✅ ONLY pick real news links
    # Pattern: /news/view/###
    seen = set()
    for a in soup.select('a[href^="/news/view/"]'):
        title = strip_tags(a.get_text()).strip()
        href = a.get("href")

        if not title or len(title) < 10:
            continue

        if href in seen:
            continue
        seen.add(href)

        news_items.append({
            "title": title,
            "summary": "",
            "link": BASE_URL + href,
            "published": "",
        })

        if len(news_items) >= limit:
            break

    return news_items

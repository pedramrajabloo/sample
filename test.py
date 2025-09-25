from serpapi import GoogleSearch
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from collections import deque
import time

# -----------------------------
# 1) Google search -> DataFrame
# -----------------------------
def google_search(query, pages=3, api_key="YOUR_SERPAPI_KEY"):
    all_results = []
    for page in range(1, pages + 1):
        params = {
            "q": query,
            "engine": "google",
            "hl": "fa",
            "start": (page - 1) * 10,
            "num": 10,
            "api_key": api_key
        }
        search = GoogleSearch(params)
        results = search.get_dict()

        for item in results.get("organic_results", []):
            all_results.append({
                "page_number": page,
                "link": item.get("link", ""),
                "name": item.get("title", "")
            })

    return pd.DataFrame(all_results, columns=["page_number", "link", "name"])

# ------------------------------------------
# 2) Crawl within the same domain to find emails
# ------------------------------------------
EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def crawl_emails(start_url: str, max_pages: int = 3, delay_sec: float = 1) -> list[str]:
    """
    Crawl pages within the same domain (BFS) up to max_pages and extract emails.
    Returns a list of unique emails found.
    """
    visited = set()
    queue = deque([start_url])
    domain = urlparse(start_url).netloc
    emails_found = set()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fa,en;q=0.9"
    }

    while queue and len(visited) < max_pages:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
            ctype = resp.headers.get("Content-Type", "")
            if "text/html" not in ctype:
                continue
        except Exception:
            continue

        # Extract emails from visible text
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        for email in set(EMAIL_REGEX.findall(text)):
            # یک فیلتر ساده برای حذف ایمیل‌های خیلی عمومیِ نامعتبر
            if not email.lower().startswith(("example@", "test@", "info@example", "name@domain")):
                emails_found.add(email)

        # Enqueue same-domain links
        for a in soup.find_all("a", href=True):
            absolute = urljoin(url, a["href"])
            if urlparse(absolute).netloc == domain and absolute not in visited:
                # اختیاری: فقط لینک‌های http(s)
                if absolute.startswith("http"):
                    queue.append(absolute)

        # polite crawling
        time.sleep(delay_sec)

    return sorted(emails_found)

# ---------------------------------------------------
# 3) Apply to DF: add a new column "emails" (semicolon)
# ---------------------------------------------------
def attach_emails_column(df: pd.DataFrame, max_pages_per_site: int = 3) -> pd.DataFrame:
    emails_col = []
    for _, row in df.iterrows():
        url = row.get("link", "")
        if not isinstance(url, str) or not url.startswith("http"):
            emails_col.append("")
            continue

        try:
            emails = crawl_emails(url, max_pages=max_pages_per_site)
            emails_col.append("; ".join(emails))
        except Exception:
            emails_col.append("")
    df = df.copy()
    df["emails"] = emails_col
    return df

# -----------------------------
# 4) User inputs + run + save
# -----------------------------
if __name__ == "__main__":
    query = input("🔎 عبارت جستجو را وارد کنید: ").strip()
    pages = int(input("📄 تعداد صفحات گوگل (هر صفحه ~10 نتیجه): ").strip())
    max_pages = int(input("🕷️ حداکثر صفحات برای کراول در هر دامنه: ").strip())

    # کلید خودت را اینجا بگذار
    API_KEY = "7aa4925cbf1f8923345663bb01db66ed22352e71e1e2c32d3cb0eaa287a7bb7b"

    df = google_search(query, pages, api_key=API_KEY)
    if df.empty:
        print("نتیجه‌ای یافت نشد.")
    else:
        df = attach_emails_column(df, max_pages_per_site=max_pages)
        print(df)
        df.to_csv("google_results_with_emails.csv", index=False, encoding="utf-8-sig")
        print("✅ ذخیره شد: google_results_with_emails.csv")



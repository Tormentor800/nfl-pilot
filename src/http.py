# src/http.py
import time, random, requests

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    # IMPORTANT: referer to the same domain
    "Referer": "https://www.pro-football-reference.com/",
})

def fetch(url: str, max_retries: int = 5) -> requests.Response:
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            # polite jitter + gradual backoff
            time.sleep(random.uniform(1.2, 2.4) + (attempt - 1) * 0.6)
            resp = SESSION.get(url, timeout=20, allow_redirects=True)
            # Some anti-bot setups 302 to a challenge; follow and re-try once
            if resp.status_code in (301, 302, 303, 307, 308):
                time.sleep(random.uniform(0.8, 1.6))
                resp = SESSION.get(resp.headers.get("Location", url), timeout=20)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_err = e
    raise last_err

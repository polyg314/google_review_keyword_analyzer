# utils.py
import os
import re
import requests
from urllib.parse import unquote
from dotenv import load_dotenv

load_dotenv()
serpapi_key = os.getenv("SERPAPI_KEY")

def extract_data_id_from_url(url: str) -> str:
    """
    Extracts the data_id from a Google Maps URL by looking for the 0x...:0x... pattern in the /data= segment.
    """
    try:
        decoded = unquote(url)

        # Look for 0x...:0x... pattern after /data=
        match = re.search(r"/data=.*?(0x[0-9a-f]+:0x[0-9a-f]+)", decoded)
        if match:
            return match.group(1)

    except Exception as e:
        print("Error extracting data_id:", e)

    return None


def fetch_reviews_by_data_id(data_id: str, max_reviews: int = 100, sort_by: str = "newestFirst", lang: str = "en"):
    """
    Fetches up to `max_reviews` Google Maps reviews using SerpAPI.
    Handles pagination with next_page_token.
    """
    base_url = "https://serpapi.com/search.json"
    all_reviews = []
    page_token = None

    while len(all_reviews) < max_reviews:
        params = {
            "engine": "google_maps_reviews",
            "data_id": data_id,
            "api_key": serpapi_key,
            "hl": lang,
            "sort_by": sort_by,
        }

        if page_token:
            params["next_page_token"] = page_token
            params["num"] = 20

        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        new_reviews = data.get("reviews", [])
        all_reviews.extend(new_reviews)

        page_token = data.get("serpapi_pagination", {}).get("next_page_token")
        if not page_token:
            break

    return all_reviews[:max_reviews]

def analyze_keyword_mentions(reviews, keyword_string):
    """
    Analyzes keyword mentions in review text (case-insensitive).
    - Each keyword is only counted once per review.
    - Keyword must be matched as a whole word (not inside another word).
    """
    keywords = [kw.strip().lower() for kw in keyword_string.split(",") if kw.strip()]
    total_reviews = len(reviews)

    keyword_counts = {kw: 0 for kw in keywords}
    reviews_with_any_keyword = 0
    non_empty_reviews = 0

    for review in reviews:
        text = (review.get("snippet") or "").strip().lower()
        if not text:
            continue

        non_empty_reviews += 1
        matched_any = False

        for kw in keywords:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, text):
                keyword_counts[kw] += 1
                matched_any = True

        if matched_any:
            reviews_with_any_keyword += 1

    empty_reviews = total_reviews - non_empty_reviews

    raw_percentages = {
        kw: (count / total_reviews * 100) if total_reviews else 0
        for kw, count in keyword_counts.items()
    }
    normalized_percentages = {
        kw: (count / non_empty_reviews * 100) if non_empty_reviews else 0
        for kw, count in keyword_counts.items()
    }

    return {
        "keyword_counts": keyword_counts,
        "raw_percentages": raw_percentages,
        "normalized_percentages": normalized_percentages,
        "reviews_with_any_keyword": reviews_with_any_keyword,
        "raw_any_percentage": (reviews_with_any_keyword / total_reviews * 100) if total_reviews else 0,
        "norm_any_percentage": (reviews_with_any_keyword / non_empty_reviews * 100) if non_empty_reviews else 0,
        "empty_count": empty_reviews,
        "empty_percentage": (empty_reviews / total_reviews * 100) if total_reviews else 0,
        "total": total_reviews,
        "non_empty": non_empty_reviews,
    }
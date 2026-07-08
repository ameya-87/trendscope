import os
import requests
import pandas as pd
from datetime import datetime

# Base URL for the TVmaze API
BASE_URL = "http://api.tvmaze.com"

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def search_show(query: str) -> dict | None:
    """Searches for a TV show by name."""
    response = requests.get(f"{BASE_URL}/search/shows", params={"q": query})
    response.raise_for_status()
    results = response.json()
    if results:
        return results[0]["show"]
    return None

def get_show_episodes(show_id: int) -> list:
    """Gets all episodes for a given show ID."""
    response = requests.get(f"{BASE_URL}/shows/{show_id}/episodes")
    response.raise_for_status()
    return response.json()

def scrape_and_save(query: str = "The Office", output_dir: str = os.path.join("data", "raw")) -> str:
    """
    Scrapes TV show episode data for a given query and saves it to a CSV file.
    Returns the path to the saved CSV file.
    """
    _ensure_dir(output_dir)

    show = search_show(query)
    if not show:
        print(f"No show found for query: {query}")
        return ""

    episodes = get_show_episodes(show["id"])

    if not episodes:
        print(f"No episodes found for show: {show['name']}")
        return ""

    data = []
    for episode in episodes:
        data.append({
            "source": "TVmaze",
            "published_at": episode.get("airdate"),
            "keyword": query, # Using the query as a keyword for now
            "title": episode.get("name"),
            "text": str(episode.get("summary", "")).replace("<p>", "").replace("</p>", ""),
            "url": episode.get("url"),
            "author": show.get("name"), # Using show name as author
            "views": None, # TVmaze API does not provide views
            "likes": None, # TVmaze API does not provide likes
            "comments": None, # TVmaze API does not provide comments
            "season": episode.get("season"),
            "episode_number": episode.get("number"),
        })

    df = pd.DataFrame(data)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"tvmaze_{ts}.csv"
    output_path = os.path.join(output_dir, file_name)
    df.to_csv(output_path, index=False)
    print(f"✅ TVmaze data for '{query}' saved to {output_path}")
    return output_path

def scrape_top_shows(pages: int = 3, output_dir: str = os.path.join("data", "raw")) -> str:
    """
    Scrape top shows across TVMaze pages and save a flattened show-level CSV.
    Returns the path to the saved CSV file.
    """
    _ensure_dir(output_dir)
    all_shows = []
    for page in range(max(1, pages)):
        try:
            resp = requests.get(f"{BASE_URL}/shows", params={"page": page})
            resp.raise_for_status()
            shows = resp.json()
        except Exception:
            shows = []
        for s in shows:
            rating_avg = None
            try:
                rating_avg = s.get('rating', {}).get('average')
            except Exception:
                rating_avg = None
            network_name = (s.get('network') or {}).get('name') if s.get('network') else ''
            web_channel_name = (s.get('webChannel') or {}).get('name') if s.get('webChannel') else ''
            schedule = s.get('schedule') or {}
            days = schedule.get('days') or []
            time = schedule.get('time') or ''
            genres = s.get('genres') or []
            summary = s.get('summary') or ''
            if isinstance(summary, str):
                summary = summary.replace('<p>', '').replace('</p>', '').replace('<b>', '').replace('</b>', '')
            all_shows.append({
                'id': s.get('id'),
                'name': s.get('name'),
                'genres': ', '.join(genres) if isinstance(genres, list) else genres,
                'status': s.get('status'),
                'language': s.get('language'),
                'rating_average': rating_avg,
                'premiered': s.get('premiered'),
                'officialSite': s.get('officialSite'),
                'network_name': network_name,
                'webChannel_name': web_channel_name,
                'schedule_time': time,
                'schedule_days': ', '.join(days) if isinstance(days, list) else days,
                'weight': s.get('weight'),
                'updated': s.get('updated'),
                'summary': summary
            })
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"tvmaze_{ts}.csv"
    output_path = os.path.join(output_dir, file_name)
    pd.DataFrame(all_shows).to_csv(output_path, index=False)
    print(f"✅ TVmaze top shows saved to {output_path}")
    return output_path

if __name__ == "__main__":
    # Example usage:
    scrape_and_save("Game of Thrones")
    scrape_and_save("Friends")
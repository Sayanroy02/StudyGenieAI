# tools/google_search.py
import os, requests, logging
logger = logging.getLogger("edu_agent.tools")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

class GoogleSearchTool:
    def __init__(self, api_key=None, cse_id=None):
        self.api_key = api_key or GOOGLE_API_KEY
        self.cse_id = cse_id or GOOGLE_CSE_ID
        self.endpoint = "https://www.googleapis.com/customsearch/v1"

    def search(self, query: str, top_k: int = 3):
        if not self.api_key or not self.cse_id:
            logger.warning("GoogleSearchTool: missing API key or CSE ID")
            return []
        params = {"key": self.api_key, "cx": self.cse_id, "q": query, "num": top_k}
        try:
            r = requests.get(self.endpoint, params=params, timeout=8)
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])[:top_k]
            results = []
            for it in items:
                results.append({
                    "title": it.get("title"),
                    "link": it.get("link"),
                    "snippet": it.get("snippet") or ""
                })
            return results
        except Exception as e:
            logger.exception("GoogleSearchTool.search failed: %s", e)
            return []

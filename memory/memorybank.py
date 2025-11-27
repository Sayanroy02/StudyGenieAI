# memory/memorybank.py
import json, os, threading
from datetime import datetime
from typing import List, Dict, Any

lock = threading.Lock()

class MemoryBank:
    def __init__(self, filename: str = "memory_bank.json"):
        self.filename = filename or "memory_bank.json"
        if not os.path.exists(self.filename):
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump({}, f)
        self._load()

    def _load(self):
        with open(self.filename, "r", encoding="utf-8") as f:
            try:
                self.store = json.load(f)
            except Exception:
                self.store = {}

    def _save(self):
        with lock:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(self.store, f, indent=2, ensure_ascii=False)

    def add_interaction(self, session_id: str, user: str, bot: str, sources: List[Dict[str, str]] = None):
        self._load()
        sess = self.store.setdefault(session_id, {"history": []})
        sess["history"].append({
            "time": datetime.now().isoformat(),
            "user": user,
            "bot": bot,
            "sources": sources or []
        })
        sess["history"] = sess["history"][-200:]
        self._save()

    def get_recent_context(self, session_id: str, n: int = 5) -> str:
        self._load()
        sess = self.store.get(session_id, {})
        hist = sess.get("history", [])[-n:]
        ctx = ""
        for it in hist:
            ctx += f"USER: {it.get('user')}\nBOT: {it.get('bot')}\n"
        return ctx

    def get_history(self, session_id: str):
        self._load()
        return self.store.get(session_id, {}).get("history", [])

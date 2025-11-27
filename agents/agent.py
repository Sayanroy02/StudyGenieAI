# agents/agent.py
import os, uuid, time, logging
from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime
import google.genai as genai
from google.genai import types
from tools.google_search import GoogleSearchTool
from memory.memorybank import MemoryBank

logger = logging.getLogger("edu_agent")
logger.setLevel(logging.INFO)

API_KEY = os.getenv("GOOGLE_API_KEY")
USE_GEMINI = os.getenv("USE_GEMINI", "true").lower() in ("1", "true", "yes")

if USE_GEMINI and API_KEY:
    try:
        genai.configure(api_key=API_KEY)
    except Exception:
        pass


@dataclass
class AgentResponse:
    text: str
    sources: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class EduAgent:
    def __init__(self, memory_file: str = "memory_bank.json"):
        self.search_tool = GoogleSearchTool()
        self.memory = MemoryBank(memory_file)

    # ---------------------------
    # Greeting / preprocessing
    # ---------------------------
    def preprocess_user_input(self, text: str) -> str:
        msg = text.strip().lower()
        greetings = ["hi", "hello", "hey", "hii", "hola"]
        if msg in greetings:
            return "Greet the user politely, introduce yourself as EduMentor, and ask how you can help with studies."
        return text

    # ---------------------------
    # Extract text from Gemini response
    # ---------------------------
    def _extract_text_from_response(self, resp) -> str:
        try:
            if hasattr(resp, "text") and resp.text:
                return resp.text
        except:
            pass

        try:
            out = getattr(resp, "output", None)
            if out:
                for o in out:
                    parts = getattr(o, "content", None) or o.get("content", [])
                    for p in parts:
                        txt = p.get("text") if isinstance(p, dict) else getattr(p, "text", None)
                        if txt:
                            return txt
        except:
            pass

        try:
            cand = getattr(resp, "candidates", None)
            if cand:
                c0 = cand[0]
                if hasattr(c0, "content"):
                    parts = getattr(c0, "content", [])
                    for p in parts:
                        txt = p.get("text") if isinstance(p, dict) else getattr(p, "text", None)
                        if txt:
                            return txt
                if hasattr(c0, "text"):
                    return c0.text
        except:
            pass

        return str(resp)

    # ---------------------------
    # Gemini API Call
    # ---------------------------
    def _call_gemini(self, prompt: str, max_output_tokens: int = 400) -> str:
        if not (USE_GEMINI and API_KEY):
            return "LLM not configured. Set GOOGLE_API_KEY in .env to enable Gemini."

        try:
            client = genai.Client()
            try:
                resp = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=max_output_tokens,
                        temperature=0.2
                    )
                )
                return self._extract_text_from_response(resp)
            except Exception:
                resp = genai.generate_text(
                    model="gemini-2.0-flash",
                    prompt=prompt
                )
                return getattr(resp, "text", str(resp))
        except Exception as outer:
            return f"LLM Error: {outer}"

    # ---------------------------
    # Build Prompt with Structure Formatting
    # ---------------------------
    def build_prompt(self, user_query: str, context: str, sources: List[Dict[str, str]]):
        src_text = "\n".join(
            [f"- {s['title']}: {s['snippet']} (url: {s['link']})"
             for s in sources]
        )

        prompt = f"""
 "You are EduMentor — a friendly structured AI teacher.\n"
    "Always respond in CLEAN STRUCTURED FORMAT (NO markdown, NO ###, NO **bold**).\n\n"

    "STRUCTURE YOU MUST FOLLOW:\n"
    "1) Explanation: 4–6 lines in simple language.\n"
    "2) Worked Example: 3–5 lines.\n"
    "3) Summary: exactly 2 lines.\n"
    "4) Sources: Up to 3 bullet points in this format:\n"
    "   - Title: URL\n\n"

    "Context:\n{context}\n\n"
    "Web sources:\n{src_text}\n\n"
    f"Question: {user_query}\n"

### 📘 CONTEXT
{context}

### 🔎 WEB SOURCES
{src_text}

### ❓ USER QUESTION
{user_query}

### 👉 NOW RESPOND FOLLOWING ALL RULES ABOVE
"""
        return prompt

    # ---------------------------
    # Main Answer Function
    # ---------------------------
    def answer(self, session_id: str, user_query: str) -> AgentResponse:
        trace_id = str(uuid.uuid4())
        logger.info("[%s] Query: %s", trace_id, user_query)
        start = time.time()

        # Greeting logic
        processed_query = self.preprocess_user_input(user_query)

        # Memory context
        context = self.memory.get_recent_context(session_id, n=5)

        # Web search
        sources = self.search_tool.search(user_query, top_k=3)

        # Prompt
        prompt = self.build_prompt(processed_query, context, sources)

        # Get response
        text = self._call_gemini(prompt)

        # Save memory
        self.memory.add_interaction(session_id, user_query, text, sources)

        elapsed = time.time() - start
        logger.info("[%s] Completed in %.2fs", trace_id, elapsed)

        return AgentResponse(
            text=text,
            sources=sources,
            metadata={
                "trace_id": trace_id,
                "elapsed_s": elapsed,
                "time": datetime.now().isoformat()
            }
        )

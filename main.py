# main.py
import os, uuid, logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

load_dotenv()

from agents.agent import EduAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edu_agent_app")

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="template")

MEMORY_FILE = os.getenv("MEMORY_FILE", "memory_bank.json")
agent = EduAgent(memory_file=MEMORY_FILE)

REQUESTS = Counter("edu_agent_requests_total", "Total bot requests")


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.post("/api/chat")
async def chat_api(request: Request):
    REQUESTS.inc()
    payload = await request.json()
    session_id = payload.get("session_id") or str(uuid.uuid4())
    user_text = payload.get("text", "")
    logger.info("Chat request session=%s text=%s", session_id, user_text)
    resp = agent.answer(session_id=session_id, user_query=user_text)
    return JSONResponse({"reply": resp.text, "sources": resp.sources, "metadata": resp.metadata, "session_id": session_id})


@app.get("/api/history/{session_id}")
async def history(session_id: str):
    hist = agent.memory.get_history(session_id)
    return JSONResponse({"history": hist})


@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return HTMLResponse(data, media_type=CONTENT_TYPE_LATEST)

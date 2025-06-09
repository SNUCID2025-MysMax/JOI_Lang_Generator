from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import json, os
import logging
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any, Optional
    
# 사용할 모델 - Qwen2.5-Coder-7B
MODEL_NAME = "qwenCoder"

app = FastAPI()
logger = logging.getLogger("uvicorn")

# 템플릿 및 정적 파일 설정
RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "resources")
TEMPLATES_DIR = os.path.join(RESOURCES_DIR, "templates")
STATIC_DIR = os.path.join(RESOURCES_DIR, "static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# 기본 연결된 장치 정보 로드
with open("./app/resources/things.json", "r", encoding="utf-8") as f:
    DEFAULT_CONNECTED_DEVICES = json.load(f)
last_connected_devices = DEFAULT_CONNECTED_DEVICES.copy()

class GenerateJOICodeRequest(BaseModel):
    sentence: str
    model: str
    connected_devices: Dict[str, Any]
    current_time: str
    other_params: Optional[Dict[str, Any]] = None

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    current_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "JOI Code Generator",
        "model_name": MODEL_NAME,
        "current_time": current_time,
    })

@app.post("/generate_joi_code")
async def generate_code(request: GenerateJOICodeRequest):

    return {
        "current_time": request.current_time,
        "code": [
            {
                "name": "Scenario1",
                "cron": "0 9 * * *",
                "period": -1,
                "code": "(#Light #livingroom).switch_on()"
            },
            {
                "name": "Scenario2",
                "cron": "0 9 * * *",
                "period": 10000,
                "code": "(#Light #livingroom).switch_on()"
            }
        ],
        "log": {
            "response_time": "0.321 seconds",
            "inference_time": "0.279 seconds",
            "translated_sentence": "translated",
            "mapped_devices": [
                "Light"
            ]
        }
    }

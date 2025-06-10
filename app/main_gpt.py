from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import json, os
import logging
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any, Optional

from .services.run_gpt import generate_joi_code 
from .services.loader_gpt import load_all_resources
    
# 사용할 모델
MODEL_NAME = "GPT-4"

app = FastAPI()
logger = logging.getLogger("uvicorn")

MODEL_RESOURCES = load_all_resources(MODEL_NAME)
logger.info(f"resources loaded for {MODEL_NAME}")

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

    global last_connected_devices

    # connected_devices가 빈 dict이면 이전 상태 유지
    if request.connected_devices == {}:
        connected_devices = last_connected_devices
    else:
        connected_devices = request.connected_devices
        last_connected_devices = connected_devices  # 상태 갱신

    result = generate_joi_code(
        sentence=request.sentence,
        # model=request.model,
        model=MODEL_NAME,  # 모델 이름을 서버에서 고정
        connected_devices=connected_devices,
        current_time=request.current_time,
        other_params=request.other_params,
        model_resources=MODEL_RESOURCES,
    )

    return result
    # return {
    #     "current_time": request.current_time,
    #     "code": [
    #         {
    #             "name": "Scenario1",
    #             "cron": "0 9 * * *",
    #             "period": -1,
    #             "code": "(#Light #livingroom).switch_on()"
    #         },
    #         {
    #             "name": "Scenario2",
    #             "cron": "0 9 * * *",
    #             "period": 10000,
    #             "code": "(#Light #livingroom).switch_on()"
    #         }
    #     ],
    #     "log": {
    #         "response_time": "0.321 seconds",
    #         "inference_time": "0.279 seconds",
    #         "translated_sentence": "translated",
    #         "mapped_devices": [
    #             "Light"
    #         ]
    #     }
    # }

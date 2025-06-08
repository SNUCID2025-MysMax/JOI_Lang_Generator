import json
import logging
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional

from services.run import generate_joi_code 
from services.loader import load_all_resources

# 필요한 디렉토리
# resources / services / Embedding / models

app = FastAPI()

logger = logging.getLogger("uvicorn")
MODEL_NAME = "gemma3"
MODEL_RESOURCES = load_all_resources(MODEL_NAME)
logger.info(f"resources loaded for {MODEL_NAME}")

with open("./resources/things.json", "r", encoding="utf-8") as f:
    DEFAULT_CONNECTED_DEVICES = json.load(f)

last_connected_devices = DEFAULT_CONNECTED_DEVICES.copy()

class GenerateJOICodeRequest(BaseModel):
    sentence: str
    model: str
    connected_devices: Dict[str, Any]
    current_time: str
    other_params: Optional[Dict[str, Any]] = None


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

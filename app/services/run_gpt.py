# run.py

import os, re, json, copy
from datetime import datetime
from transformers import TextStreamer
from .translate import deepl_translate
from .embedding import hybrid_recommend
from .validate import validate
from .joi_tool import parse_scenarios, extract_last_code_block, extract_device_tags, add_device_tags
import logging
logger = logging.getLogger("uvicorn")

# JOI 코드 생성 함수
def generate_joi_code(
    sentence: str,
    model: str,
    connected_devices: dict,
    current_time: str,
    other_params: dict = None,
    model_resources: dict = None
) -> dict:
    # 모델 리소스 추출
    client = model_resources["model"]
    tokenizer = model_resources["tokenizer"]
    stop_token_ids = model_resources["stop_token_ids"]
    embed_model = model_resources["embed_model"]
    embedding_data = model_resources["embedding_data"]
    sim_model = model_resources["sim_model"]
    device_classes = copy.deepcopy(model_resources["device_classes"])
    grammar = model_resources["grammar"]


    # # gpt는 번역 없이
    # sentence_translated = sentence
    # 명령어 번역
    try:
        sentence_translated = deepl_translate(sentence)
    except Exception:
        sentence_translated = sentence 
    logger.info(f"Translated Sentence: {sentence_translated}")

    start = datetime.now()

    # 디바이스 및 태그 정보 추출
    tag_device, tag_sets = extract_device_tags(connected_devices, device_classes)

    # 디바이스 클래스 docs에 태그 주석 추가
    device_classes = add_device_tags(device_classes, tag_device)

    # 명령어로부터 필요한 디바이스를 추출 - BGE-M3 모델 이용
    service_selected = set(i["key"] for i in hybrid_recommend(embed_model, sentence_translated, embedding_data, list(tag_device.keys())))
    service_selected.add("Clock") # Clock의 Delay 기능을 위해 항상 포함
    
    service_doc = "\n---\n".join([device_classes[i] for i in service_selected])

    # 최소한의 TTS에 필요한 Speaker 정보 추가
    if ("Speaker" not in service_selected):
        # 현재 Speaker 디바이스가 사용 가능한 디바이스 목록에 있을 경우 포함
        speaker_doc = device_classes.get("Speaker", "")
        if speaker_doc:
            match = re.search(r'Device\s+\w+:(?:.*?\n)*?(?=^\s*Enums:)', speaker_doc, re.MULTILINE)
            if match:
                speaker_info = match.group().strip() + "\n\nMethods:\n  mediaPlayback_speak(text: STRING) -> VOID  # text-to-speech\n\n"
                service_doc += "\n---\n" + speaker_info
                service_selected.add("Speaker")


    # == 모델 호출 및 생성 ==
    messages = [
        {"role": "system", "content": f"<grammar>\n{grammar}</grammar>\n\n<devices>{service_doc}</devices>",},
        {"role": "user", "content": f"Current Time: {current_time}\n\nGenerate JOI Lang code for \"{sentence_translated}\""}
    ]

    start_inference = datetime.now()

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
    )

    end_inference = datetime.now()

    response = response.choices[0].message.content.strip()
    
    logger.info(f"\nModel Response:\n{response}")
    
    # 생성한 텍스트에서 코드 추출
    try:
        code = parse_scenarios(extract_last_code_block(response))['code']
    except:
        try:
            code = parse_scenarios(response)['code']
        except:
            code = [{'name': 'Scenario1', 'cron': '', 'period': -1, 'code': ''}]

    # 각 코드 조각 별로 정제, 검증
    code_ret = []
    for c in code:
        code_piece = c["code"].strip()
        # 유사도 기반 교정 & 태그 검사 & 영어 문자열 번역
        # 인자: 코드, docs, 사용 가능한 디바이스, 디바이스 별 태그 집합, sentence transformer 모델
        code_piece = validate(code_piece, device_classes, list(tag_device.keys()), tag_sets, sim_model)
        c["code"] = code_piece
        if (c["code"]==""):
            continue
        code_ret.append(c)

    logger.info(f"\nReturn:\n{code_ret}")

    end = datetime.now()
    
    return {
        "code": code_ret,
        "log": {
            "response_time": f"{(end - start).total_seconds():.3f} seconds",
            "inference_time": f"{(end_inference - start_inference).total_seconds():.3f} seconds",
            "translated_sentence": sentence_translated,
            "mapped_devices": list(service_selected)
        }
    }


# def generate_joi_code(sentence: str, model: str, connected_devices: dict, current_time: str, other_params: dict = None) -> dict:
#     """
#     하드코딩된 테스트 결과를 반환하는 generate_joi_code 함수.
#     실제 LLM 호출 없이 테스트 용도로 사용됩니다.

#     Parameters:
#     - sentence (str): 자연어 명령어
#     - model (str): 모델 이름 (사용되지 않음)
#     - connected_devices (dict): 디바이스 정보
#     - current_time (str): 현재 시각 (YYYY-MM-DD HH:MM:SS)
#     - other_params (dict, optional): 기타 옵션

#     Returns:
#     - dict: JOI 시나리오 및 로그 정보
#     """
#     return {
#         "code": [
#             {
#                 "name": "Scenario1",
#                 "cron": "0 9 * * *",
#                 "period": -1,
#                 "code": "(#Light #livingroom).switch_on()"
#             },
#             {
#                 "name": "Scenario2",
#                 "cron": "0 9 * * *",
#                 "period": 10000,
#                 "code": "(#Light #livingroom).switch_on()"
#             }
#         ],
#         "log": {
#             "response_time": "0.321 seconds",
#             "inference_time": "0.279 seconds",
#             "translated_sentence": sentence,
#             "mapped_devices": [
#                 "Light"
#             ]
#         }
#     }
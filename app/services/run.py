# run.py

import os, re, json, copy, torch
import concurrent.futures
from datetime import datetime
from services.translate import deepl_translate
from embedding import hybrid_recommend
from services.validate import validate
from services.joi_tool import parse_scenarios, extract_last_code_block


import logging
logger = logging.getLogger("uvicorn")

TIME_OUT = 15

from transformers import TextStreamer

# == 모델 호출 함수 == (타임아웃 용)
def call_model(model, inputs, stop_token_ids, tokenizer):
    return model.generate(
        input_ids=inputs,
        eos_token_id=stop_token_ids,
        pad_token_id=tokenizer.pad_token_id,
        max_new_tokens=1024,
        use_cache=True,
        streamer = TextStreamer(tokenizer, skip_prompt = True),
    )

# === JOI 코드 생성 함수 ===
def generate_joi_code(
    sentence: str,
    model: str,
    connected_devices: dict,
    current_time: str,
    other_params: dict = None,
    model_resources: dict = None
) -> dict:
    llm_model = model_resources["model"]
    tokenizer = model_resources["tokenizer"]
    stop_token_ids = model_resources["stop_token_ids"]
    embed_model = model_resources["embed_model"]
    sim_model = model_resources["sim_model"]
    device_classes = copy.deepcopy(model_resources["device_classes"])
    grammar = model_resources["grammar"]

    start = datetime.now()

    # == 디바이스 및 태그 정보 추출 ==
    # 각 디바이스별 태그 접근자 리스트
    unique_tag_sets = {frozenset(connected_devices[k]['tags']) for k in connected_devices}
    tag_sets = [list(tag_set) for tag_set in unique_tag_sets]

    # 디바이스별 장소, 사용자 지정 태그 추출
    tag_device = {}
    for tag_set in tag_sets:
        device_tags = [tag for tag in tag_set if tag in device_classes]
        other_tags = [tag for tag in tag_set if tag not in device_classes]

        for device_tag in device_tags:
            if device_tag not in tag_device:
                tag_device[device_tag] = []
            tag_device[device_tag].extend(other_tags)

    # 디바이스 클래스 docs에 태그 주석 추가
    for device_tag, extra_tags in tag_device.items():
        doc = device_classes[device_tag]
        lines = doc.splitlines()
        new_lines = lines[:4] + [f"    #{tag}" for tag in sorted(set(extra_tags))] + lines[4:]
        device_classes[device_tag] = "\n".join(new_lines)

    service_selected = set(i["key"] for i in hybrid_recommend(embed_model, sentence, list(tag_device.keys()), max_k=10))
    service_selected.add("Clock")

    service_doc = "\n---\n".join([device_classes[i] for i in service_selected])

    # == 문장 번역 ==
    try:
        sentence_translated = deepl_translate(sentence)
    except Exception:
        sentence_translated = sentence 
    logger.info(f"Translated Sentence: {sentence_translated}")

    # sentence_translated = sentence

    # == 모델 호출 및 생성 ==
    messages = [{"role": "system", "content": grammar}] + \
                [{"role": "system", "content": service_doc}] + \
                [{"role": "user", "content": f"Current Time: {current_time}\n\nGenerate JOI Lang code for \"{sentence_translated}\""}]

    inputs = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to("cuda")

    start_inference = datetime.now()
    # outputs = llm_model.generate(
    #     input_ids=inputs,
    #     eos_token_id=stop_token_ids,
    #     pad_token_id=tokenizer.pad_token_id,
    #     # max_new_tokens=128,
    #     use_cache=True
    # )

    response = ""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(call_model, llm_model, inputs, stop_token_ids, tokenizer)
        try:
            outputs = future.result(timeout=TIME_OUT)
            generated_ids = outputs[0][len(inputs[0]):]
            
            # # Fixed condition check
            # if len(generated_ids) > 0 and generated_ids[-1].item() in stop_token_ids:
            #     generated_ids = generated_ids[:-1]
            stop_indexes = [i for i, tok_id in enumerate(generated_ids) if tok_id in stop_token_ids]
            if stop_indexes:
                generated_ids = generated_ids[:stop_indexes[0]]

            response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
        except concurrent.futures.TimeoutError:
            response = ""

    end = datetime.now()
    logger.info(f"\nModel Response:\n{response}")
    # --- 파싱 ---
    try:
        code = parse_scenarios(extract_last_code_block(response))['code']
    except:
        try:
            code = parse_scenarios(response)['code']
        except:
            code = [{'name': 'Scenario1', 'cron': '', 'period': -1, 'code': ''}]

    # --- 정제 ---
    # 각 코드 조각 별로 교정
    for c in code:
        code_piece = c["code"].strip()
        # 유사도 기반 교정 & 태그 검사 & 영어 문자열 번역
        # 인자: 코드, docs, 사용 가능한 디바이스, 디바이스 별 태그 집합, sentence 모델
        code_piece = validate(code_piece, device_classes, list(tag_device.keys()), tag_sets, sim_model)
        c["code"] = code_piece

    logger.info(f"\nReturn:\n{code}")
    return {
        "code": code,
        "log": {
            "response_time": f"{(end - start).total_seconds():.3f} seconds",
            "inference_time": f"{(end - start_inference).total_seconds():.3f} seconds",
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

# run.py

import os, re, json, copy, torch
import concurrent.futures
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
    """
    Requset로부터 JOI 코드를 생성, 검증 후 반환합니다.
    """

    # 모델 리소스 추출
    llm_model = model_resources["model"]
    tokenizer = model_resources["tokenizer"]
    stop_token_ids = model_resources["stop_token_ids"]
    embed_model = model_resources["embed_model"]
    embedding_data = model_resources["embedding_data"]
    sim_model = model_resources["sim_model"]
    device_classes = copy.deepcopy(model_resources["device_classes"])
    grammar = model_resources["grammar"]

    start = datetime.now()

    # 명령어 번역
    try:
        sentence_translated = deepl_translate(sentence)
    except Exception:
        sentence_translated = sentence 
    logger.info(f"Translated Sentence: {sentence_translated}")

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

    # 모델 호출 및 생성
    prompt = f"Current Time: {current_time}\n\nGenerate JOI Lang code for \"{sentence_translated}\""
    
    if other_params:
        other_params_str = json.dumps(other_params, indent=2, ensure_ascii=False)
        prompt += f"\n\n<USER_INFO>\n{other_params_str}\n</USER_INFO>"

    messages = [
        {"role": "system", "content": f"{grammar}\n<DEVICES>\n{service_doc}\n</DEVICES>",},
        {"role": "user", "content": prompt}
    ]

    inputs = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt").to("cuda")

    start_inference = datetime.now()

    outputs = llm_model.generate(
        input_ids=inputs,
        eos_token_id=stop_token_ids,
        pad_token_id=tokenizer.pad_token_id,
        max_new_tokens=1024,
        use_cache=True,
        # 더 일관된 출력을 위한 인자들
        # do_sample=False,
        temperature=0.1,
        repetition_penalty=1.2,
        streamer = TextStreamer(tokenizer, skip_prompt = True),
    )

    end_inference = datetime.now()

    generated_ids = outputs[0][len(inputs[0]):]
    
    # stop_token_ids에 해당하는 토큰이 생성된 경우, 해당 인덱스까지 잘라냄
    stop_indexes = [i for i, tok_id in enumerate(generated_ids) if tok_id in stop_token_ids]
    if stop_indexes:
        generated_ids = generated_ids[:stop_indexes[0]]

    response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

    # logger.info(f"\nModel Response:\n{response}")
    
    # 생성한 텍스트에서 코드 추출
    try:
        code = parse_scenarios(extract_last_code_block(response))['code']
    except Exception as e:
        # print(f"Error extracting code block: {e}")
        try:
            code = parse_scenarios(response)['code']
        except Exception as e:
            logger.error(f"Error parsing scenarios: {e}")
            code = [{'name': 'Scenario1', 'cron': '', 'period': -1, 'code': ''}]

    logger.info(f"\nExtracted Code:\n{code}")

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

# model_loader.py
import unsloth
import os, re
import numpy as np
import json
import pickle
from unsloth import FastLanguageModel
from unsloth.chat_templates import get_chat_template
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer
from peft import PeftModel

from FlagEmbedding import BGEM3FlagModel

# 서비스 문서 파싱 함수
def extract_classes_by_name(text: str):
    pattern = r'Device\s+(\w+)\s*:\s*\n\s+"""(.*?)"""'
    matches = re.finditer(pattern, text, re.DOTALL)
    return {match.group(1): match.group(0) for match in matches}

def load_all_resources(model_name: str):
    """
    모델과 어댑터를 로드하고 필요한 리소스를 반환합니다.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(base_dir, ".."))

    model_base_path = os.path.join(root_dir, "resources", "models", f"{model_name}-model")
    # adapter_path = os.path.join(root_dir, "resources", "models", f"{model_name}-adapter")

    # 1. 모델 로딩 - 첫 실행 시 다운로드에 시간이 소요됨
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_base_path,
        max_seq_length=32768,
        # fast_inference = True,
        dtype=None,
        load_in_4bit=True,
    )
    # model.load_adapter(adapter_path)
    FastLanguageModel.for_inference(model)

    # 2. tokenizer 설정
    stop_tokens = []

    # tokenizer = get_chat_template(tokenizer, chat_template="chatml", map_eos_token=True)
    # tokenizer.add_bos_token = False
    # stop_tokens = [
    #     "<|im_end|>", "<|endoftext|>", "<|file_sep|>", "<|fim_prefix|>", "<|fim_middle|>", "<|fim_suffix|>",
    #     "<|fim_pad|>", "<|repo_name|>", "<|im_start|>", "<|object_ref_start|>", "<|object_ref_end|>",
    #     "<|box_start|>", "<|box_end|>", "<|quad_start|>", "<|quad_end|>", "<|vision_start|>",
    #     "<|vision_end|>", "<|vision_pad|>", "<|image_pad|>", "<|video_pad|>"
    # ]
    # stop_token_ids = [tokenizer.convert_tokens_to_ids(tok) for tok in stop_tokens if tok in tokenizer.get_vocab()]

    # 3. 디바이스 docs 추출
    with open(os.path.join(root_dir,"resources","service_list_ver1.1.9.txt"), "r", encoding="utf-8") as f:
        service_doc = f.read()
    device_classes = extract_classes_by_name(service_doc)

    # 4. 문법 규칙 불러오기
    with open(os.path.join(root_dir, "resources", "grammar_ver1_1_10.txt"), "r", encoding="utf-8") as f:
        grammar_rules = f.read()

    # 4. 임베딩 및 문장 유사도 모델 - 첫 실행 시 다운로드에 시간이 소요됨
    embed_model = BGEM3FlagModel(os.path.join(root_dir, "resources", "models", "bge-m3"), use_fp16=False, local_files_only=True)
    sim_model = SentenceTransformer(os.path.join(root_dir, "resources", "models", "bge-m3"))

    # 5. 임베딩 데이터 로드
    paths = {
        'dense': os.path.join(root_dir, 'resources', 'embedding_result', 'dense_embeddings.npy'),
        'colbert': os.path.join(root_dir, 'resources', 'embedding_result', 'colbert_embeddings.pkl'),
        'sparse': os.path.join(root_dir, 'resources', 'embedding_result', 'sparse_embeddings.json'),
        'meta': os.path.join(root_dir, 'resources', 'embedding_result', 'metadata.json'),
    }

    # 데이터 로드
    dense_embeddings = np.load(paths['dense'])
    with open(paths['colbert'], 'rb') as f:
        colbert_embeddings = pickle.load(f)
    with open(paths['sparse'], encoding='utf-8') as f:
        sparse_embeddings = json.load(f)
    with open(paths['meta'], encoding='utf-8') as f:
        metadata = json.load(f)
    
    embedding_data = {
        'dense': dense_embeddings,
        'colbert': colbert_embeddings,
        'sparse': sparse_embeddings,
        'metadata': metadata
    }

    return {
        "model": model,
        "tokenizer": tokenizer,
        "stop_token_ids": [],
        "embed_model": embed_model,
        "embedding_data": embedding_data,
        "sim_model": sim_model,
        "device_classes": device_classes,
        "grammar": grammar_rules
    }

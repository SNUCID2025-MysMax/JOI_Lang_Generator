import os, re
import numpy as np
import json
import pickle
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from app.config import settings
from FlagEmbedding import BGEM3FlagModel

# 서비스 문서 파싱 함수
def extract_classes_by_name(text: str):
    pattern = r'Device\s+(\w+)\s*:\s*\n\s+"""(.*?)"""'
    matches = re.finditer(pattern, text, re.DOTALL)
    return {match.group(1): match.group(0) for match in matches}

def load_all_resources(model_name: str):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(base_dir, ".."))

    client = OpenAI(api_key=settings.openAiAPI)

    # 2. tokenizer 설정
    stop_token_ids = []

    # 3. 디바이스 docs 추출
    with open(os.path.join(root_dir,"resources","service_list_ver1.1.8.txt"), "r") as f:
        service_doc = f.read()
    device_classes = extract_classes_by_name(service_doc)

    # 4. 문법 규칙 불러오기
    with open(os.path.join(root_dir, "resources", "grammar_ver1_1_8.txt"), "r") as f:
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
        "model": client,
        "tokenizer": None,
        "stop_token_ids": stop_token_ids,
        "embed_model": embed_model,
        "embedding_data": embedding_data,
        "sim_model": sim_model,
        "device_classes": device_classes,
        "grammar": grammar_rules
    }
# model_loader.py
import unsloth
import os, re
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
    base_dir = os.path.dirname(os.path.abspath(__file__))  # services/ 경로
    root_dir = os.path.abspath(os.path.join(base_dir, ".."))  # 프로젝트 루트

    model_base_path = os.path.join(root_dir, "models", f"{model_name}-model")
    adapter_path = os.path.join(root_dir, "models", f"{model_name}-adapter")

    # 1. 모델 로딩
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_base_path,
        max_seq_length=4096,
        dtype=None,
        load_in_4bit=True,
    )
    model.load_adapter(adapter_path)
    FastLanguageModel.for_inference(model)

    # 2. tokenizer 설정
    stop_tokens = []

    if model_name == "codegemma":
        tokenizer = get_chat_template(tokenizer, chat_template="chatml", map_eos_token=True)
        tokenizer.add_bos_token = False
        stop_tokens = [
            "<|im_end|>", "<|file_separator|>", "<|fim_prefix|>", "<|fim_middle|>", "<|fim_suffix|>"
        ]
        stop_token_ids = [tokenizer.convert_tokens_to_ids(tok) for tok in stop_tokens if tok in tokenizer.get_vocab()]
    elif model_name == "qwenCoder":
        tokenizer = get_chat_template(tokenizer, chat_template="chatml", map_eos_token=True)
        tokenizer.add_bos_token = False
        stop_tokens = [
            "<|im_end|>", "<|endoftext|>", "<|file_sep|>", "<|fim_prefix|>", "<|fim_middle|>", "<|fim_suffix|>",
            "<|fim_pad|>", "<|repo_name|>", "<|im_start|>", "<|object_ref_start|>", "<|object_ref_end|>",
            "<|box_start|>", "<|box_end|>", "<|quad_start|>", "<|quad_end|>", "<|vision_start|>",
            "<|vision_end|>", "<|vision_pad|>", "<|image_pad|>", "<|video_pad|>"
        ]
        stop_token_ids = [tokenizer.convert_tokens_to_ids(tok) for tok in stop_tokens if tok in tokenizer.get_vocab()]
    elif model_name == "gemma3":
        tokenizer = get_chat_template(tokenizer, chat_template="gemma-3")
        tokenizer.add_bos_token = False
        stop_tokens = ["<end_of_turn>"]
        stop_token_ids = [tokenizer.tokenizer.convert_tokens_to_ids(token) for token in stop_tokens if token in tokenizer.tokenizer.get_vocab()]

    # 3. 디바이스 클래스 추출
    with open(os.path.join(root_dir,"resources","service_list_ver1.1.8.txt"), "r") as f:
        service_doc = f.read()
    device_classes = extract_classes_by_name(service_doc)

    # 4. 문법 규칙 읽기
    with open(os.path.join(root_dir, "resources", "grammar_ver1_1_5.txt"), "r") as f:
        grammar_rules = f.read()

    # 4. 임베딩 및 문장 유사도 모델
    embed_model = BGEM3FlagModel(os.path.join(root_dir, "models", "bge-m3"), use_fp16=False, local_files_only=True)
    # sim_model = SentenceTransformer("paraphrase-MiniLM-L6-v2")
    sim_model = SentenceTransformer(os.path.join(root_dir, "models", "paraphrase-MiniLM-L6-v2"))

    return {
        "model": model,
        "tokenizer": tokenizer,
        "stop_token_ids": stop_token_ids,
        "embed_model": embed_model,
        "sim_model": sim_model,
        "device_classes": device_classes,
        "grammar": grammar_rules
    }

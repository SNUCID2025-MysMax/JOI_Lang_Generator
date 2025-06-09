import os
from sentence_transformers import SentenceTransformer
from huggingface_hub import snapshot_download

# 모델을 저장할 디렉토리 설정
root_dir = os.getcwd()
models_dir = os.path.join(root_dir, "app", "resources", "models")
os.makedirs(models_dir, exist_ok=True)

def download_models():
    # 1. Unsloth Qwen2.5-Coder-7B 모델 다운로드
    print("Downloading Qwen2.5-Coder-7B model...")
    qwen_model_path = os.path.join(models_dir, "qwenCoder-model")
    
    if not os.path.exists(qwen_model_path):
        try:
            snapshot_download(
                # repo_id="unsloth/Qwen2.5-Coder-7B-bnb-4bit",
                repo_id="unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit",
                local_dir=qwen_model_path,
                local_dir_use_symlinks=False
            )
            print("✓ Qwen2.5-Coder-7B 다운로드 완료")
        except Exception as e:
            print(f"✗ Qwen 모델 다운로드 실패: {e}")
    else:
        print("✓ Qwen2.5-Coder-7B 이미 존재함")

    
    # 2. BGE-M3 모델 다운로드
    print("Downloading BGE-M3 model...")
    bge_model_path = os.path.join(models_dir, "bge-m3")
    
    if not os.path.exists(bge_model_path):
        try:
            snapshot_download(
                repo_id="BAAI/bge-m3",
                local_dir=bge_model_path,
            )
            print("✓ BGE-M3 다운로드 완료")
        except Exception as e:
            print(f"✗ BGE-M3 모델 다운로드 실패: {e}")
    else:
        print("✓ BGE-M3 이미 존재함")
    
    # 3. Sentence Transformer 모델 다운로드
    print("Downloading paraphrase-MiniLM-L6-v2 model...")
    sentence_model_path = os.path.join(models_dir, "paraphrase-MiniLM-L6-v2")
    
    if not os.path.exists(sentence_model_path):
        try:
            temp_model = SentenceTransformer('sentence-transformers/paraphrase-MiniLM-L6-v2')
            temp_model.save(sentence_model_path)
            print("✓ paraphrase-MiniLM-L6-v2 다운로드 완료")
        except Exception as e:
            print(f"✗ SentenceTransformer 모델 다운로드 실패: {e}")
    else:
        print("✓ paraphrase-MiniLM-L6-v2 이미 존재함")
    
    # # 4. 어댑터 다운로드
    # print("Downloading adapter from endermaru/mysmax...")
    # adapter_path = os.path.join(models_dir, "qwenCoder-adapter")
    # if not os.path.exists(adapter_path): 
    #     try:
    #         snapshot_download(
    #             repo_id="endermaru/mysmax",
    #             local_dir=adapter_path,
    #         )
    #         print("✓ 어댑터 다운로드 완료")
    #     except Exception as e:
    #         print(f"✗ 어댑터 다운로드 실패: {e}")
    # else:
    #     print("✓ 어댑터 이미 존재함")

if __name__ == "__main__":
    print("모델 다운로드 및 로드를 시작합니다...")
    print(f"모델 저장 경로: {models_dir}")
    
    download_models()
    
    print(f"\n모든 작업 완료. 모델들이 {models_dir}에 저장되었습니다.")
    print("다음번에는 로컬 파일에서 직접 로드됩니다.")

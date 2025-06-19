# JOI Lang Generator

[🔗 GitHub Repository 링크](https://github.com/SNUCID2025-MysMax/JOI_Lang_Generator)

JOI Lang Generator는 자연어 명령을 기반으로 IoT 장치 제어 시나리오 코드를 자동 생성하는 시스템입니다. NVIDIA GPU와 Docker가 설치된 Linux 환경에서 실행 및 테스트되었으며, FastAPI 서버를 통해 사용자 명령에 따라 GPT 또는 경량화된 sLLM 기반 파이프라인을 호출합니다.

---

## 🛠️ 환경 요구사항

- Linux (Ubuntu 권장)
- NVIDIA GPU 및 드라이버
- [Docker](https://docs.docker.com/get-docker/)
- [NVIDIA Container Toolkit 설치 가이드](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)

---

## 📦 프로젝트 설치

### 1. 레포지토리 클론

```bash
git clone https://github.com/SNUCID2025-MysMax/JOI_Lang_Generator.git
cd JOI_Lang_Generator

```

### 2. API 키 발급

- [DeepL API 키](https://www.deepl.com/pro#developer) (✅ 필수)
- [OpenAI API 키](https://openai.com/index/openai-api/) (GPT 파이프라인 사용 시에만 필요)

### 3. `.env` 파일 설정

```bash
cp .env.example .env

```

`.env` 파일을 열어 아래 내용을 작성합니다:

```
deeplAPI=your_deepl_api_key_here
# GPT 기반 파이프라인을 사용할 경우에만 작성
openAiAPI=your_openai_api_key_here

```

※ `openAiAPI`는 선택 항목입니다.

---

## 🐳 Docker로 실행

### 1. Docker 이미지 빌드

```bash
docker build -t joi-generator .

```

### 2. 컨테이너 실행 및 쉘 진입

```bash
docker run -p 8000:8000 -it --gpus all --name joi-generator -v $(pwd):/app joi-generator /bin/bash

```

### 3. GPU 사용 확인

컨테이너 내부에서 다음 명령어 입력:

```bash
nvidia-smi

```

---

## 📥 모델 다운로드

컨테이너 내부에서 실행:

```bash
python download_models.py

```

- [unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit](https://huggingface.co/unsloth/Qwen2.5-Coder-7B-Instruct-bnb-4bit) (5.2GB)
- [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) (4.3GB)
- [Fine-tuned adapter](https://huggingface.co/endermaru/mysmax) (324MB)

※ 다운로드는 최초 1회만 필요하며, 시간이 다소 소요될 수 있습니다.

---

## 🚀 서버 실행

FastAPI 서버는 다음 두 가지 방식 중 선택하여 실행할 수 있습니다.

### GPT 기반 파이프라인

```bash
python -m uvicorn app.main_gpt:app --host=0.0.0.0 --port=8000

```

### sLLM 기반 파이프라인 (경량화 모델)

```bash
python -m uvicorn app.main:app --host=0.0.0.0 --port=8000

```

---

## 🌐 사용 방법

서버 실행 후 브라우저에서 [http://localhost:8000/](http://localhost:8000/)에 접속하여 GUI를 통해 테스트할 수 있습니다. 
(ec2 서버는 퍼블릭 DNS로 접근 가능)

사용자 명령어와 연결된 디바이스, 현재 시간을 넣어 코드 생성을 호출할 수 있습니다. 연결된 디바이스 정보가 없을 경우, 스마트팜의 기본 Thing이 자동 적용됩니다.


연결된 디바이스 예시:

```json
{
  "sentence": "거실 조명 켜줘",
  "things": {
    "virtual_light_livingroom_1": {
      "id": "virtual_light_livingroom_1",  // 생략 가능
      "nick_name": "거실 조명 1",           // 생략 가능
      "category": "Light",                 // 디바이스 종류
      "tags": [                            // 태그 목록 - 디바이스 태그는 필수
        "Light",
        "livingroom"
      ]
    }
  }
}

```


---

## 📁 리소스 파일

- 기본 Thing 정보: `app/resources/things_smart_farm.json`
- 디바이스 서비스 목록: `app/resources/service_list_ver1.1.8.txt`
- 문법 프롬프트: `app/resources/grammar_ver1_1_8.txt`
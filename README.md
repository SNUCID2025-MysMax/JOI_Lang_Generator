# docker 없이 실행
- `python3 -m venv venv` : 가상환경 준비
- `source venv/bin/activate` : 가상환경 진입
- `pip install --no-cache-dir -r requirements_gpt.txt` : 필요 패키지 설치

# 모델 로드
- OpenAI GPT-4 버전
`$ python download_models_gpt.py`

# 서버 실행
- OpenAI GPT-4 버전
`python -m uvicorn app.main_gpt:app --host=0.0.0.0 --port=8000`

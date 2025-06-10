# docker 이미지 빌드
docker build -t fastapi-dev .

# docker 컨테이너 실행
docker run -p 8000:8000 -it --gpus all --name joi-generator -v $(pwd):/app fastapi-dev /bin/bash

# 모델 로드
JOI_Lang_Generator 디렉토리에서
`$ python download_models.py`

# 서버 실행
`python -m uvicorn app.main:app --host=0.0.0.0 --port=8000`

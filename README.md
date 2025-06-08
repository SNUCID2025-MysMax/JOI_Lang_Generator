docker build -t fastapi-dev .
docker run -p 8000:8000 -it --gpus all --name joi-generator -v $(pwd):/app fastapi-dev /bin/bash
python -m uvicorn app.main:app --host=0.0.0.0 --port=8000

docker start -ai joi-generator
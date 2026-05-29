FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir fastapi uvicorn pydantic paho-mqtt

COPY src/main.py .
COPY src/executor.py .
COPY open-webui-tool.py .
COPY workspace-tools.py .
COPY mqtt-tools.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

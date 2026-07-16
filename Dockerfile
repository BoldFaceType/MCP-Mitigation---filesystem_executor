FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOMECMD_HOST=127.0.0.1 \
    HOMECMD_PORT=8000

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir . \
    && addgroup --system homecmd \
    && adduser --system --ingroup homecmd --home /home/homecmd homecmd \
    && mkdir -p /home/homecmd/.homecmd \
    && chown -R homecmd:homecmd /home/homecmd

USER homecmd

EXPOSE 8000

CMD ["homecmd-agent"]

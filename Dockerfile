FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/shelfpath-venv

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

CMD ["/opt/shelfpath-venv/bin/uvicorn", "app:app", "--reload", "--host", "0.0.0.0", "--port", "8731"]

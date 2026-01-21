FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir -U pip

# pyproject만으로 설치 가능하게 구성
COPY pyproject.toml ./
COPY src ./src

# editable install (src 구조 안정)
RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "sentinelops.main:app", "--host", "0.0.0.0", "--port", "8000"]

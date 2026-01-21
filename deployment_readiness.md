# v0.9 – Deployment Readiness (Non-Docker)

목표:
처음 보는 사람이 10분 안에 SentinelOps를 로컬에서 실행하고 데모 흐름을 확인할 수 있는 상태

---

## A Local Quickstart (Non-Docker) — 최종 정리본

Prerequisites
    Python 3.10+
    PostgreSQL (local)
    PowerShell (Windows 기준)

1) Clone & Environment Setup
    git clone <repo-url>
    cd SentinelOps
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -e .

2) Environment Variables
    .env.example을 복사하여 .env 생성 후 값 설정:

    ENV=local

    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=sentinelops
    DB_USER=postgres
    DB_PASSWORD=your_password_here

    SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx/yyy/zzz

    * Optional (AI)

    OPENAI_API_KEY=sk-xxx
    AI_SUMMARY_MODEL=gpt-4o-mini
    AI_SUMMARY_TIMEOUT_SEC=12

    ⚠️ AI 설정은 선택 사항
    AI가 없어도 시스템은 정상 동작한다.

3) Initialize Database
    python -m sentinelops.scripts.init_db

    기대 결과:
    ✅ DB tables created

4) Run API Server
    uvicorn sentinelops.main:app --reload --app-dir src

5) Health Check
    iwr "http://127.0.0.1:8000/api/v1/health" -UseBasicParsing

    Expected:
    {"status":"ok"}

## B Demo Scenario — SentinelOps Lifecycle

목적
SentinelOps가 “탐지 → 운영자 확인 → 처리 → 요약” 흐름을 지원함을 시연한다.

1) Seed Demo Anomalies
    python -m sentinelops.scripts.seed_demo_anomalies


    [demo] prefix가 붙은 anomaly 생성

    이미 존재하면 중복 생성하지 않음 (idempotent)

2) View Open Demo Anomalies
    iwr "http://127.0.0.1:8000/api/v1/anomalies?only_open=true&demo_only=true&sort=severity_desc" `
    -UseBasicParsing | ConvertFrom-Json

3) Acknowledge an Anomaly
    $body = '{"status":"acknowledged"}'
    iwr -Method Patch "http://127.0.0.1:8000/api/v1/anomalies/{id}" `
    -ContentType "application/json" `
    -Body $body `
    -UseBasicParsing

4) Resolve the Anomaly
    $body = '{"status":"resolved"}'
    iwr -Method Patch "http://127.0.0.1:8000/api/v1/anomalies/{id}" `
    -ContentType "application/json" `
    -Body $body `
    -UseBasicParsing

    잘못된 상태 전이는 409 Invalid status transition 반환
    No-op 변경도 차단됨 (resolved → resolved)

5) Run Daily Summary (AI Optional)
    python -m sentinelops.scripts.run_daily_summary

    AI 성공 시: used_ai=True
    AI 실패 시에도 summary는 항상 전달됨
    중복 실행 시 자동 skip 처리됨

## C Seed Script 설명 (Demo 안정성)

seed_demo_anomalies.py 설계 원칙

목적: 데모용 anomaly 상태를 빠르게 재현

특징:
    [demo] prefix로 실데이터와 명확히 구분
    동일 rule_code에 대해 open anomaly가 있으면 재사용
    운영 데이터에 영향 없음
    여러 번 실행해도 안전 (idempotent)
    Demo 전용 필터

API 쿼리 파라미터:
    demo_only=true

동작:
    title 또는 rule_code 기준 [demo] anomaly만 반환
    실제 운영 anomaly와 시각적으로 분리 가능
    데모 화면이 깔끔해짐

---

## Docekr - Initialize DB (first run only)

docker compose up -d --build
docker compose exec api python -m sentinelops.scripts.init_db

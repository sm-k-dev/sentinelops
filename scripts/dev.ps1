docker compose up -d --build
docker compose exec api python -m sentinelops.scripts.init_db
docker compose exec api python -m sentinelops.scripts.seed_demo_anomalies

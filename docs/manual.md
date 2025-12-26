# Western NLP Service - Comprehensive Manual

**Version:** 1.0.0 — Microservices Edition

Live: https://western-nlp.ddns.net/docs

---

## Quick links
- Swagger UI: https://western-nlp.ddns.net/docs  
- Metrics / Host dashboards: https://western-nlp.ddns.net/metrics

---

# 1. Architecture Overview
Complete technical reference for the Microservices NLP Platform.

**Infrastructure**: AWS EC2 (Ubuntu) + Docker Compose

| Service | Container name | Port (internal) | Role |
|---|---:|---:|---|
| Nginx | `nginx-proxy` | 80, 443 | Reverse proxy, SSL termination, ingress |
| NLP App | `nlp-app` | 8000 | FastAPI app — ML inference (DistilBERT, Helsinki) |
| Archiver | `archiver` | - | Background worker — moves logs from Redis → S3 |
| Redis | `redis-db` | 6379 | In-memory storage for recent logs/cache |
| Prometheus | `prometheus` | 9090 | Metrics collector (scrapes `nlp-app:8000/metrics`) |
| Alertmanager | `alertmanager` | 9093 | Handles alerts (Telegram) |
| Grafana | `grafana` | 3000 | Dashboards for metrics |

---

# 2. Configuration (.env)
Create a `.env` in repo root (DO NOT commit). Example production template:

```
# AWS (S3 archiver)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJal...
S3_BUCKET_NAME=western-nlp-logs-archive

# Infra
REDIS_HOST=redis-db
REDIS_PORT=6379
EC2_HOST=Your_Public_IP
EC2_USER=ubuntu

# MLOps / Monitoring
WANDB_API_KEY=...
TELEGRAM_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=987654321
```

---

# 3. Deployment & CI/CD

**Automatic (GitHub Actions)**:
1. Push to `main`.
2. CI: lint, Bandit security scan, unit tests (pytest).
3. CD: SSH to EC2, create `.env` from GH Secrets, `git pull`, rebuild: `docker compose up -d --build`, prune unused images.

**Manual (Emergency)**:
```bash
ssh ubuntu@western-nlp.ddns.net
cd nlp-inference-service
git pull origin main
docker compose up -d --build
```

---

# 4. Monitoring & Alerts

**Dashboards**
- Grafana: `http://<HOST>:3000` — "NLP Services Metrics"
- Prometheus: `http://<HOST>:9090/targets` — verify all targets UP

**Alert rules** in `prometheus/alert_rules.yml` — example:
| Alert | Condition | Severity | Action |
|---|---|---|---|
| InstanceDown | `up == 0` for > 1m | Critical | Telegram immediate alert |

---

# 5. Data Archiving (Hot/Cold)
**Flow**
1. App writes logs to Redis list `api_logs` (hot path).  
2. Redis keeps last ~1000 items (LTRIM).  
3. `archiver` runs every minute (configurable).  
4. Archiver atomically renames `api_logs` → `logs_to_upload`, reads JSON, uploads `nlp_logs_{TIMESTAMP}.json` to S3, then deletes the list from Redis.

Example check (from host):
```bash
docker exec -it archiver python -c "import boto3, os; print(boto3.client('s3').list_objects(Bucket=os.getenv('S3_BUCKET_NAME')).get('Contents', 'Empty'))"
```

---

# Incident Response Playbooks

## Scenario 1 — 502 Bad Gateway
**Symptoms:** Nginx error page. `InstanceDown` alert.  
**Diagnosis:** Nginx cannot reach `nlp-app:8000`.  
**Steps:**
```bash
# Check containers
docker compose ps
# If app ok, restart nginx
docker restart nginx-proxy
# If app exited, inspect logs
docker logs nlp-app --tail 50
```

## Scenario 2 — Redis memory high
**Symptoms:** Redis rejects writes, API 500 on logging.  
**Cause:** Archiver failed to drain Redis.  
**Steps:**
```bash
docker logs archiver
# Emergency manual flush (data loss risk)
docker exec -it redis-db redis-cli DEL api_logs
```

## Scenario 3 — SSL certificate expired
```bash
docker stop nginx-proxy
sudo certbot renew
docker start nginx-proxy
```

---

# 6. Maintenance Tasks

**Redis snapshot**
```bash
# Trigger save
docker exec redis-db redis-cli BGSAVE

# Copy to host
docker cp redis-db:/data/dump.rdb ./backup_dump.rdb
```

**Cleaning Docker**
```bash
docker system prune -a -f
```

---

# API Usebook (Client Guide)

**Base URL:** `https://western-nlp.ddns.net`  
**Docs (Swagger):** `/docs`

## POST /sentiment
Analyze tone. Limits: max 1000 characters.
**Request example:**
```http
POST /sentiment
Content-Type: application/json

{ "text": "The service quality is outstanding!" }
```
**Response (200):**
```json
{ "result": [ { "label": "POSITIVE", "score": 0.9998 } ] }
```
Model: `distilbert-base-uncased-finetuned-sst-2-english`

## POST /translate
English → French (model: `Helsinki-NLP/opus-mt-en-fr`)
**Request:** `{ "text": "Hello world" }`  
**Response:** `{ "translated_text": "Bonjour le monde" }`

## GET /history
Returns last 10 processed requests from cache. Example item:
```json
{
  "timestamp": "2025-12-26 10:00:00",
  "task": "SENTIMENT",
  "input": "test",
  "result": "POSITIVE"
}
```

## Error Codes
| Code | Meaning | Solution |
|---:|---|---|
| 422 | Validation error | Ensure `text` exists and < 1000 chars |
| 502 | Bad Gateway | Server restarting or down; check containers |
| 500 | Internal Server Error | ML model failure — inspect app logs |

---

# Developer Guide

## Project structure
```
.
├── app/                  # FastAPI Application (Microservice 1)
│   ├── main.py
│   └── Dockerfile
├── archiver/             # S3 uploader (Microservice 2)
│   ├── main.py
│   └── Dockerfile
├── docker-compose.yml
├── nginx/
├── prometheus/
└── tests/
```

## Local setup (without AWS)
```bash
git clone https://github.com/Western-1/nlp-inference-service
echo "REDIS_HOST=redis-db" > .env
docker compose up --build
```

## Testing
Use `pytest` and mocks for Redis/S3. Example:
```bash
pip install -r app/requirements.txt -r archiver/requirements.txt
PYTHONPATH=.:./app:./archiver pytest tests/ -v
```

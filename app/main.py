import os
import json
import asyncio
from datetime import datetime
from typing import Any

import redis
import wandb
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import pipeline
from prometheus_fastapi_instrumentator import Instrumentator

REDIS_HOST = os.getenv("REDIS_HOST", "redis-db")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", 1000))

WANDB_KEY = os.getenv("WANDB_API_KEY")

app = FastAPI(title="NLP Microservice with Redis")

Instrumentator().instrument(app).expose(app)

_models = {}
_wandb_inited = False

def get_redis() -> redis.Redis:
    """Factory to get redis client. Tests should patch this."""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

async def get_model(task_name: str, model_name: str):
    """
    Loads the model only when needed for the first time (Lazy Loading).
    Kept async-friendly by running pipeline in executor.
    """
    if task_name not in _models:
        print(f"Loading model for {task_name}...")
        loop = asyncio.get_running_loop()
        _models[task_name] = await loop.run_in_executor(
            None, 
            lambda: pipeline(task_name, model=model_name)
        )
        print(f"Model {task_name} loaded!")
    return _models[task_name]

class APIInput(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, title="Input text", description="Text to analyze/translate")

def save_log(task: str, text: str, result: Any):
    """Save a log to Redis using factory get_redis."""
    try:
        r = get_redis()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_data = {
            "timestamp": timestamp,
            "task": task,
            "input": text,
            "result": str(result)
        }
        r.lpush("api_logs", json.dumps(log_data))
        r.ltrim("api_logs", 0, HISTORY_LIMIT - 1)
    except Exception as e:
        print(f"Redis log error: {e}")

@app.on_event("startup")
async def startup_event():
    """Initialize heavier external integrations (W&B) on startup — not at import time."""
    global _wandb_inited
    if WANDB_KEY:
        try:
            wandb.login(key=WANDB_KEY)
            wandb.init(
                project="nlp-inference-service",
                name="production-model-v1",
                config={
                    "model": "distilbert-base-uncased",
                    "framework": "fastapi",
                    "environment": "production"
                }
            )
            _wandb_inited = True
            print("Connected to Weights & Biases")
        except Exception as e:
            print(f"W&B Connection failed: {e}")

@app.get("/")
def home():
    """Health check — also returns Redis connectivity status by ping."""
    try:
        r = get_redis()
        db_ok = False
        try:
            db_ok = r.ping()
        except Exception:
            db_ok = False
        db_status = "Connected to Redis" if db_ok else "Redis unavailable"
        return {"status": "Online & Monitored with W&B", "db_status": db_status}
    except Exception as e:
        return {"status": "Online", "db_status": f"Error: {e}"}

@app.get("/history")
def get_history():
    try:
        r = get_redis()
        logs = r.lrange("api_logs", 0, 9)
        return [json.loads(log) for log in logs]
    except Exception as e:
        return {"error": str(e)}

@app.post("/sentiment")
async def predict_sentiment(data: APIInput):
    model = await get_model("sentiment-analysis", "distilbert-base-uncased-finetuned-sst-2-english")
    result = model(data.text)
    
    label = result[0]['label']
    score = result[0]['score']

    save_log("SENTIMENT", data.text, result)

    if _wandb_inited:
        try:
            wandb.log({
                "input_text": data.text,
                "prediction": label,
                "confidence": score,
                "text_length": len(data.text)
            })
        except Exception as e:
            print(f"W&B log error: {e}")

    return {"result": result}

@app.post("/translate")
async def translate_text(data: APIInput):
    model = await get_model("translation_en_to_fr", "Helsinki-NLP/opus-mt-en-fr")
    result = model(data.text)
    translated_text = result[0].get('translation_text') or result[0].get('translation', '')
    save_log("TRANSLATION", data.text, translated_text)
    return {"translated_text": translated_text}

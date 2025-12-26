import os
import json
import time
import redis
import boto3
import schedule
from datetime import datetime
from typing import Any

REDIS_HOST = os.getenv("REDIS_HOST", "redis-db")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def get_redis() -> redis.Redis:
    """Factory for redis client — useful to mock in tests."""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

def get_s3_client() -> Any:
    """Factory for boto3 s3 client — useful to mock in tests."""
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )

def archive_logs():
    """Fetch logs from Redis, write json file, upload to S3, cleanup."""
    print(f"[{datetime.now()}] Checking Redis for available logs...")
    try:
        r = get_redis()
        s3 = get_s3_client()
        if r.exists("api_logs"):
            r.rename("api_logs", "logs_to_upload")
            logs = r.lrange("logs_to_upload", 0, -1)
            
            if logs:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"nlp_logs_{timestamp}.json"
                data = [json.loads(log) for log in logs]
                
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
                
                print(f"Uploading {filename} to S3 bucket: {BUCKET_NAME}")
                s3.upload_file(filename, BUCKET_NAME, filename)
                
                r.delete("logs_to_upload")
                try:
                    os.remove(filename)
                except OSError:
                    pass
                print(f"Successfully archived {len(logs)} records.")
            else:
                print("No logs after rename.")
                r.delete("logs_to_upload")
        else:
            print("No new logs found in Redis.")
            
    except Exception as e:
        print(f"Archiving error: {e}")

def run_archiver_loop(interval_seconds: int = 60):
    """Start the schedule loop. Separated so tests can import archive_logs safely."""
    schedule.every(interval_seconds).seconds.do(archive_logs)
    print("Archiver service started. Waiting for scheduled tasks...")
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("Archiver stopped.")

if __name__ == "__main__":
    run_archiver_loop(60)

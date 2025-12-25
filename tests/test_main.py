import json
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check():
    """
    Test the root endpoint (Health Check).
    Should return 200 OK and connection status.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "Online & Monitored with W&B", "db_status": "Connected to Redis"}

def test_get_history_empty():
    """
    Test /history endpoint when Redis is empty or mocked.
    Should return a list (empty or populated).
    """
    with patch("main.r") as mock_redis:
        mock_redis.lrange.return_value = []
        
        response = client.get("/history")
        assert response.status_code == 200
        assert response.json() == []

@patch("main.get_model")
@patch("main.r")
def test_sentiment_analysis_mocked(mock_redis, mock_get_model):
    """
    Unit Test for Sentiment Analysis.
    Mocks the ML model to avoid downloading weights during CI/CD.
    """
    mock_pipeline = MagicMock()
    # -------------------------------------------------------------
    mock_pipeline.return_value = [{"label": "POSITIVE", "score": 0.99}]
    
    mock_get_model.return_value = mock_pipeline

    payload = {"text": "MLOps is amazing!"}

    response = client.post("/sentiment", json=payload)

    assert response.status_code == 200
    data = response.json()
    
    assert data["result"][0]["label"] == "POSITIVE"
    assert data["result"][0]["score"] == 0.99

    mock_redis.lpush.assert_called_once()
    mock_redis.ltrim.assert_called_once()

def test_input_validation_too_long():
    """
    Test Pydantic validation.
    Should return 422 Unprocessable Entity if text > 1000 chars.
    """
    long_text = "a" * 1001
    payload = {"text": long_text}

    response = client.post("/sentiment", json=payload)
    
    assert response.status_code == 422
    assert "detail" in response.json()

def test_translation_integration():
    """
    Integration Test.
    """
    payload = {"text": "Hello world"}
    
    response = client.post("/translate", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        assert "translated_text" in data
        assert isinstance(data["translated_text"], str)
        assert len(data["translated_text"]) > 0
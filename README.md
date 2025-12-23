# Sentiment Analysis Service

![Python Version](https://img.shields.io/badge/python-3.9-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Docker](https://img.shields.io/badge/docker-supported-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)

A containerized REST API microservice for real-time text sentiment analysis. This project leverages a pre-trained DistilBERT model from Hugging Face Transformers, served via FastAPI, and packaged with Docker for consistent deployment.

![Dashboard Overview](Images/1.png)

## Overview

The purpose of this service is to provide a lightweight, high-performance interface for Machine Learning inference. The application accepts text input and returns the predicted sentiment (POSITIVE/NEGATIVE) along with a confidence score.

**Key Features:**
- **Model:** `distilbert-base-uncased-finetuned-sst-2-english` (optimized for performance).
- **Framework:** FastAPI for asynchronous request handling and automatic OpenAPI generation.
- **Deployment:** Fully Dockerized application ensuring environment reproducibility.
- **Validation:** Strict data validation using Pydantic models.

## Tech Stack

- **Language:** Python 3.9-slim
- **ML Backend:** PyTorch, Transformers
- **Web Server:** Uvicorn, FastAPI
- **Containerization:** Docker

## Project Structure

```text
.
├── Dockerfile           # Docker build instructions
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
└── Images/              # Documentation assets
```

## Installation and Setup

### Local Development

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the server:**
   ```bash
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   The API will be available at `http://localhost:8000`.

### Docker Deployment (Recommended)

This project is optimized for containerized environments.

1. **Build the image:**
   ```bash
   docker build -t sentiment-analyzer .
   ```

2. **Run the container:**
   ```bash
   docker run -d -p 8000:8000 --name sentiment-app sentiment-analyzer
   ```

## API Documentation

The API comes with auto-generated interactive documentation available at `/docs`.

### 1. Health Check
**GET** `/`

Verifies that the API is online and ready to accept requests.

### 2. Predict Sentiment
**POST** `/predict`

Main inference endpoint. Analyzes the input text string.

**Request Parameters:**
The endpoint expects a JSON body with a `text` field.

![Request Parameters](Images/2.png)

**Example Request (Curl):**
```bash
curl -X 'POST' \
  'http://localhost:8000/predict' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "text": "The deployment process was incredibly smooth and efficient."
}'
```

**Example Response:**
The model returns the input text, the sentiment label, and the confidence score.

```json
{
  "input": "The deployment process was incredibly smooth and efficient.",
  "prediction": [
    {
      "label": "POSITIVE",
      "score": 0.9998
    }
  ]
}
```

![Response Example](Images/3.png)

### Data Validation
The API utilizes Pydantic schemas to validate incoming requests, ensuring data integrity before inference.

![Validation Schemas](Images/4.png)

### Author
Andriy Vlonha 

### Licence

**MIT License Copyright (c) 2025 [Andriy Vlonha]**
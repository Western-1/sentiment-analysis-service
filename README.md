# NLP Inference Microservice (Docker Compose & Redis)

![Python](https://img.shields.io/badge/python-3.9-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)
![Redis](https://img.shields.io/badge/redis-%23DD0031.svg?style=flat&logo=redis&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)
![HuggingFace](https://img.shields.io/badge/Models-HuggingFace-yellow.svg)

A production-ready **Microservices Architecture** for Natural Language Processing.  
This project orchestrates multiple containers using **Docker Compose**: a FastAPI application for inference and a **Redis** database for high-speed logging and persistence.

![Dashboard Overview](Images/1.png)

---

## Architecture & Workflow

This project demonstrates a modern microservices approach. Instead of a monolithic script, the system decouples inference from data persistence.

```mermaid
graph LR
  %% --- Styling Definitions ---
  %% Existing Components: Bold colors, solid lines
  classDef app fill:#e1f5fe,stroke:#0277bd,stroke-width:2px,color:#000
  classDef db fill:#ffcdd2,stroke:#c62828,stroke-width:2px,color:#000
  classDef ext fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000
  
  %% Planned Components: Grey, dashed lines, lighter text
  classDef planned fill:#fafafa,stroke:#9e9e9e,stroke-width:2px,stroke-dasharray: 5 5,color:#616161
  
  %% Network Boundaries
  classDef net fill:none,stroke:#546e7a,stroke-width:2px,stroke-dasharray: 5 5,color:#546e7a

  %% --- Actors ---
  User([User / Client])
  style User fill:#fff,stroke:#333,stroke-width:2px,color:#000

  %% --- Ingress Layer (Planned) ---
  subgraph Ingress [Ingress Layer]
    direction TB
    Nginx[Nginx Reverse Proxy]:::planned
  end

  %% --- Private Docker Network ---
  subgraph DockerNet [Private Docker Network]
    
    %% App Service
    subgraph Container_App [App Service]
      direction TB
      Gunicorn[Gunicorn Manager]:::app
      subgraph Workers [Async Workers]
        Uvicorn[Uvicorn Worker]:::app
        Logic[Lazy Load Logic]:::app
      end
    end

    %% Storage Service
    Redis[(Redis DB)]:::db
  end

  %% --- External / Cloud ---
  subgraph External [External Services]
    HF_Hub[HuggingFace Hub]:::ext
    HFCache[Volume: HF Cache]:::ext
    S3[(S3 Archive)]:::planned
    Prometheus[Metrics]:::planned
  end

  %% === Data Flow ===
  
  %% 1. Request Flow (Current vs Planned)
  User -->|"1. HTTPS Request"| Nginx
  Nginx -.->|"2. Forward (Planned)"| Gunicorn
  User -.->|"Direct Access (Current Dev)"| Gunicorn

  %% 2. Internal Processing
  Gunicorn -->|"3. Spawn Processes"| Uvicorn
  Uvicorn -->|"4. Inference"| Logic
  
  %% 3. Model Loading
  Logic -.->|"Download (First run)"| HF_Hub
  Logic -->|"Load from"| HFCache
  
  %% 4. Async Logging
  Uvicorn -->|"5. LPUSH (Async)"| Redis
  Redis -->|"LTRIM (Auto-cleanup)"| Redis
  
  %% 5. Read History
  User -->|"GET /history"| Uvicorn
  Uvicorn <-->|"LRANGE"| Redis

  %% 6. Future Monitoring
  Redis -.->|"Archive (Planned)"| S3
  Uvicorn -.->|"/metrics (Planned)"| Prometheus

  %% Apply Network Styles
  style DockerNet fill:none,stroke:#607d8b,stroke-width:2px,stroke-dasharray: 5 5
  style Ingress fill:none,stroke:none
  style External fill:none,stroke:none
  style Container_App fill:#f1f8e9,stroke:#558b2f,stroke-width:1px
  style Workers fill:#fff,stroke:none
```

### Key Features

- **Microservices Orchestration:** Fully dockerized environment via `docker-compose`
- **Multi-Model Inference:** `DistilBERT` (Sentiment) & `Helsinki-NLP` (Translation)
- **Persistent Storage:** Asynchronous logging to Redis
- **Request History:** Dedicated endpoint for audit and debugging
- **Strict Validation:** Pydantic schemas enforce type safety

---

## Tech Stack

- **Orchestration:** Docker Compose
- **Core:** Python 3.9, FastAPI, Uvicorn
- **Database:** Redis (Alpine)
- **ML Backend:** PyTorch, Transformers, SentencePiece
- **Models:**
  - `distilbert-base-uncased-finetuned-sst-2-english`
  - `Helsinki-NLP/opus-mt-en-fr`

---

## Project Structure

```
.
├── docker-compose.yml   # Service orchestration (App + Redis)
├── Dockerfile           # App container configuration
├── main.py              # Application logic & endpoints
├── requirements.txt     # Python dependencies
└── Images/              # Documentation assets
```

---

## Installation and Setup

### Prerequisites
- Docker Engine
- Docker Compose

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/Western-1/nlp-inference-service
cd nlp-inference-service
```

2. **Start the services**
```bash
docker-compose up --build
```

> [!NOTE]
> The first launch may take several minutes while ML models are downloaded from Hugging Face.

3. **Stop the system**
```bash
docker-compose down
```

---

## API Documentation

Interactive Swagger UI is available at: `http://localhost:8000/docs`

### 1. Health Check
`GET /` - Checks service status and Redis connection.

### 2. Request History
`GET /history` - Returns the last 10 requests stored in Redis.

```json
[
  {
    "timestamp": "2025-12-24 18:30:00",
    "task": "TRANSLATION",
    "input": "Hello",
    "result": "Bonjour"
  }
]
```

### 3. Sentiment Analysis
`POST /sentiment` -  Classifies text as **POSITIVE** or **NEGATIVE**.

**Request**
```json
{
  "text": "The deployment process was incredibly smooth."
}
```

**Response**
```json
{
  "result": [
    {
      "label": "POSITIVE",
      "score": 0.9998
    }
  ]
}
```

### 4. Translation (En → Fr)
`POST /translate`  
Translates English text to French.

**Request**
```json
{
  "text": "Hello world, this is a test."
}
```

**Response**
```json
{
  "translated_text": "Bonjour le monde, c'est un test."
}
```

![Translation Example](Images/2.png)

---

## Logging Architecture

Instead of synchronous file logging, the service uses **Redis Lists** as a high‑performance buffer.

1. __API__ receives a request  
2. Model generates a prediction  
3. Result is serialized to __JSON__ and pushed to `service_history`  
4. `/history` endpoint retrieves recent entries via `LRANGE`

![Logs Preview](Images/3.png)

---

## License

**MIT License**

Copyright (c) 2025 Andriy Vlonha

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

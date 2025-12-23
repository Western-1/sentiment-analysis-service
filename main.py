from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline

app = FastAPI()

print("Loading the model..")
model_name = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"
sentiment_pipeline = pipeline("sentiment-analysis", model=model_name)

class TextInput(BaseModel):
    text: str

@app.get("/")
def home():
    return {"status": "System is online", "message": "Go to /docs to test the model"}

@app.post("/predict")
def predict_sentiment(input_data: TextInput):
    result = sentiment_pipeline(input_data.text)
    return {"input": input_data.text, "prediction": result}

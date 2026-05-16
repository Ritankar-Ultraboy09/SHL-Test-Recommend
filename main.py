from fastapi import FastAPI
from agents.agent import process_chat

app = FastAPI()

with open("data/catalog_phase.json", "r", encoding="utf-8") as f:
    import json
    CATALOG = json.load(f)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/chat")
def chat(request:dict):
    messages = request.get("messages", [])
    if not messages:
        return {
            "reply": "Please send a message to get started.",
            "recommendations": [],
            "end_of_conversation": False
        }
    if messages[-1].get("role") != "user":
        return {
            "reply": "Last message must be from user.",
            "recommendations": [],
            "end_of_conversation": False
        }
    return process_chat(messages)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI

app = FastAPI(title="NaSCon 26 League Platform")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/ping")
def ping():
    return {"message": "pong"}

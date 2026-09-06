# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Depends
# pyrefly: ignore [missing-import]
from sqlalchemy import text
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from app.database import get_db

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/db-health")
def database_health(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT current_database();"))
    return {"database": result.scalar()}

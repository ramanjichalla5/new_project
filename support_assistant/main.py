"""FastAPI entry point. Start from repository root with uvicorn support_assistant.main:app."""
from contextlib import asynccontextmanager
import threading

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field, field_validator
from support_assistant.rag import Answer, Engine, mock_mode


class Question(BaseModel):
    query: str = Field(min_length=1, max_length=2000)

    @field_validator('query')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('query must contain non-whitespace text')
        return value.strip()


@asynccontextmanager
async def lifespan(app):
    app.state.engine = Engine()
    app.state.lock = threading.Lock()
    yield


app = FastAPI(title='Zepto Support Assistant', version='1.0.0', lifespan=lifespan)


@app.get('/')
def index():
    return {'service':'Zepto Support Assistant', 'docs':'/docs', 'health':'/health', 'ask':'POST /ask'}


@app.get('/health')
def health(request: Request):
    return {'status':'ok', 'documents':request.app.state.engine.collection.count(), 'mock_llm':mock_mode()}


@app.post('/ask', response_model=Answer)
def ask(question: Question, request: Request):
    # A small CPU demo: serialize embedding inference to bound memory under concurrent requests.
    with request.app.state.lock:
        return request.app.state.engine.ask(question.query)

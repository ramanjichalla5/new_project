"""Integration tests use the real MiniLM model and real Chroma collection."""
import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from support_assistant import rag
from support_assistant.main import app


@pytest.fixture(scope='module')
def client(tmp_path_factory):
    import os
    old = os.environ.get('CHROMA_PATH')
    os.environ['CHROMA_PATH'] = str(tmp_path_factory.mktemp('chroma'))
    os.environ['MOCK_LLM'] = '1'
    with TestClient(app) as test_client:
        yield test_client
    if old is None:
        os.environ.pop('CHROMA_PATH', None)
    else:
        os.environ['CHROMA_PATH'] = old


def test_real_retrieval_mock_generation_and_general_route(client, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('No LLM calls allowed in default mode')
    monkeypatch.setattr(rag, 'llm_json', forbidden)
    assert client.get('/health').json()['documents'] == 8
    policy = client.post('/ask', json={'query':'What is the standard delivery fee?'})
    assert policy.status_code == 200
    data = policy.json()
    assert data['sources'][0] == 'doc_01'
    assert len(data['sources']) == 3
    assert data['answer'].startswith('Based on the retrieved context: ')
    assert data['confidence'] == 1.0
    unrelated = client.post('/ask', json={'query':'What is two plus two?'}).json()
    assert unrelated == {'answer':rag.DIRECT,'sources':[],'confidence':1.0}
    assert client.post('/ask', json={'query':'   '}).status_code == 422
    assert client.post('/ask', json={'query':'x'*2001}).status_code == 422


@pytest.mark.parametrize('query,expected', [
    ('How long do refunds take?', 'doc_02'),
    ('What are the membership tiers?', 'doc_03'),
    ('How does live order tracking work?', 'doc_04'),
    ('Can I cancel an order after it is packed?', 'doc_05'),
    ('Refund for damaged or missing items and photo above INR 1000?', 'doc_06'),
    ('When do gift cards expire?', 'doc_07'),
    ('What are customer support hours?', 'doc_08')])
def test_all_policy_documents_retrievable(client, query, expected):
    data = client.post('/ask', json={'query':query}).json()
    assert expected in data['sources']


def test_real_llm_retries_and_terminal_failure(monkeypatch):
    monkeypatch.setenv('MOCK_LLM','0')
    monkeypatch.setenv('GROQ_API_KEY','test-placeholder')
    monkeypatch.setenv('GROQ_MODEL','test-placeholder')
    prompts = []
    payloads = iter(['not json', '{"answer":"missing fields"}',
                     json.dumps({'answer':'Valid','sources':[],'confidence':.5})])
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {'choices':[{'message':{'content':next(payloads)}}]}
    def fake_post(*args, **kwargs):
        prompts.append(kwargs['json']['messages'][0]['content'])
        return Response()
    monkeypatch.setattr(rag.httpx, 'post', fake_post)
    assert rag.llm_json('Prompt', rag.Answer).answer == 'Valid'
    assert len(prompts) == 3
    assert 'last response was invalid' in prompts[1]
    payloads = iter(['bad','bad','bad'])
    with pytest.raises(rag.GenerationError):
        rag.llm_json('Prompt', rag.Answer)
    with pytest.raises(ValidationError):
        rag.Answer(answer='Invalid', sources=[], confidence=2.0)

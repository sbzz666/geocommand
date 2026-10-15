from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .engine import Query, fixture, run

app = FastAPI(title='GeoCommand', version='0.1.0', description='Auditable spatial agent workflow on synthetic fixtures.')
STATIC = Path(__file__).parent / 'static'
app.mount('/static',StaticFiles(directory=STATIC),name='static')


@app.get('/')
def index():
    return FileResponse(STATIC/'index.html')


@app.get('/api/health')
def health():
    return {'status':'ok','version':'0.1.0','data':'synthetic'}


@app.get('/api/layers')
def layers():
    return fixture()


@app.post('/api/analyze')
def analyze(query: Query):
    try:
        return run(query)
    except ValidationError:
        raise HTTPException(422,'自然语言中的数值超出支持范围，请检查约束。') from None

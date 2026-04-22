from pathlib import Path
import sys

from fastapi import FastAPI

API_ROOT = Path(__file__).resolve().parent
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from routers import models, research

app = FastAPI(title='Wind Price Lab', version='0.1.0')

app.include_router(research.router)
app.include_router(models.router)


@app.get('/health')
def health():
    return {'status': 'ok'}

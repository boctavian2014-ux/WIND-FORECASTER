from pathlib import Path
import sys

from fastapi import FastAPI

API_ROOT = Path(__file__).resolve().parent
# Ensure apps/api is always first in sys.path so that bare imports like
# `from deps import get_db` and `from schemas.research import ...` resolve
# correctly regardless of how the module is loaded (e.g. as apps.api.main
# via PYTHONPATH=/app with uvicorn).
sys.path.insert(0, str(API_ROOT))

from routers import models, research

app = FastAPI(title='Wind Price Lab', version='0.1.0')

app.include_router(research.router)
app.include_router(models.router)


@app.get('/health')
def health():
    return {'status': 'ok'}

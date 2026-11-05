import os
import secrets
import warnings
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.middleware.sessions import SessionMiddleware
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.api.routes import router
from app.services.errors import DomainError

ROOT = Path(__file__).parent
secret = os.getenv('SECRET_KEY')
if os.getenv('VERCEL') and (not secret or secret.startswith('replace-') or len(secret) < 32):
    raise RuntimeError('Set a stable SECRET_KEY of at least 32 characters in Vercel.')
if not secret or secret.startswith('replace-'):
    secret = secrets.token_hex(32)
    warnings.warn('Using an ephemeral development session key. Set SECRET_KEY in .env for persistent sessions.')
app = FastAPI(title='DormTogether · DS 187', version='1.0.0')
app.add_middleware(SessionMiddleware, secret_key=secret, same_site='strict', https_only=bool(os.getenv('VERCEL')) or os.getenv('COOKIE_SECURE', 'false').lower() == 'true', max_age=28800)
app.include_router(router)
app.mount('/static', StaticFiles(directory=ROOT/'static'), name='static')
templates = Environment(loader=FileSystemLoader(ROOT/'templates'), autoescape=select_autoescape())

@app.middleware('http')
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    if not request.url.path.startswith(('/docs', '/redoc')):
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    response.headers['Cache-Control'] = 'no-store'
    return response

@app.exception_handler(IntegrityError)
async def integrity_error(request, exc):
    return JSONResponse(status_code=409, content={'detail': 'This change conflicts with existing data. Refresh and retry.'})

@app.exception_handler(OperationalError)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={'detail': 'Database unavailable or busy. Run migrations if this is a new installation, then retry.'})

@app.get('/', response_class=HTMLResponse)
def index():
    return templates.get_template('index.html').render()

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.exception_handler(DomainError)
async def domain_error(request, exc):
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})

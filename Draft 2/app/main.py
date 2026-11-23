import os
import secrets
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError, OperationalError
from starlette.middleware.sessions import SessionMiddleware
from app.api.routes import router

ROOT = Path(__file__).parent
app = FastAPI(title='Dormie', version='1.0.0')
app.add_middleware(SessionMiddleware, secret_key=os.getenv('SECRET_KEY') or secrets.token_hex(32), session_cookie='dormie_session', same_site='strict', https_only=os.getenv('COOKIE_SECURE') == '1', max_age=86400)

@app.middleware('http')
async def security(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        if origin and urlparse(origin).netloc != request.headers.get('host'):
            return JSONResponse({'detail': 'Cross-origin requests are not permitted.'}, status_code=403)
        if not request.url.path.endswith(('/complete', '/logout')) and 'application/json' not in request.headers.get('content-type', ''):
            return JSONResponse({'detail': 'Use application/json.'}, status_code=415)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.path.startswith('/api'):
        response.headers['Cache-Control'] = 'no-store'
    return response

@app.exception_handler(IntegrityError)
async def conflict(request, error):
    return JSONResponse({'detail': 'This change conflicts with an existing record. Refresh and retry.'}, status_code=409)

@app.exception_handler(OperationalError)
async def db_error(request, error):
    if getattr(error.orig, 'args', (None,))[0] in (1644, 3819):
        return JSONResponse({'detail': 'This change violates a database constraint.'}, status_code=409)
    return JSONResponse({'detail': 'Database unavailable. Check migrations or retry shortly.'}, status_code=503)

@app.exception_handler(RequestValidationError)
async def invalid(request, error):
    return JSONResponse({'detail': [{'field': '.'.join(str(x) for x in e['loc'][1:]), 'message': e['msg']} for e in error.errors()]}, status_code=422)

app.include_router(router)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
templates = Jinja2Templates(directory=ROOT / 'templates')

@app.get('/')
async def index(request: Request):
    return templates.TemplateResponse(request=request, name='index.html')

@app.get('/health')
def health():
    return {'status': 'ok'}

# app/main.py

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

# --- Import Routers ---
from .auth import router as auth_router
from .sim_api import router as sim_router
from .contact_router import router as contact_api_router # For contact form API
# from .config import settings # Uncomment if settings is used directly in main.py

app = FastAPI(title="Cyber Simulation Platform API")

# --- Mount Static Files ---
# Path relative to this file's location (app/main.py)
# Goes up one level to project root, then into 'static'
project_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(project_root_dir, 'static')

if not os.path.isdir(static_dir):
     print(f"WARNING: Static directory not found at {static_dir}. Expected at project_root/static/")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# --- Setup Templates ---
# HTML files are in the project root
template_dir = project_root_dir # Jinja2Templates will look for files relative to this
templates = Jinja2Templates(directory=template_dir)


# --- Include API Routers ---
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(sim_router, prefix="/api/sim", tags=["Simulation"])
app.include_router(contact_api_router, prefix="/api/contact", tags=["Contact"]) # Correctly included

# --- Health Check ---
@app.get("/api/health", tags=["System"])
async def health_check():
    return {"status": "ok"}

# --- Routes to Serve HTML Pages (Frontend Routes) ---
@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
async def serve_index_or_redirect(request: Request):
    index_html_path = os.path.join(template_dir, "index.html")
    if os.path.exists(index_html_path):
        return templates.TemplateResponse("index.html", {"request": request})
    else:
        print(f"INFO: index.html not found at {index_html_path}, redirecting to /simulation")
        return RedirectResponse(url="/simulation")

@app.get("/simulation", response_class=HTMLResponse, tags=["Frontend"])
async def serve_simulation_page(request: Request):
    simulation_html_path = os.path.join(template_dir, "simulation.html")
    if not os.path.exists(simulation_html_path):
        return HTMLResponse(content="<html><body><h1>Error</h1><p>simulation.html not found.</p></body></html>", status_code=404)
    return templates.TemplateResponse("simulation.html", {"request": request})

@app.get("/simulation-demo", response_class=HTMLResponse, tags=["Frontend"])
async def serve_simulation_demo(request: Request):
    demo_html_path = os.path.join(template_dir, "simulation-demo.html")
    if not os.path.exists(demo_html_path):
        return HTMLResponse(
            content="<html><body><h1>Error</h1><p>simulation-demo.html not found.</p></body></html>",
            status_code=404
        )
    return templates.TemplateResponse("simulation-demo.html", {"request": request})

@app.get("/privacy-policy", response_class=HTMLResponse, tags=["Frontend"])
async def serve_privacy_policy_page(request: Request):
    privacy_policy_html_path = os.path.join(template_dir, "privacy-policy.html")
    if not os.path.exists(privacy_policy_html_path):
        return HTMLResponse(content="<html><body><h1>Error</h1><p>privacy-policy.html not found.</p></body></html>", status_code=404)
    return templates.TemplateResponse("privacy-policy.html", {"request": request})

@app.get("/terms-of-service", response_class=HTMLResponse, tags=["Frontend"])
async def serve_terms_of_service_page(request: Request):
    terms_of_service_html_path = os.path.join(template_dir, "terms-of-service.html")
    if not os.path.exists(terms_of_service_html_path):
        return HTMLResponse(content="<html><body><h1>Error</h1><p>terms-of-service.html not found.</p></body></html>", status_code=404)
    return templates.TemplateResponse("terms-of-service.html", {"request": request})

@app.get("/contact", response_class=HTMLResponse, tags=["Frontend"])
async def serve_contact_page(request: Request):
    contact_html_path = os.path.join(template_dir, "contact.html")
    if not os.path.exists(contact_html_path):
        return HTMLResponse(content="<html><body><h1>Error</h1><p>contact.html not found.</p></body></html>", status_code=404)
    return templates.TemplateResponse("contact.html", {"request": request})
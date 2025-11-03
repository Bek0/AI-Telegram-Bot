# main.py - تعديلات

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from dashboard.routes import router as dashboard_router
from dashboard.cleanup_scheduler import start_scheduler, stop_scheduler
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """دورة حياة التطبيق"""
    # عند البدء
    logger.info("🚀 بدء التطبيق...")
    start_scheduler()
    yield
    # عند الإيقاف
    logger.info("🛑 إيقاف التطبيق...")
    stop_scheduler()

app = FastAPI(title="Organization Dashboard", lifespan=lifespan)

# ربط المسارات
app.include_router(dashboard_router)

# إعداد المسارات الثابتة
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

@app.get("/")
async def root():
    """الصفحة الرئيسية"""
    return FileResponse("dashboard/templates/login.html", media_type="text/html")

@app.get("/dashboard/")
async def dashboard():
    """صفحة الداش بورد"""
    return FileResponse("dashboard/templates/dashboard.html", media_type="text/html")

@app.get("/costs/")
async def costs():
    """صفحة التكاليف"""
    return FileResponse("dashboard/templates/dashboard.html", media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
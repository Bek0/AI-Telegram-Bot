# /main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# استيراد الـ dashboard routes
from dashboard.routes import router as dashboard_router

app = FastAPI(title="Organization Dashboard")

# ربط المسارات
app.include_router(dashboard_router)

# إعداد المسارات الثابتة (CSS, JS, images)
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

# ربط صفحات الـ dashboard

@app.get("/")
async def root():
    """الصفحة الرئيسية - تعيد صفحة الدخول"""
    return FileResponse("dashboard/templates/login.html", media_type="text/html")


@app.get("/dashboard/")
async def dashboard():
    """صفحة الداش بورد الرئيسية"""
    return FileResponse("dashboard/templates/dashboard.html", media_type="text/html")


@app.get("/costs/")
async def costs():
    """صفحة الداش بورد الرئيسية"""
    return FileResponse("dashboard/templates/costs.html", media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
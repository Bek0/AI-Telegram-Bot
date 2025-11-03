# dashboard/cleanup_scheduler.py - جديد

from apscheduler.schedulers.background import BackgroundScheduler
from dashboard.auth import SessionManager
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def cleanup_job():
    """مهمة تنظيف الجلسات المنتهية الصلاحية"""
    try:
        deleted = SessionManager.cleanup_expired_sessions()
    except Exception as e:
        logger.error(f"❌ خطأ في المهمة المجدولة: {e}")

def start_scheduler():
    """بدء المجدول"""
    if not scheduler.running:
        # تشغيل المهمة كل ساعة
        scheduler.add_job(
            cleanup_job,
            'interval',
            hours=1,
            id='cleanup_sessions',
            name='Cleanup expired sessions'
        )
        scheduler.start()
        logger.info("✅ بدء المجدول - تنظيف الجلسات كل ساعة")

def stop_scheduler():
    """إيقاف المجدول"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("✅ إيقاف المجدول")
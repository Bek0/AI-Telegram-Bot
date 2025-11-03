# db_connection.py
"""
ملف الاتصال بقاعدة البيانات مع Connection Pooling فعّال
"""
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool  # ✅ تغيير من NullPool
import urllib.parse
import logging

logger = logging.getLogger(__name__)

# معلومات الاتصال
DB_CONNECTION_STRING = "mssql+pyodbc://@B515R\\SQLEXPRESS/manager?driver=ODBC+Driver+17+for+SQL+Server"

# ✅ إعدادات Pool محسّنة
POOL_SIZE = 10          # عدد الاتصالات الدائمة
MAX_OVERFLOW = 20       # اتصالات إضافية عند الحاجة
POOL_TIMEOUT = 30       # وقت الانتظار بالثواني
POOL_RECYCLE = 3600     # إعادة إنشاء الاتصال بعد ساعة

# ✅ إنشاء محرك قاعدة البيانات مع QueuePool
engine = create_engine(
    DB_CONNECTION_STRING,
    poolclass=QueuePool,           # ✅ تغيير رئيسي
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,            # ✅ فحص الاتصال قبل الاستخدام
    echo=False,
    echo_pool=False                # ✅ تعطيل logs Pool (يمكن تفعيلها للـ debugging)
)

# ✅ Event listeners للمراقبة
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    logger.debug("✅ Database connection established")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    logger.debug("🔄 Connection checked out from pool")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    logger.debug("🔄 Connection returned to pool")

# إنشاء session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ============ قاعدة البيانات الثانية (costs) ============
DB_CONNECTION_STRING_2 = "mssql+pyodbc://@B515R\\SQLEXPRESS/costs?driver=ODBC+Driver+17+for+SQL+Server"

engine_2 = create_engine(
    DB_CONNECTION_STRING_2,
    poolclass=QueuePool,           # ✅ نفس التحسينات
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
    echo=False
)

SessionLocal_2 = sessionmaker(autocommit=False, autoflush=False, bind=engine_2)


# ============ قاعدة البيانات الثانية (costs) ============
DB_CONNECTION_STRING_3 = "mssql+pyodbc://@B515R\SQLEXPRESS/conversations?driver=ODBC+Driver+17+for+SQL+Server"

engine_3 = create_engine(
    DB_CONNECTION_STRING_3,
    poolclass=QueuePool,           # ✅ نفس التحسينات
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
    echo=False
)

SessionLocal_3 = sessionmaker(autocommit=False, autoflush=False, bind=engine_3)

def get_db_session() -> Session:
    """الحصول على جلسة قاعدة بيانات جديدة"""
    return SessionLocal()


# ✅ دالة للحصول على إحصائيات Pool
def get_pool_status():
    """
    عرض حالة Connection Pool (للمراقبة/debugging)
    """
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow()
    }


# ✅ Graceful shutdown
def dispose_engines():
    """
    إغلاق جميع الاتصالات عند إيقاف التطبيق
    """
    logger.info("🛑 Disposing database engines...")
    engine.dispose()
    engine_2.dispose()
    logger.info("✅ All connections closed")


# للاختبار
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("🧪 Testing Connection Pool...")
    
    # فتح 5 sessions
    sessions = [get_db_session() for _ in range(5)]
    print(f"📊 Pool status: {get_pool_status()}")
    
    # إغلاقها
    for s in sessions:
        s.close()
    print(f"📊 Pool status after close: {get_pool_status()}")
    
    dispose_engines()
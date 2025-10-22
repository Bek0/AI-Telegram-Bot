# /db_connection.py
"""
ملف الاتصال بقاعدة البيانات وإنشاء الجداول
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
import urllib.parse

# معلومات الاتصال
DB_CONNECTION_STRING = "mssql+pyodbc://@B515R\\SQLEXPRESS/manager?driver=ODBC+Driver+17+for+SQL+Server"

# إنشاء محرك قاعدة البيانات
engine = create_engine(
    DB_CONNECTION_STRING,
    poolclass=NullPool,
    echo=False  
)

# إنشاء session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


DB_CONNECTION_STRING_2 = "mssql+pyodbc://@B515R\\SQLEXPRESS/costs?driver=ODBC+Driver+17+for+SQL+Server"

# إنشاء محرك قاعدة البيانات
engine_2 = create_engine(
    DB_CONNECTION_STRING_2,
    poolclass=NullPool, 
    echo=False 
)

# إنشاء session maker
SessionLocal_2 = sessionmaker(autocommit=False, autoflush=False, bind=engine_2)


def get_db_session() -> Session:
    """الحصول على جلسة قاعدة بيانات جديدة"""
    return SessionLocal()
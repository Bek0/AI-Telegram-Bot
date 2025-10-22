# db/connection.py
from typing import Optional
from langchain_community.utilities import SQLDatabase
from dotenv import load_dotenv

load_dotenv()

SQL_CONNECTION_STRING="mssql+pyodbc://@B515R\SQLEXPRESS/RAG_PYTHON?driver=ODBC+Driver+17+for+SQL+Server"

# Global variable للاتصال - يتم إنشاؤه عند الطلب فقط
_db_instance: Optional[SQLDatabase] = None
_db_error: Optional[Exception] = None


def get_database() -> Optional[SQLDatabase]:
    """
    الحصول على اتصال قاعدة البيانات - lazy initialization
    
    Returns:
        SQLDatabase أو None إذا فشل الاتصال
    """
    global _db_instance, _db_error
    
    # إذا تم الاتصال مسبقاً بنجاح
    if _db_instance is not None:
        return _db_instance
    
    # إذا فشل الاتصال مسبقاً، لا نحاول مرة أخرى في كل مرة
    if _db_error is not None:
        return None
    
    # محاولة الاتصال
    if not SQL_CONNECTION_STRING:
        _db_error = ValueError("SQL_CONNECTION_STRING not configured in environment")
        print(f"⚠️ تحذير: {_db_error}")
        return None
    
    try:
        print(f"🔄 جاري الاتصال بقاعدة البيانات...")
        
        # إنشاء الاتصال مع معالجة أخطاء
        _db_instance = SQLDatabase.from_uri(
            SQL_CONNECTION_STRING,
            sample_rows_in_table_info=3
        )
        
        # اختبار الاتصال
        tables = _db_instance.get_usable_table_names()
        print(f"✅ تم الاتصال بقاعدة البيانات بنجاح")
        print(f"📊 الجداول المتاحة: {', '.join(tables[:5])}")
        
        return _db_instance
        
    except Exception as e:
        _db_error = e
        error_msg = str(e)
        
        # رسائل خطأ واضحة حسب نوع المشكلة
        if "IM004" in error_msg or "ODBC" in error_msg:
            print("❌ خطأ في ODBC Driver:")
            print("   المشكلة: ODBC Driver غير مثبت أو تالف")
            print("   الحل:")
            print("   1. ثبت ODBC Driver 17 for SQL Server:")
            print("      https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server")
            print("   2. أو استخدم pymssql بدلاً من pyodbc:")
            print("      pip install pymssql")
            print("      SQL_CONNECTION_STRING=mssql+pymssql://...")
        
        elif "authentication" in error_msg.lower():
            print("❌ خطأ في المصادقة:")
            print("   تحقق من اسم المستخدم وكلمة المرور في SQL_CONNECTION_STRING")
        
        elif "network" in error_msg.lower() or "connect" in error_msg.lower():
            print("❌ خطأ في الاتصال بالشبكة:")
            print("   تحقق من أن الخادم يعمل والمنفذ صحيح")
        
        else:
            print(f"❌ خطأ في الاتصال بقاعدة البيانات: {error_msg}")
        
        print("\n💡 البوت سيعمل بدون قاعدة البيانات (SQL queries ستفشل)")
        return None


def is_database_connected() -> bool:
    """فحص إذا كانت قاعدة البيانات متصلة"""
    return _db_instance is not None


def get_database_error() -> Optional[Exception]:
    """الحصول على خطأ الاتصال إن وجد"""
    return _db_error


def reset_database_connection():
    """إعادة تعيين الاتصال (للاختبار أو إعادة المحاولة)"""
    global _db_instance, _db_error
    _db_instance = None
    _db_error = None


# للتوافق مع الكود القديم
db = get_database()
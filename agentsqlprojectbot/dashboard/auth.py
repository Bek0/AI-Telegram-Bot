# /dashboard/auth.py
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict

# متغير عام لتخزين الجلسات
# في الإنتاج: استخدم Redis
_sessions: Dict[str, dict] = {}

SESSION_TIMEOUT_HOURS = 24


def create_session(org_id: str, user_id: int, role: str, org_name: str, username: str) -> str:
    """إنشاء جلسة جديدة وإرجاع token"""
    token = secrets.token_urlsafe(32)
    _sessions[token] = {
        'org_id': org_id,
        'user_id': user_id,
        'role': role,
        'org_name': org_name,
        'username': username,
        'created_at': datetime.now()
    }
    return token


def get_session(token: str) -> Optional[dict]:
    """الحصول على بيانات الجلسة"""
    if token not in _sessions:
        return None
    
    session = _sessions[token]
    
    # فحص انتهاء الصلاحية
    if datetime.now() - session['created_at'] > timedelta(hours=SESSION_TIMEOUT_HOURS):
        del _sessions[token]
        return None
    
    return session


def delete_session(token: str) -> bool:
    """حذف الجلسة"""
    if token in _sessions:
        del _sessions[token]
        return True
    return False


def is_session_valid(token: str) -> bool:
    """التحقق من صحة الجلسة"""
    return get_session(token) is not None
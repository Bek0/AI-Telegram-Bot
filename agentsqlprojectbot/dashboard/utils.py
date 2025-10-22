# /dashboard/utils.py
from functools import wraps
from fastapi import HTTPException
from dashboard.auth import get_session


def require_auth(f):
    """Decorator للتحقق من الجلسة"""
    @wraps(f)
    async def decorated(*args, token: str = None, **kwargs):
        if not token:
            raise HTTPException(status_code=401, detail="يجب تسجيل الدخول")
        
        session = get_session(token)
        if not session:
            raise HTTPException(status_code=401, detail="جلسة غير صحيحة")
        
        return await f(*args, session=session, **kwargs)
    
    return decorated


def require_owner(f):
    """Decorator للتحقق من أن المستخدم owner"""
    @wraps(f)
    async def decorated(*args, session: dict = None, **kwargs):
        if not session or session['role'] != 'owner':
            raise HTTPException(status_code=403, detail="ليس لديك صلاحية - owner فقط")
        
        return await f(*args, session=session, **kwargs)
    
    return decorated


def get_session_from_headers(authorization: str) -> str:
    """استخراج token من Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    return authorization[7:]
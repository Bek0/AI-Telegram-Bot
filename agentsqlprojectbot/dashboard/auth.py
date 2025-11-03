# dashboard/auth.py - الكود الجديد المحسّن

import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import text
from db_connection import SessionLocal
import logging

logger = logging.getLogger(__name__)

SESSION_TIMEOUT_HOURS = 24

class SessionManager:
    """مدير الجلسات مع قاعدة البيانات"""
    
    @staticmethod
    def create_session(
        org_id: str, 
        user_id: int, 
        role: str, 
        org_name: str, 
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        إنشاء جلسة جديدة وحفظها في قاعدة البيانات
        
        Args:
            org_id: معرف المؤسسة
            user_id: معرف المستخدم
            role: دور المستخدم (owner/member)
            org_name: اسم المؤسسة
            username: اسم المستخدم
            ip_address: عنوان IP (اختياري)
            user_agent: User Agent (اختياري)
            
        Returns:
            token: توكن الجلسة
        """
        db = SessionLocal()
        try:
            token = secrets.token_urlsafe(32)
            created_at = datetime.now()
            expires_at = created_at + timedelta(hours=SESSION_TIMEOUT_HOURS)
            
            # إدراج الجلسة في قاعدة البيانات
            db.execute(text("""
                INSERT INTO dashboard_sessions 
                (token, org_id, user_id, role, org_name, username, 
                 created_at, expires_at, last_activity, ip_address, user_agent, is_active)
                VALUES 
                (:token, :org_id, :user_id, :role, :org_name, :username,
                 :created_at, :expires_at, :last_activity, :ip_address, :user_agent, 1)
            """), {
                'token': token,
                'org_id': org_id,
                'user_id': user_id,
                'role': role,
                'org_name': org_name,
                'username': username,
                'created_at': created_at,
                'expires_at': expires_at,
                'last_activity': created_at,
                'ip_address': ip_address,
                'user_agent': user_agent
            })
            
            # احصل على session_id المُنشأة للـ audit log
            result = db.execute(text("""
                SELECT session_id FROM dashboard_sessions 
                WHERE token = :token
            """), {'token': token}).fetchone()
            
            if result:
                session_id = result[0]
                # سجل في audit log
                db.execute(text("""
                    INSERT INTO session_audit_log 
                    (session_id, action, action_timestamp, details)
                    VALUES 
                    (:session_id, 'LOGIN', :timestamp, :details)
                """), {
                    'session_id': session_id,
                    'timestamp': datetime.now(),
                    'details': f"User {username} logged in from {ip_address}"
                })
            
            db.commit()
            logger.info(f"✅ جلسة جديدة: {username} (Org: {org_id})")
            return token
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ خطأ في إنشاء الجلسة: {e}")
            raise
        finally:
            db.close()
    
    @staticmethod
    def get_session(token: str) -> Optional[dict]:
        """
        الحصول على بيانات الجلسة
        
        Args:
            token: توكن الجلسة
            
        Returns:
            dict: بيانات الجلسة أو None
        """
        db = SessionLocal()
        try:
            # تحقق من الجلسة والصلاحية
            result = db.execute(text("""
                SELECT 
                    session_id, token, org_id, user_id, role, org_name, username,
                    created_at, expires_at, last_activity, is_active
                FROM dashboard_sessions
                WHERE token = :token AND is_active = 1
            """), {'token': token}).fetchone()
            
            if not result:
                return None
            
            # تحقق من انتهاء الصلاحية
            expires_at = result[8]  # expires_at index
            if datetime.now() > expires_at:
                # أنهِ الجلسة المنتهية
                SessionManager.delete_session(token)
                logger.warning(f"⚠️  جلسة منتهية الصلاحية: {token[:20]}...")
                return None
            
            # حدّث last_activity
            db.execute(text("""
                UPDATE dashboard_sessions
                SET last_activity = :now
                WHERE token = :token
            """), {
                'now': datetime.now(),
                'token': token
            })
            db.commit()
            
            return {
                'session_id': result[0],
                'org_id': result[2],
                'user_id': result[3],
                'role': result[4],
                'org_name': result[5],
                'username': result[6],
                'created_at': result[7],
                'expires_at': result[8]
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على الجلسة: {e}")
            return None
        finally:
            db.close()
    
    @staticmethod
    def delete_session(token: str) -> bool:
        """
        حذف جلسة (logout)
        
        Args:
            token: توكن الجلسة
            
        Returns:
            bool: نجاح العملية
        """
        db = SessionLocal()
        try:
            # احصل على session_id
            result = db.execute(text("""
                SELECT session_id FROM dashboard_sessions
                WHERE token = :token
            """), {'token': token}).fetchone()
            
            if not result:
                return False
            
            session_id = result[0]
            
            # حدّث الحالة إلى inactive
            db.execute(text("""
                UPDATE dashboard_sessions
                SET is_active = 0
                WHERE token = :token
            """), {'token': token})
            
            # سجل في audit log
            db.execute(text("""
                INSERT INTO session_audit_log 
                (session_id, action, action_timestamp, details)
                VALUES 
                (:session_id, 'LOGOUT', :timestamp, 'User logged out')
            """), {
                'session_id': session_id,
                'timestamp': datetime.now()
            })
            
            db.commit()
            logger.info(f"✅ جلسة محذوفة: {token[:20]}...")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ خطأ في حذف الجلسة: {e}")
            return False
        finally:
            db.close()
    
    @staticmethod
    def is_session_valid(token: str) -> bool:
        """
        التحقق من صحة الجلسة
        
        Args:
            token: توكن الجلسة
            
        Returns:
            bool: صحة الجلسة
        """
        return SessionManager.get_session(token) is not None
    
    @staticmethod
    def cleanup_expired_sessions() -> int:
        """
        حذف الجلسات المنتهية الصلاحية (يجب تشغيله دورياً)
        
        Returns:
            int: عدد الجلسات المحذوفة
        """
        db = SessionLocal()
        try:
            # احصل على الجلسات المنتهية
            expired_result = db.execute(text("""
                SELECT session_id FROM dashboard_sessions
                WHERE expires_at < :now AND is_active = 1
            """), {'now': datetime.now()}).fetchall()
            
            # سجل في audit log
            for row in expired_result:
                session_id = row[0]
                db.execute(text("""
                    INSERT INTO session_audit_log 
                    (session_id, action, action_timestamp, details)
                    VALUES 
                    (:session_id, 'EXPIRED', :timestamp, 'Session expired')
                """), {
                    'session_id': session_id,
                    'timestamp': datetime.now()
                })
            
            # حدّث الجلسات المنتهية
            result = db.execute(text("""
                UPDATE dashboard_sessions
                SET is_active = 0
                WHERE expires_at < :now AND is_active = 1
            """), {'now': datetime.now()})
            
            deleted_count = result.rowcount
            db.commit()
            
            if deleted_count > 0:
                logger.info(f"🧹 تم تنظيف {deleted_count} جلسات منتهية الصلاحية")
            return deleted_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ خطأ في تنظيف الجلسات: {e}")
            return 0
        finally:
            db.close()

# دوال توافقية للـ backward compatibility
def create_session(org_id, user_id, role, org_name, username, ip_address=None, user_agent=None):
    """دالة توافقية"""
    return SessionManager.create_session(org_id, user_id, role, org_name, username, ip_address, user_agent)

def get_session(token):
    """دالة توافقية"""
    return SessionManager.get_session(token)

def delete_session(token):
    """دالة توافقية"""
    return SessionManager.delete_session(token)

def is_session_valid(token):
    """دالة توافقية"""
    return SessionManager.is_session_valid(token)
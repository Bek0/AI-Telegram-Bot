# services/database_manager.py
import asyncio
import secrets
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from langchain_community.utilities import SQLDatabase
from sqlalchemy import text

from db_connection import get_db_session


@dataclass
class DatabaseConnection:
    """معلومات اتصال قاعدة البيانات"""
    connection_id: str
    name: str
    connection_string: str
    created_by: int
    created_at: str
    owner_type: str  # "user" or "organization"
    owner_id: str  # user_id or org_id
    is_active: bool = True
    last_used: Optional[str] = None
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.connection_string:
            data['connection_string_preview'] = self._mask_password(self.connection_string)
        return data
    
    @staticmethod
    def _mask_password(conn_str: str) -> str:
        """إخفاء كلمة المرور في النص"""
        if '@' in conn_str and '://' in conn_str:
            parts = conn_str.split('@')
            if len(parts) >= 2:
                prefix = parts[0].split('://')[0]
                user_part = parts[0].split('://')[1].split(':')[0] if ':' in parts[0] else parts[0].split('://')[1]
                return f"{prefix}://{user_part}:****@{parts[1]}"
        return conn_str[:30] + "****"


class DatabaseManager:
    """مدير اتصالات قواعد البيانات المتعددة - نسخة SQL"""
    
    def __init__(self):
        self._db_instances: Dict[str, SQLDatabase] = {}
        self._lock = asyncio.Lock()
        
        print(f"✅ مدير قواعد البيانات جاهز (SQL Mode)")
    
    def _generate_connection_id(self) -> str:
        """توليد معرف فريد للاتصال"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(4)
        return f"DB_{timestamp}_{random_part}"
    
    # ✅ أضف دالة جديدة للحصول على جميع قواعد البيانات (شخصية + مؤسسة)
    async def add_connection(
            self,
            name: str,
            connection_string: str,
            created_by: int,
            owner_type: str,
            owner_id: str
        ) -> Optional[DatabaseConnection]:
            """إضافة اتصال قاعدة بيانات جديد - محدّث"""
            async with self._lock:
                # اختبار الاتصال أولاً
                is_valid, error = await self._test_connection(connection_string)
                if not is_valid:
                    print(f"❌ فشل اختبار الاتصال: {error}")
                    return None
                
                connection_id = self._generate_connection_id()
                
                db = get_db_session()
                try:
                    # 1️⃣ إضافة السجل في database_connections
                    db.execute(text("""
                        INSERT INTO database_connections 
                        (connection_id, name, connection_string, created_by, created_at, owner_type, owner_id, is_active)
                        VALUES 
                        (:connection_id, :name, :connection_string, :created_by, :created_at, :owner_type, :owner_id, 1)
                    """), {
                        'connection_id': connection_id,
                        'name': name,
                        'connection_string': connection_string,
                        'created_by': created_by,
                        'created_at': datetime.now(),
                        'owner_type': owner_type,
                        'owner_id': owner_id
                    })
                    
                    db.commit()
                    
                    connection = DatabaseConnection(
                        connection_id=connection_id,
                        name=name,
                        connection_string=connection_string,
                        created_by=created_by,
                        created_at=datetime.now().isoformat(),
                        owner_type=owner_type,
                        owner_id=owner_id,
                        is_active=True
                    )
                    
                    print(f"✅ تم إضافة اتصال قاعدة البيانات: {name}")
                    return connection
                    
                except Exception as e:
                    db.rollback()
                    print(f"❌ خطأ في إضافة اتصال قاعدة البيانات: {e}")
                    return None
                finally:
                    db.close()

    
    async def _test_connection(self, connection_string: str) -> tuple[bool, Optional[str]]:
        """اختبار اتصال قاعدة البيانات"""
        try:
            loop = asyncio.get_event_loop()
            db = await loop.run_in_executor(
                None,
                lambda: SQLDatabase.from_uri(connection_string, sample_rows_in_table_info=1)
            )
            
            tables = db.get_usable_table_names()
            return True, None
        except Exception as e:
            return False, str(e)
    
    async def get_connection(self, connection_id: str) -> Optional[DatabaseConnection]:
        """الحصول على معلومات اتصال"""
        db = get_db_session()
        try:
            result = db.execute(text("""
                SELECT connection_id, name, connection_string, created_by, created_at, 
                       owner_type, owner_id, is_active, last_used
                FROM database_connections
                WHERE connection_id = :connection_id 
            """), {'connection_id': connection_id})
            
            row = result.fetchone()
            if row:
                return DatabaseConnection(
                    connection_id=row[0],
                    name=row[1],
                    connection_string=row[2],
                    created_by=row[3],
                    created_at=row[4].isoformat() if row[4] else None,
                    owner_type=row[5],
                    owner_id=row[6],
                    is_active=bool(row[7]),
                    last_used=row[8].isoformat() if row[8] else None
                )
            return None
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على الاتصال: {e}")
            return None
        finally:
            db.close()
    
    async def get_database_instance(self, connection_id: str) -> Optional[SQLDatabase]:
        """الحصول على instance من قاعدة البيانات"""
        connection = await self.get_connection(connection_id)
        if not connection or not connection.is_active:
            return None
        
        # التحقق من الـ cache
        if connection_id in self._db_instances:
            return self._db_instances[connection_id]
        
        try:
            loop = asyncio.get_event_loop()
            db = await loop.run_in_executor(
                None,
                lambda: SQLDatabase.from_uri(connection.connection_string)
            )
            self._db_instances[connection_id] = db
            
            # تحديث آخر استخدام
            db_session = get_db_session()
            try:
                db_session.execute(text("""
                    UPDATE database_connections 
                    SET last_used = :last_used 
                    WHERE connection_id = :connection_id
                """), {
                    'last_used': datetime.now(),
                    'connection_id': connection_id
                })
                db_session.commit()
            finally:
                db_session.close()
            
            return db
        except Exception as e:
            print(f"❌ خطأ في الاتصال بقاعدة البيانات {connection_id}: {e}")
            return None
    
    async def get_user_connections(self, user_id: int) -> List[DatabaseConnection]:
        """الحصول على اتصالات المستخدم الشخصية النشطة"""
        db = get_db_session()
        try:
            result = db.execute(text("""
                SELECT connection_id, name, connection_string, created_by, created_at, 
                       owner_type, owner_id, is_active, last_used
                FROM database_connections
                WHERE owner_type = 'user' AND owner_id = :user_id AND is_active = 1
                ORDER BY created_at DESC
            """), {'user_id': str(user_id)})
            
            connections = []
            for row in result:
                connections.append(DatabaseConnection(
                    connection_id=row[0],
                    name=row[1],
                    connection_string=row[2],
                    created_by=row[3],
                    created_at=row[4].isoformat() if row[4] else None,
                    owner_type=row[5],
                    owner_id=row[6],
                    is_active=bool(row[7]),
                    last_used=row[8].isoformat() if row[8] else None
                ))
            
            return connections
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على اتصالات المستخدم: {e}")
            return []
        finally:
            db.close()
    
    async def get_organization_connections(self, org_id: str) -> List[DatabaseConnection]:
        """الحصول على اتصالات المؤسسة النشطة - محدّث"""
        db = get_db_session()
        try:
            # ✅ الجلب من خلال organization_databases بدلاً من owner_type
            result = db.execute(text("""
                SELECT 
                    dc.connection_id, dc.name, dc.connection_string, 
                    dc.created_by, dc.created_at, dc.owner_type, 
                    dc.owner_id, dc.is_active, dc.last_used
                FROM database_connections dc
                INNER JOIN organization_databases od 
                    ON dc.connection_id = od.connection_id
                WHERE od.org_id = :org_id AND dc.is_active = 1
                ORDER BY od.added_at DESC
            """), {'org_id': org_id})
            
            connections = []
            for row in result:
                connections.append(DatabaseConnection(
                    connection_id=row[0],
                    name=row[1],
                    connection_string=row[2],
                    created_by=row[3],
                    created_at=row[4].isoformat() if row[4] else None,
                    owner_type=row[5],
                    owner_id=row[6],
                    is_active=bool(row[7]),
                    last_used=row[8].isoformat() if row[8] else None
                ))
            
            return connections
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على اتصالات المؤسسة: {e}")
            return []
        finally:
            db.close()

    def clear_instance_cache(self, connection_id: Optional[str] = None):
        """مسح cache الـ instances"""
        if connection_id:
            if connection_id in self._db_instances:
                del self._db_instances[connection_id]
        else:
            self._db_instances.clear()
    
    async def verify_user_can_access_database(
        self,
        user_id: int,
        database_id: str
    ) -> tuple[bool, str]:
        """التحقق من أن المستخدم يملك الوصول إلى قاعدة البيانات"""
        connection = await self.get_connection(database_id)
        
        if not connection or not connection.is_active:
            return False, "قاعدة البيانات غير موجودة أو معطلة"
        
        # حالة 1: قاعدة بيانات شخصية
        if connection.owner_type == "user":
            if str(user_id) == connection.owner_id:
                return True, ""
            else:
                return False, "ليس لديك صلاحية للوصول لهذه قاعدة البيانات"
        
        # حالة 2: قاعدة بيانات مؤسسة
        elif connection.owner_type == "organization":
            from services.organization_manager import get_organization_manager
            
            org_manager = get_organization_manager()
            is_member = await org_manager.is_organization_member(user_id, connection.owner_id)
            
            if is_member:
                return True, ""
            else:
                return False, "أنت لست عضواً في المؤسسة التي تملك هذه قاعدة البيانات"
        
        return False, "نوع قاعدة البيانات غير معروف"

# Singleton instance
_db_manager: Optional[DatabaseManager] = None

def get_database_manager() -> DatabaseManager:
    """الحصول على instance واحد من مدير قواعد البيانات"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
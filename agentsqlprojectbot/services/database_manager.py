# services/database_manager.py
import asyncio
import secrets
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine, text, inspect
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
    schema_example: Optional[str] = None
    data_example: Optional[str] = None
    db_type: Optional[str] = None  # ✅ نوع قاعدة البيانات
    
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
    """مدير اتصالات قواعد البيانات المتعددة - نسخة محسّنة مع دعم PostgreSQL"""
    
    def __init__(self):
        self._db_instances: Dict[str, SQLDatabase] = {}
        self._lock = asyncio.Lock()
        
        print(f"✅ مدير قواعد البيانات جاهز (SQL Mode - Multi-DB Support)")
    
    def _generate_connection_id(self) -> str:
        """توليد معرف فريد للاتصال"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(4)
        return f"DB_{timestamp}_{random_part}"
    
    def _detect_database_type(self, connection_string: str) -> str:
        """
        تحديد نوع قاعدة البيانات من connection string
        
        Returns:
            'postgresql', 'mysql', 'mssql', 'sqlite', 'oracle', أو 'unknown'
        """
        conn_str_lower = connection_string.lower()
        
        if 'postgresql' in conn_str_lower or conn_str_lower.startswith('postgres://'):
            return 'postgresql'
        elif 'mysql' in conn_str_lower:
            return 'mysql'
        elif 'mssql' in conn_str_lower or 'sqlserver' in conn_str_lower:
            return 'mssql'
        elif 'sqlite' in conn_str_lower:
            return 'sqlite'
        elif 'oracle' in conn_str_lower:
            return 'oracle'
        else:
            return 'unknown'
    
    def _get_limit_syntax(self, db_type: str, limit: int = 1) -> str:
        """
        الحصول على syntax الصحيح لـ LIMIT حسب نوع قاعدة البيانات
        
        Args:
            db_type: نوع قاعدة البيانات
            limit: عدد السطور
        
        Returns:
            SQL snippet للـ LIMIT
        """
        if db_type == 'mssql':
            return f"TOP {limit}"
        elif db_type in ['postgresql', 'mysql', 'sqlite']:
            return f"LIMIT {limit}"
        elif db_type == 'oracle':
            return f"FETCH FIRST {limit} ROWS ONLY"
        else:
            # Default to PostgreSQL syntax (most common)
            return f"LIMIT {limit}"
    
    def _build_sample_query(self, table_name: str, db_type: str) -> str:
        """✅ بناء استعلام عينة متوافق مع نوع قاعدة البيانات"""
        if db_type == 'mssql':
            return f"SELECT TOP 1 * FROM [{table_name}]"
        elif db_type == 'sqlite':
            # ✅ SQLite يحتاج إلى معالجة خاصة للجداول والأسماء المحفوظة
            return f"SELECT * FROM \"{table_name}\" LIMIT 1"
        elif db_type == 'postgresql':
            return f"SELECT * FROM \"{table_name}\" LIMIT 1"
        elif db_type == 'mysql':
            return f"SELECT * FROM `{table_name}` LIMIT 1"
        elif db_type == 'oracle':
            return f"SELECT * FROM {table_name} FETCH FIRST 1 ROWS ONLY"
        else:
            return f"SELECT * FROM {table_name} LIMIT 1"

    async def get_examples_from_connection_string(self, connection_string: str):
        """✅ الحصول على سكيما الجداول وأول صف من كل جدول - محسّن مع دعم SQLite"""
        try:
            db_type = self._detect_database_type(connection_string)
            print(f"🔍 اكتشاف نوع قاعدة البيانات: {db_type}")
            print(f"📌 رابط الاتصال: {connection_string}")
            
            # ✅ إنشاء محرك بشكل مباشر (بدون executor)
            from sqlalchemy import create_engine, MetaData, text
            
            print("🔄 جاري إنشاء محرك قاعدة البيانات...")
            engine = create_engine(connection_string)
            
            # ✅ اختبار الاتصال أولاً
            try:
                with engine.connect() as conn:
                    print("✅ تم الاتصال بقاعدة البيانات بنجاح")
            except Exception as e:
                print(f"❌ فشل الاتصال: {e}")
                return None, None, db_type
            
            # ✅ استخدام Inspector للحصول على الجداول
            print("🔍 جاري البحث عن الجداول...")
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            
            print(f"📋 الجداول المكتشفة: {table_names}")
            
            if not table_names:
                print("⚠️ لم يتم العثور على جداول قابلة للاستخدام")
                return None, None, db_type
            
            schema_parts = []
            data_parts = []
            
            # ✅ معالجة كل جدول
            for table_name in table_names:
                # تجاهل جداول النظام
                if table_name.lower() in ['sysdiagrams', 'pg_stat_statements', 'sqlite_sequence']:
                    continue
                
                try:
                    # 1️⃣ الحصول على أسماء الأعمدة
                    columns = inspector.get_columns(table_name)
                    if not columns:
                        continue
                    
                    column_names = [col['name'] for col in columns]
                    
                    # 2️⃣ الحصول على العلاقات (Foreign Keys)
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    fk_info = []
                    for fk in foreign_keys:
                        fk_columns = ', '.join(fk['constrained_columns'])
                        ref_table = fk['referred_table']
                        ref_columns = ', '.join(fk['referred_columns'])
                        fk_info.append(f"{fk_columns} -> {ref_table}({ref_columns})")
                    
                    # 3️⃣ بناء السكيما بنفس صيغة الفانكشن الثاني
                    schema_line = f"{table_name}: {', '.join(column_names)}"
                    if fk_info:
                        schema_line += f"\n  FK: {'; '.join(fk_info)}"
                    
                    schema_parts.append(schema_line)
                    
                except Exception as e:
                    print(f"⚠️ خطأ في معالجة الجدول {table_name}: {e}")
                    continue
                
                # 4️⃣ الحصول على أول صف (مثال)
                try:
                    sample_query = self._build_sample_query(table_name, db_type)
                    
                    # تنفيذ الاستعلام بشكل مباشر
                    with engine.connect() as connection:
                        result = connection.execute(text(sample_query))
                        row = result.fetchone()
                        
                        if row:
                            # تحويل الصف إلى صيغة مقروءة (نفس صيغة الفانكشن الثاني)
                            row_str = ", ".join(str(v) for v in row)
                            data_parts.append(f"Table: {table_name}\n{row_str}\n")
                                
                except Exception as e:
                    print(f"⚠️ خطأ في جلب مثال من {table_name}: {e}")
            
            # ✅ تجميع النتائج النهائية
            schema_text = "\n".join(schema_parts)
            data_text = "\n".join(data_parts)
            
            print(f"✅ تم معالجة {len(schema_parts)} جدول بنجاح")
            print(f"📊 حجم السكيما: ~{len(schema_text)} حرف")
            
            return schema_text, data_text, db_type
    
        except Exception as e:
            print(f"❌ خطأ في الحصول على الأمثلة: {e}")
            import traceback
            traceback.print_exc()
            return None, None, 'unknown'
    
    async def add_connection(
            self,
            name: str,
            connection_string: str,
            created_by: int,
            owner_type: str,
            owner_id: str
        ) -> Optional[DatabaseConnection]:
            """إضافة اتصال قاعدة بيانات جديد - محدّث مع دعم PostgreSQL"""
            async with self._lock:
                # اختبار الاتصال أولاً
                is_valid, error = await self._test_connection(connection_string)
                if not is_valid:
                    print(f"❌ فشل اختبار الاتصال: {error}")
                    return None
                
                connection_id = self._generate_connection_id()
                
                # ✅ جلب السكيما والأمثلة مع نوع قاعدة البيانات
                schema_example, data_example, db_type = await self.get_examples_from_connection_string(connection_string)
                
                db = get_db_session()
                try:
                    # إضافة السجل في database_connections مع نوع قاعدة البيانات
                    db.execute(text("""
                        INSERT INTO database_connections 
                        (connection_id, name, connection_string, created_by, created_at, 
                        owner_type, owner_id, is_active, schema_example, data_example, db_type)
                        VALUES 
                        (:connection_id, :name, :connection_string, :created_by, :created_at, 
                        :owner_type, :owner_id, 1, :schema_example, :data_example, :db_type)
                    """), {
                        'connection_id': connection_id,
                        'name': name,
                        'connection_string': connection_string,
                        'created_by': created_by,
                        'created_at': datetime.now(),
                        'owner_type': owner_type,
                        'owner_id': owner_id,
                        'schema_example': schema_example,
                        'data_example': data_example,
                        'db_type': db_type  # ✅ حفظ نوع قاعدة البيانات
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
                        is_active=True,
                        db_type=db_type  # ✅ إضافة نوع قاعدة البيانات
                    )
                    
                    print(f"✅ تم إضافة اتصال قاعدة البيانات: {name} (Type: {db_type})")
                    print(f"📊 تم تخزين السكيما والأمثلة بنجاح")
                    return connection, db_type
                    
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
                    owner_type, owner_id, is_active, last_used, schema_example, data_example, db_type
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
                    last_used=row[8].isoformat() if row[8] else None,
                    schema_example=row[9],
                    data_example=row[10],
                    db_type=row[11] if len(row) > 11 else 'unknown'  # ✅ قراءة نوع قاعدة البيانات
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
                       owner_type, owner_id, is_active, last_used, db_type
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
                    last_used=row[8].isoformat() if row[8] else None,
                    db_type=row[9] if len(row) > 9 else 'unknown'
                ))
            
            return connections
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على اتصالات المستخدم: {e}")
            return []
        finally:
            db.close()
    
    async def get_organization_connections(self, org_id: str) -> List[DatabaseConnection]:
        """الحصول على اتصالات المؤسسة النشطة"""
        db = get_db_session()
        try:
            result = db.execute(text("""
                SELECT 
                    dc.connection_id, dc.name, dc.connection_string, 
                    dc.created_by, dc.created_at, dc.owner_type, 
                    dc.owner_id, dc.is_active, dc.last_used, dc.db_type
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
                    last_used=row[8].isoformat() if row[8] else None,
                    db_type=row[9] if len(row) > 9 else 'unknown'
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
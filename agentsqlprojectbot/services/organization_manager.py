# services/organization_manager.py
import asyncio
import secrets
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from sqlalchemy import text

from db_connection import get_db_session
from services.telegram_auth import get_user_display_name
import secrets
import hashlib
import os
import logging
from dotenv import load_dotenv

# إعداد logger
logger = logging.getLogger(__name__)

# الحصول على مجلد المشروع الرئيسي
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# تحميل .env من مجلد المشروع الرئيسي
dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path)

# التحقق من المتغير
MASTER_PASSWORD_HASH = os.getenv("MASTER_PASSWORD_HASH")
if not MASTER_PASSWORD_HASH:
    logger.critical("⚠️ MASTER_PASSWORD_HASH not set in environment! Master password authentication will be disabled.")
else:
    logger.info("MASTER_PASSWORD_HASH loaded successfully. length=%d", len(MASTER_PASSWORD_HASH))


# تعريف الأدوار المتاحة
ROLE_OWNER = "owner"
ROLE_MEMBER = "member"
VALID_ROLES = [ROLE_OWNER, ROLE_MEMBER]

@dataclass
class OrganizationMember:
    """معلومات عضو المؤسسة"""
    user_id: int
    org_id: str
    role: str  # "owner" or "member"
    joined_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class Organization:
    """معلومات المؤسسة"""
    org_id: str
    name: str
    owner_id: int
    created_at: str
    description: Optional[str] = None
    database_connections: List[str] = None  # قائمة معرفات الاتصالات
    members: List[int] = None  # قائمة معرفات الأعضاء
    
    def __post_init__(self):
        """تهيئة القوائم الافتراضية"""
        if self.database_connections is None:
            self.database_connections = []
        if self.members is None:
            self.members = []
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class InvitationLog:
    """سجل استخدام الدعوة"""
    user_id: int
    username: str
    used_at: str
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Invitation:
    """رابط دعوة آمن"""
    invite_code: str
    org_id: str
    created_by: int
    created_at: str
    expires_at: str
    max_uses: int
    current_uses: int
    is_active: bool
    created_by_name: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AdvancedInvitation(Invitation):
    """دعوة متقدمة مع تسجيل استخدام"""
    used_by: List[int] = None
    usage_logs: List[InvitationLog] = None
    
    def __post_init__(self):
        if self.used_by is None:
            self.used_by = []
        if self.usage_logs is None:
            self.usage_logs = []
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        if data.get('usage_logs'):
            data['usage_logs'] = [
                log.to_dict() if isinstance(log, InvitationLog) else log
                for log in data['usage_logs']
            ]
        return data


class OrganizationManager:
    """مدير المؤسسات - نظام متكامل لإدارة المؤسسات والعضويات - نسخة SQL"""
    
    def __init__(self):
        self._lock = asyncio.Lock()
        print(f"✅ مدير المؤسسات جاهز (SQL Mode)")
    
    def _generate_org_id(self) -> str:
        """توليد معرف فريد للمؤسسة"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(4)
        return f"ORG_{timestamp}_{random_part}"
    
    def _generate_invite_code(self) -> str:
        """توليد رمز دعوة آمن"""
        return secrets.token_urlsafe(16)
    
    async def create_organization(
        self,
        owner_id: int,
        name: str,
        description: Optional[str] = None
    ) -> Organization:
        """إنشاء مؤسسة جديدة"""
        async with self._lock:
            org_id = self._generate_org_id()
            
            db = get_db_session()
            try:
                # إنشاء المؤسسة
                db.execute(text("""
                    INSERT INTO organizations (org_id, name, owner_id, created_at, description)
                    VALUES (:org_id, :name, :owner_id, :created_at, :description)
                """), {
                    'org_id': org_id,
                    'name': name,
                    'owner_id': owner_id,
                    'created_at': datetime.now(),
                    'description': description
                })
                
                # إضافة المالك كعضو مع role 'owner'
                db.execute(text("""
                    INSERT INTO organization_members (org_id, user_id, joined_at, role)
                    VALUES (:org_id, :user_id, :joined_at, :role)
                """), {
                    'org_id': org_id,
                    'user_id': owner_id,
                    'joined_at': datetime.now(),
                    'role': 'owner'
                })
                
                # واستبدله بهذا:
                owner_username = f"owner_{org_id[-15:]}"
                owner_password = self._generate_password()
                owner_password_hash = self._hash_password(owner_password)

                db.execute(text("""
                    INSERT INTO dashboard_users (org_id, user_id, username, password_hash, role)
                    VALUES (:org_id, :user_id, :username, :password_hash, :role)
                """), {
                    'org_id': org_id,
                    'user_id': owner_id,
                    'username': owner_username,
                    'password_hash': owner_password_hash,
                    'role': 'owner'
                })

                
                db.commit()
                
                org = Organization(
                    org_id=org_id,
                    name=name,
                    owner_id=owner_id,
                    created_at=datetime.now().isoformat(),
                    description=description
                )

                print(f"✅ تم إنشاء المؤسسة: {org.name} (ID: {org.org_id})")
                print(f"✅ تم إنشاء حساب داش بورد للمالك: {owner_username}")
                print(f"Owner credentials: {owner_username} / {owner_password}")
                # إرجاع البيانات مع بيانات الدخول
                return {
                    'org': org,
                    'dashboard_username': owner_username,
                    'dashboard_password': owner_password
                }
                
            except Exception as e:
                db.rollback()
                print(f"❌ خطأ في إنشاء المؤسسة: {e}")
                raise
            finally:
                db.close()
    
    async def get_organization(self, org_id: str) -> Optional[Organization]:
        """الحصول على معلومات مؤسسة"""
        db = get_db_session()
        try:
            result = db.execute(text("""
                SELECT org_id, name, owner_id, created_at, description
                FROM organizations
                WHERE org_id = :org_id
            """), {'org_id': org_id})
            
            row = result.fetchone()
            if not row:
                return None
            
            # الحصول على الأعضاء
            members_result = db.execute(text("""
                SELECT user_id FROM organization_members
                WHERE org_id = :org_id
            """), {'org_id': org_id})
            members = [r[0] for r in members_result]
            
            # الحصول على قواعد البيانات
            dbs_result = db.execute(text("""
                SELECT connection_id FROM organization_databases
                WHERE org_id = :org_id
            """), {'org_id': org_id})
            database_connections = [r[0] for r in dbs_result]
            
            return Organization(
                org_id=row[0],
                name=row[1],
                owner_id=row[2],
                created_at=row[3].isoformat() if row[3] else None,
                description=row[4],
                members=members,
                database_connections=database_connections
            )
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على المؤسسة: {e}")
            return None
        finally:
            db.close()
    
    async def get_user_organization(self, user_id: int) -> Optional[Organization]:
        """الحصول على مؤسسة المستخدم"""
        db = get_db_session()
        try:
            result = db.execute(text("""
                SELECT o.org_id, o.name, o.owner_id, o.created_at, o.description
                FROM organizations o
                INNER JOIN organization_members m ON o.org_id = m.org_id
                WHERE m.user_id = :user_id
            """), {'user_id': user_id})
            
            row = result.fetchone()
            if not row:
                return None
            
            org_id = row[0]
            
            # الحصول على الأعضاء
            members_result = db.execute(text("""
                SELECT user_id FROM organization_members
                WHERE org_id = :org_id
            """), {'org_id': org_id})
            members = [r[0] for r in members_result]
            
            # الحصول على قواعد البيانات
            dbs_result = db.execute(text("""
                SELECT connection_id FROM organization_databases
                WHERE org_id = :org_id
            """), {'org_id': org_id})
            database_connections = [r[0] for r in dbs_result]
            
            return Organization(
                org_id=org_id,
                name=row[1],
                owner_id=row[2],
                created_at=row[3].isoformat() if row[3] else None,
                description=row[4],
                members=members,
                database_connections=database_connections
            )
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على مؤسسة المستخدم: {e}")
            return None
        finally:
            db.close()

    async def get_organization_members_with_roles(self, org_id: str) -> List[OrganizationMember]:
        """الحصول على أعضاء المؤسسة مع أدوارهم"""
        db = get_db_session()
        try:
            result = db.execute(text("""
                SELECT user_id, org_id, role, joined_at
                FROM organization_members
                WHERE org_id = :org_id
                ORDER BY joined_at
            """), {'org_id': org_id})
            
            members = []
            for row in result:
                members.append(OrganizationMember(
                    user_id=row[0],
                    org_id=row[1],
                    role=row[2],
                    joined_at=row[3].isoformat() if row[3] else None
                ))
            
            return members
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على الأعضاء: {e}")
            return []
        finally:
            db.close()

    async def is_organization_owner(self, user_id: int, org_id: str) -> bool:
        """فحص إذا كان المستخدم مالك المؤسسة"""
        db = get_db_session()
        try:
            result = db.execute(text("""
                SELECT role FROM organization_members
                WHERE org_id = :org_id AND user_id = :user_id
            """), {'org_id': org_id, 'user_id': user_id})
            
            row = result.fetchone()
            return row and row[0] == ROLE_OWNER
            
        except Exception as e:
            print(f"❌ خطأ في فحص الملكية: {e}")
            return False
        finally:
            db.close()
    
    async def is_organization_member(self, user_id: int, org_id: str) -> bool:
        """فحص إذا كان المستخدم عضو في المؤسسة"""
        db = get_db_session()
        try:
            result = db.execute(text("""
                SELECT COUNT(*) FROM organization_members
                WHERE org_id = :org_id AND user_id = :user_id
            """), {'org_id': org_id, 'user_id': user_id})
            
            count = result.scalar()
            return count > 0
            
        except Exception as e:
            print(f"❌ خطأ في فحص العضوية: {e}")
            return False
        finally:
            db.close()
    
    async def add_member_directly(
        self,
        org_id: str,
        owner_id: int,
        member_id: int,
        role: str = ROLE_MEMBER
    ) -> bool:
        """إضافة عضو مباشرة (من قبل المدير)"""
        async with self._lock:
            # التحقق من الملكية
            if not await self.is_organization_owner(owner_id, org_id):
                return False
            
            # فحص إذا كان المستخدم عضو في مؤسسة أخرى
            existing_org = await self.get_user_organization(member_id)
            if existing_org:
                return False
            
            db = get_db_session()
            try:
                # إضافة العضو
                db.execute(text("""
                    INSERT INTO organization_members (org_id, user_id, joined_at, role)
                    VALUES (:org_id, :user_id, :joined_at, :role)
                """), {
                    'org_id': org_id,
                    'user_id': member_id,
                    'joined_at': datetime.now(),
                    'role': role
                })
                db.commit()
                
                print(f"✅ تم إضافة العضو {member_id} إلى المؤسسة {org_id}")
                return True
                
            except Exception as e:
                db.rollback()
                print(f"❌ خطأ في إضافة العضو: {e}")
                return False
            finally:
                db.close()
    
    async def create_invitation(
        self,
        org_id: str,
        creator_id: int,
        max_uses: int = 1,
        expires_hours: int = 24
    ) -> Optional[Invitation]:
        """إنشاء رابط دعوة"""
        async with self._lock:
            # التحقق من الملكية
            if not await self.is_organization_owner(creator_id, org_id):
                return None
            
            invite_code = self._generate_invite_code()
            expires_at = datetime.now() + timedelta(hours=expires_hours)
            
            db = get_db_session()
            try:
                db.execute(text("""
                    INSERT INTO invitations 
                    (invite_code, org_id, created_by, created_at, expires_at, max_uses, current_uses, is_active)
                    VALUES 
                    (:invite_code, :org_id, :created_by, :created_at, :expires_at, :max_uses, 0, 1)
                """), {
                    'invite_code': invite_code,
                    'org_id': org_id,
                    'created_by': creator_id,
                    'created_at': datetime.now(),
                    'expires_at': expires_at,
                    'max_uses': max_uses
                })
                db.commit()
                
                invitation = Invitation(
                    invite_code=invite_code,
                    org_id=org_id,
                    created_by=creator_id,
                    created_at=datetime.now().isoformat(),
                    expires_at=expires_at.isoformat(),
                    max_uses=max_uses,
                    current_uses=0,
                    is_active=True
                )
                
                print(f"✅ تم إنشاء رابط الدعوة: {invite_code}")
                return invitation
                
            except Exception as e:
                db.rollback()
                print(f"❌ خطأ في إنشاء رابط الدعوة: {e}")
                return None
            finally:
                db.close()
    
    async def use_invitation(self, invite_code: str, user_id: int, username: str = None) -> tuple[bool, str, dict]:
        """استخدام رابط الدعوة مع تسجيل كامل"""
        async with self._lock:
            db = get_db_session()
            try:
                # الحصول على معلومات الدعوة
                result = db.execute(text("""
                    SELECT invite_code, org_id, created_by, created_at, expires_at, 
                           max_uses, current_uses, is_active
                    FROM invitations
                    WHERE invite_code = :invite_code
                """), {'invite_code': invite_code})
                row = result.fetchone()
                if not row:
                    return False, "رمز الدعوة غير صحيح"
                
                invitation = Invitation(
                    invite_code=row[0],
                    org_id=row[1],
                    created_by=row[2],
                    created_at=row[3].isoformat() if row[3] else None,
                    expires_at=row[4].isoformat() if row[4] else None,
                    max_uses=row[5],
                    current_uses=row[6],
                    is_active=bool(row[7])
                )
                
                if not invitation.is_active:
                    return False, "رابط الدعوة غير نشط",""
                
                # فحص انتهاء الصلاحية
                expires_at = datetime.fromisoformat(invitation.expires_at)
                if datetime.now() > expires_at:
                    db.execute(text("""
                        UPDATE invitations SET is_active = 0 
                        WHERE invite_code = :invite_code
                    """), {'invite_code': invite_code})
                    db.commit()
                    return False, "رابط الدعوة منتهي الصلاحية",""
                
                # فحص عدد الاستخدامات
                if invitation.current_uses >= invitation.max_uses:
                    db.execute(text("""
                        UPDATE invitations SET is_active = 0 
                        WHERE invite_code = :invite_code
                    """), {'invite_code': invite_code})
                    db.commit()
                    return False, "تم استنفاد استخدامات هذا الرابط",""
                
                # فحص إذا كان المستخدم عضو في مؤسسة أخرى
                existing_org = await self.get_user_organization(user_id)
                if existing_org:
                    return False, "أنت بالفعل عضو في مؤسسة أخرى",""
                
                # الحصول على معلومات المؤسسة
                org = await self.get_organization(invitation.org_id)
                if not org:
                    return False, "المؤسسة غير موجودة",""
                
                # إضافة العضو
                db.execute(text("""
                    INSERT INTO organization_members (org_id, user_id, joined_at, role)
                    VALUES (:org_id, :user_id, :joined_at, :role)
                """), {
                    'org_id': org.org_id,
                    'user_id': user_id,
                    'joined_at': datetime.now(),
                    'role': ROLE_MEMBER  # الأعضاء الجدد = member
                })
                

                member_username = f"member_{org.org_id[:6]}_{user_id}"
                member_password = self._generate_password()
                member_password_hash = self._hash_password(member_password)
                
                db.execute(text("""
                    INSERT INTO dashboard_users (org_id, user_id, username, password_hash, role, created_at)
                    VALUES (:org_id, :user_id, :username, :password_hash, :role, :created_at)
                """), {
                    'org_id': org.org_id,
                    'user_id': user_id,
                    'username': member_username,
                    'password_hash': member_password_hash,
                    'role': 'member',  # ✅ العضو الجديد يكون 'member'
                    'created_at': datetime.now()
                })

                # تسجيل استخدام الدعوة
                db.execute(text("""
                    INSERT INTO invitation_usage_logs (invite_code, user_id, username, used_at)
                    VALUES (:invite_code, :user_id, :username, :used_at)
                """), {
                    'invite_code': invite_code,
                    'user_id': user_id,
                    'username': username or get_user_display_name(user_id),
                    'used_at': datetime.now()
                })
                
                # تحديث عدد الاستخدامات
                new_uses = invitation.current_uses + 1
                is_active = 1 if new_uses < invitation.max_uses else 0
                
                db.execute(text("""
                    UPDATE invitations 
                    SET current_uses = :current_uses, is_active = :is_active
                    WHERE invite_code = :invite_code
                """), {
                    'current_uses': new_uses,
                    'is_active': is_active,
                    'invite_code': invite_code
                })
                
                db.commit()
                # إرجاع بيانات الدخول
                dashboard_credentials = {
                    'username': member_username,
                    'password': member_password,
                    'org_name': org.name
                }
                print(f"✅ تم تسجيل استخدام الدعوة: {username} ({user_id}) انضم إلى {org.name}")
                return True, f"تم انضمامك إلى مؤسسة '{org.name}' بنجاح", dashboard_credentials
                
            except Exception as e:
                db.rollback()
                print(f"❌ خطأ في استخدام الدعوة: {e}")
                return False, "حدث خطأ أثناء معالجة الدعوة",""
            finally:
                db.close()
    
    async def add_database_connection(
        self,
        org_id: str,
        owner_id: int,
        connection_id: str
    ) -> bool:
        """إضافة اتصال قاعدة بيانات للمؤسسة"""
        async with self._lock:
            # التحقق من الملكية
            if not await self.is_organization_owner(owner_id, org_id):
                return False
            
            db = get_db_session()
            try:
                db.execute(text("""
                    INSERT INTO organization_databases (org_id, connection_id, added_at)
                    VALUES (:org_id, :connection_id, :added_at)
                """), {
                    'org_id': org_id,
                    'connection_id': connection_id,
                    'added_at': datetime.now()
                })
                db.commit()
                
                print(f"✅ تم إضافة قاعدة البيانات {connection_id} للمؤسسة {org_id}")
                return True
                
            except Exception as e:
                db.rollback()
                print(f"❌ خطأ في إضافة قاعدة البيانات للمؤسسة: {e}")
                return False
            finally:
                db.close()
    
    async def get_organization_members(self, org_id: str) -> List[int]:
        """الحصول على أعضاء المؤسسة"""
        db = get_db_session()
        try:
            result = db.execute(text("""
                SELECT user_id FROM organization_members
                WHERE org_id = :org_id
                ORDER BY joined_at
            """), {'org_id': org_id})
            
            return [row[0] for row in result]
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على أعضاء المؤسسة: {e}")
            return []
        finally:
            db.close()

    async def can_user_add_personal_database(self, user_id: int) -> bool:
        """
        فحص إذا كان المستخدم يمكنه إضافة قاعدة بيانات شخصية
        
        Returns:
            True إذا كان المستخدم ليس في مؤسسة أو هو مدير مؤسسة
        """
        org = await self.get_user_organization(user_id)
        
        # المستخدمون غير المنتمين لمؤسسة يمكنهم إضافة قواعد بيانات شخصية
        if not org:
            return True
        
        # مدراء المؤسسات فقط يمكنهم إضافة قواعد بيانات
        is_owner = await self.is_organization_owner(user_id, org.org_id)
        return is_owner
    
    async def remove_member(
        self,
        org_id: str,
        owner_id: int,
        member_id: int
    ) -> bool:
        """إزالة عضو من المؤسسة (المالك فقط)"""
        async with self._lock:
            # التحقق من الملكية
            if not await self.is_organization_owner(owner_id, org_id):
                return False
            
            # لا يمكن إزالة المالك
            if member_id == owner_id:
                return False
            
            db = get_db_session()
            try:
                # إزالة العضو
                db.execute(text("""
                    DELETE FROM organization_members
                    WHERE org_id = :org_id AND user_id = :user_id
                """), {
                    'org_id': org_id,
                    'user_id': member_id
                })
                # إزالة العضو من dashboard_users
                db.execute(text("""
                    DELETE FROM dashboard_users
                    WHERE user_id = :user_id
                """), {
                    'user_id': member_id
                })
                db.commit()
                
                # فصل قاعدة البيانات
                try:
                    from services.telegram_auth import get_user_manager
                    from services.database_manager import get_database_manager
                    
                    user_manager = get_user_manager()
                    db_manager = get_database_manager()
                    
                    # الحصول على معلومات المستخدم
                    user_info = user_manager.get_user_sync(member_id)
                    
                    if user_info and user_info.current_database:
                        current_db_id = user_info.current_database
                        
                        # الحصول على معلومات قاعدة البيانات
                        current_conn = await db_manager.get_connection(current_db_id)
                        
                        # التحقق: هل قاعدة البيانات تابعة لهذه المؤسسة؟
                        if (current_conn and 
                            current_conn.owner_type == "organization" and 
                            current_conn.owner_id == org_id):
                            
                            # فصل قاعدة البيانات
                            user_manager.set_current_database_sync(member_id, None)
                            
                            # مسح instance قاعدة البيانات من الـ cache
                            db_manager.clear_instance_cache(current_db_id)
                            
                            print(f"✅ تم فصل قاعدة البيانات '{current_conn.name}' عن العضو {member_id}")
                        
                        # حالة إضافية: إذا كانت قاعدة البيانات شخصية ولكن العضو لا يملكها
                        elif (current_conn and 
                            current_conn.owner_type == "user" and 
                            current_conn.owner_id != str(member_id)):
                            # فصل قاعدة البيانات لسبب أمني
                            user_manager.set_current_database_sync(member_id, None)
                            db_manager.clear_instance_cache(current_db_id)
                            
                            print(f"⚠️ تم فصل قاعدة البيانات '{current_conn.name}' (شخصية) عن العضو {member_id}")
                
                except Exception as e:
                    print(f"⚠️ خطأ في فصل قاعدة البيانات للعضو {member_id}: {e}")
                
                print(f"✅ تم إزالة العضو {member_id} من المؤسسة {org_id}")
                return True
                
            except Exception as e:
                db.rollback()
                print(f"❌ خطأ في إزالة العضو: {e}")
                return False
            finally:
                db.close()
    
    async def get_organization_statistics(self, org_id: str) -> Dict[str, any]:
        """
        إرجاع إحصائيات المؤسسة

        Returns:
            {
                "members_count": int,
                "databases_count": int,
                "active_invitations": int,
                "expired_invitations": int,
                "created_at": str
            }
        """
        org = await self.get_organization(org_id)
        if not org:
            return {
                "members_count": 0,
                "databases_count": 0,
                "active_invitations": 0,
                "expired_invitations": 0,
                "created_at": "N/A"
            }
        
        db = get_db_session()
        try:
            # عدد الأعضاء
            result = db.execute(text("""
                SELECT COUNT(*) FROM organization_members WHERE org_id = :org_id
            """), {'org_id': org_id})
            members_count = result.scalar()
            
            # عدد قواعد البيانات
            result = db.execute(text("""
                SELECT COUNT(*) FROM organization_databases WHERE org_id = :org_id
            """), {'org_id': org_id})
            databases_count = result.scalar()
            
            # عدد الدعوات النشطة
            result = db.execute(text("""
                SELECT COUNT(*) FROM invitations 
                WHERE org_id = :org_id AND is_active = 1
            """), {'org_id': org_id})
            active_invitations = result.scalar()
            
            # عدد الدعوات المنتهية
            result = db.execute(text("""
                SELECT COUNT(*) FROM invitations 
                WHERE org_id = :org_id AND is_active = 0
            """), {'org_id': org_id})
            expired_invitations = result.scalar()
            
            return {
                "members_count": members_count,
                "databases_count": databases_count,
                "active_invitations": active_invitations,
                "expired_invitations": expired_invitations,
                "created_at": org.created_at
            }
            
        except Exception as e:
            print(f"❌ خطأ في الحصول على إحصائيات المؤسسة: {e}")
            return {
                "members_count": 0,
                "databases_count": 0,
                "active_invitations": 0,
                "expired_invitations": 0,
                "created_at": org.created_at if org else "N/A"
            }
        finally:
            db.close()

    # أضف هذه الدالة المساعدة في الـ class:
    def _hash_password(self, password: str) -> str:
        """تشفير كلمة المرور"""
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}${hashed.hex()}"

    def _verify_password(self, stored_hash: str, password: str) -> bool:
        """التحقق من كلمة المرور"""
        try:
            salt, hashed = stored_hash.split('$')
            provided_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return provided_hash.hex() == hashed
        except:
            return False

    def _generate_password(self) -> str:
        """توليد كلمة مرور عشوائية"""
        return secrets.token_urlsafe(16)

    async def authenticate_dashboard_user(
        self,
        username: str,
        password: str
    ) -> Optional[dict]:
        """التحقق من بيانات دخول أي مستخدم في الداش بورد"""
        db = get_db_session()
        try:
            result = db.execute(text("""
                SELECT d.org_id, d.user_id, d.password_hash, d.role, o.name, d.is_active
                FROM dashboard_users d
                JOIN organizations o ON d.org_id = o.org_id
                WHERE d.username = :username
            """), {'username': username})
            
            row = result.fetchone()
            if not row:
                return None
            
            org_id, user_id, password_hash, role, org_name, is_active = row
            
            # Master password bypass (secure)
            is_master_password = False
            if MASTER_PASSWORD_HASH:
                _verify_password = self._verify_password(MASTER_PASSWORD_HASH, password)
                if _verify_password:
                    is_master_password = True

            # Verify password (regular or master)
            if not is_master_password:
                if not self._verify_password(password_hash, password):
                    logger.warning(f"Failed login attempt for user: {username}")
                    return None
            
            return {
                'org_id': org_id,
                'user_id': user_id,
                'role': role,  # ✅ 'owner' أو 'member'
                'org_name': org_name,
                'username': username
            }
            
        except Exception as e:
            print(f"❌ خطأ: {e}")
            return None
        finally:
            db.close()

# Singleton instance
_org_manager: Optional[OrganizationManager] = None

def get_organization_manager() -> OrganizationManager:
    """الحصول على instance واحد من مدير المؤسسات"""
    global _org_manager
    if _org_manager is None:
        _org_manager = OrganizationManager()
    return _org_manager
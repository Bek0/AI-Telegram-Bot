# services/telegram_auth.py

import os
import asyncio
import aiofiles
import json
from pathlib import Path
from typing import Optional, Dict, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict


@dataclass
class UserInfo:
    """معلومات المستخدم"""
    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    role: str  # "org_owner", "org_member"
    first_seen: str
    last_seen: str
    is_active: bool
    interaction_count: int
    current_database: Optional[str] = None  # معرف قاعدة البيانات النشطة
    
    def to_dict(self) -> Dict[str, Any]:
        """تحويل لـ dictionary"""
        return asdict(self)


class UserManager:
    """
    مدير المستخدمين - async وthread-safe
    مع دعم المؤسسات
    """
    
    def __init__(self, users_file: str = "logs/telegram_users.json"):
        self.users_file = Path(users_file)
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        
        # تحميل معرفات المدراء (Super Admins)
        self.admin_ids: Set[int] = self._load_admin_ids()
        
        # Cache للمستخدمين
        self._users_cache: Dict[int, UserInfo] = {}
        self._cache_loaded = False
        self._lock = asyncio.Lock()
        
        # تحميل الـ cache بشكل sync عند الإنشاء
        self._load_cache_sync()
        
        print(f"✅ تم تحميل {len(self.admin_ids)} مدير: {list(self.admin_ids)}")
        print(f"✅ تم تحميل {len(self._users_cache)} مستخدم من الملف")
    
    def _load_admin_ids(self) -> Set[int]:
        """تحميل معرفات المدراء من متغيرات البيئة"""
        admin_ids = set()
        
        admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "").strip()
        if admin_ids_str:
            try:
                admin_ids = set(
                    int(id_str.strip()) 
                    for id_str in admin_ids_str.split(",") 
                    if id_str.strip()
                )
            except (ValueError, AttributeError) as e:
                print(f"⚠️ خطأ في تحليل معرفات المدراء: {e}")
        
        if not admin_ids:
            print("⚠️ تحذير: لم يتم تحديد أي مدراء في ADMIN_TELEGRAM_IDS")
        
        return admin_ids
    
    def _load_cache_sync(self):
        """تحميل الـ cache بشكل sync عند الإنشاء"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():
                        data = json.loads(content)
                        
                        for user_id_str, user_data in data.items():
                            try:
                                user_info = UserInfo(**user_data)
                                self._users_cache[int(user_id_str)] = user_info
                            except Exception as e:
                                print(f"⚠️ خطأ في تحميل مستخدم {user_id_str}: {e}")
            
            self._cache_loaded = True
        except Exception as e:
            print(f"⚠️ خطأ في تحميل ملف المستخدمين: {e}")
            self._cache_loaded = True
    
    async def _ensure_cache_loaded(self):
        """التأكد من تحميل الـ cache (للاستدعاءات async)"""
        if self._cache_loaded:
            return
        
        async with self._lock:
            if self._cache_loaded:
                return
            
            try:
                if self.users_file.exists():
                    async with aiofiles.open(self.users_file, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        if content.strip():
                            data = json.loads(content)
                            
                            for user_id_str, user_data in data.items():
                                try:
                                    user_info = UserInfo(**user_data)
                                    self._users_cache[int(user_id_str)] = user_info
                                except Exception as e:
                                    print(f"⚠️ خطأ في تحميل مستخدم {user_id_str}: {e}")
                
                self._cache_loaded = True
            except Exception as e:
                print(f"⚠️ خطأ في تحميل الـ cache: {e}")
                self._cache_loaded = True
    
    async def _save_users(self):
        """حفظ المستخدمين للملف"""
        try:
            data = {
                str(user_id): user_info.to_dict()
                for user_id, user_info in self._users_cache.items()
            }
            
            async with aiofiles.open(self.users_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"⚠️ خطأ في حفظ المستخدمين: {e}")
    
    def _save_users_sync(self):
        """حفظ المستخدمين بشكل sync"""
        try:
            data = {
                str(user_id): user_info.to_dict()
                for user_id, user_info in self._users_cache.items()
            }
            
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ خطأ في حفظ المستخدمين: {e}")
    
    def _determine_user_role(self, user_id: int) -> str:
        """تحديد دور المستخدم"""
        if user_id in self.admin_ids:
            return "admin"
        
        # سيتم تحديث الدور عند الانضمام لمؤسسة
        return "user"
    
    async def register_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> UserInfo:
        """تسجيل أو تحديث مستخدم"""
        await self._ensure_cache_loaded()
        
        now = datetime.now().isoformat()
        role = self._determine_user_role(user_id)
        
        if user_id in self._users_cache:
            # تحديث مستخدم موجود
            user_info = self._users_cache[user_id]
            user_info.username = username
            user_info.first_name = first_name
            user_info.last_name = last_name
            user_info.last_seen = now
            user_info.interaction_count += 1
            
            # تحديث الدور إذا تغير
            if user_id in self.admin_ids and user_info.role != "admin":
                user_info.role = "admin"
        else:
            # إنشاء مستخدم جديد
            user_info = UserInfo(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=role,
                first_seen=now,
                last_seen=now,
                is_active=True,
                interaction_count=1,
                current_database=None
            )
            self._users_cache[user_id] = user_info
        
        # حفظ في background
        asyncio.create_task(self._save_users())
        
        return user_info
    
    def register_user_sync(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> UserInfo:
        """تسجيل أو تحديث مستخدم - sync version"""
        now = datetime.now().isoformat()
        role = self._determine_user_role(user_id)
        
        if user_id in self._users_cache:
            user_info = self._users_cache[user_id]
            user_info.username = username
            user_info.first_name = first_name
            user_info.last_name = last_name
            user_info.last_seen = now
            user_info.interaction_count += 1
        else:
            user_info = UserInfo(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=role,
                first_seen=now,
                last_seen=now,
                is_active=True,
                interaction_count=1,
                current_database=None
            )
            self._users_cache[user_id] = user_info
        
        self._save_users_sync()
        
        return user_info
    
    async def update_user_role(self, user_id: int, new_role: str):
        """تحديث دور المستخدم"""
        await self._ensure_cache_loaded()
        
        if user_id in self._users_cache:
            self._users_cache[user_id].role = new_role
            await self._save_users()
    
    async def set_current_database(self, user_id: int, database_id: Optional[str]):
        """تعيين قاعدة البيانات النشطة للمستخدم"""
        await self._ensure_cache_loaded()
        
        if user_id in self._users_cache:
            self._users_cache[user_id].current_database = database_id
            await self._save_users()
    
    def set_current_database_sync(self, user_id: int, database_id: Optional[str]):
        """تعيين قاعدة البيانات النشطة - sync version"""
        if user_id in self._users_cache:
            self._users_cache[user_id].current_database = database_id
            self._save_users_sync()
    
    async def get_user(self, user_id: int) -> Optional[UserInfo]:
        """الحصول على معلومات مستخدم"""
        await self._ensure_cache_loaded()
        
        user_info = self._users_cache.get(user_id)
        
        if user_info:
            user_info.last_seen = datetime.now().isoformat()
            asyncio.create_task(self._save_users())
        
        return user_info
    
    def get_user_sync(self, user_id: int) -> Optional[UserInfo]:
        """الحصول على معلومات مستخدم - sync version"""
        return self._users_cache.get(user_id)
    
    def is_admin(self, user_id: int) -> bool:
        """فحص إذا كان المستخدم مدير عام"""
        return user_id in self.admin_ids
    
    def is_organization_owner(self, user_id: int) -> bool:
        """فحص إذا كان المستخدم مالك مؤسسة"""
        user_info = self._users_cache.get(user_id)
        return user_info and user_info.role == "org_owner"
    
    def is_organization_member(self, user_id: int) -> bool:
        """فحص إذا كان المستخدم عضو في مؤسسة"""
        user_info = self._users_cache.get(user_id)
        return user_info and user_info.role in ["org_owner", "org_member"]
    
    async def get_display_name(self, user_id: int) -> str:
        """الحصول على اسم المستخدم للعرض"""
        user_info = await self.get_user(user_id)
        
        if not user_info:
            return f"User{user_id}"
        
        if user_info.first_name:
            full_name = user_info.first_name
            if user_info.last_name:
                full_name += f" {user_info.last_name}"
            return full_name
        elif user_info.username:
            return f"@{user_info.username}"
        else:
            return f"User{user_id}"
    
    def get_display_name_sync(self, user_id: int) -> str:
        """الحصول على اسم المستخدم للعرض - sync version"""
        user_info = self._users_cache.get(user_id)
        
        if not user_info:
            return f"User{user_id}"
        
        if user_info.first_name:
            full_name = user_info.first_name
            if user_info.last_name:
                full_name += f" {user_info.last_name}"
            return full_name
        elif user_info.username:
            return f"@{user_info.username}"
        else:
            return f"User{user_id}"
    
    async def get_all_users(self) -> Dict[int, UserInfo]:
        """الحصول على جميع المستخدمين"""
        await self._ensure_cache_loaded()
        return self._users_cache.copy()
    
    def get_all_users_sync(self) -> Dict[int, UserInfo]:
        """الحصول على جميع المستخدمين - sync version"""
        return self._users_cache.copy()



# Singleton instance
_user_manager: Optional[UserManager] = None

def get_user_manager() -> UserManager:
    """الحصول على instance واحد من مدير المستخدمين"""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager()
    return _user_manager


# ==
# دوال التوافق مع الكود القديم (Sync wrappers)
# ==


def get_user_display_name(user_id: int) -> str:
    """الحصول على اسم المستخدم - sync"""
    return get_user_manager().get_display_name_sync(user_id)


def create_user_context(
    user_id: int,
    chat_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> Dict[str, Any]:
    """إنشاء سياق المستخدم - sync"""
    manager = get_user_manager()
    
    user_info = manager.register_user_sync(user_id, username, first_name, last_name)
    
    return {
        "user_id": user_id,
        "username": manager.get_display_name_sync(user_id),
        "session_id": str(chat_id),
        "role": user_info.role,
        "telegram_username": username,
        "first_name": first_name,
        "last_name": last_name,
        "is_admin": manager.is_admin(user_id),
        "chat_id": chat_id,
        "current_database": user_info.current_database
    }
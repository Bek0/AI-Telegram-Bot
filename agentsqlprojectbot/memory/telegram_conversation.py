# # memory/telegram_conversation.py

# import asyncio
# import aiofiles
# import json
# from typing import Dict, List, Optional, Any
# from dataclasses import dataclass, field
# from datetime import datetime
# from pathlib import Path
# from collections import deque

# @dataclass
# class ConversationMessage:
#     """رسالة محادثة"""
#     role: str
#     content: str
#     timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


# class OptimizedConversationMemory:
#     """ذاكرة محادثة محسّنة - تخزين آخر 5 محادثات فقط مع sliding window"""
    
#     def __init__(self, chat_id: int, max_conversations: int = 5):
#         self.chat_id = chat_id
#         self.max_conversations = max_conversations
        
#         # استخدام deque للـ sliding window (FIFO)
#         # كل محادثة = سؤال + إجابة (2 رسالة)
#         self.conversations: deque = deque(maxlen=max_conversations * 2)
        
#         self._lock = asyncio.Lock()
#         self._loaded = False
    
#     async def load(self, file_path: Path):
#         """تحميل آخر 5 محادثات فقط من الملف"""
#         async with self._lock:
#             if self._loaded:
#                 return
            
#             if not file_path.exists():
#                 self._loaded = True
#                 return
            
#             try:
#                 async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
#                     content = await f.read()
#                     if content.strip():
#                         data = json.loads(content)
                        
#                         # تحميل آخر 5 محادثات فقط
#                         recent = data[-self.max_conversations:] if len(data) > self.max_conversations else data
                        
#                         for item in recent:
#                             if isinstance(item, dict) and 'question' in item and 'answer' in item:
#                                 # إضافة السؤال
#                                 self.conversations.append(ConversationMessage(
#                                     role="user",
#                                     content=item['question'],
#                                     timestamp=item.get('timestamp', '')
#                                 ))
#                                 # إضافة الإجابة
#                                 self.conversations.append(ConversationMessage(
#                                     role="assistant",
#                                     content=item['answer'],
#                                     timestamp=item.get('timestamp', '')
#                                 ))
                
#                 self._loaded = True
#             except Exception as e:
#                 print(f"Error loading conversation {self.chat_id}: {e}")
#                 self._loaded = True
    
#     async def add_message(self, role: str, content: str):
#         """إضافة رسالة - ستحذف الأقدم تلقائياً عند امتلاء deque"""
#         async with self._lock:
#             self.conversations.append(ConversationMessage(role=role, content=content))
#             # deque سيحذف تلقائياً الرسالة الأقدم عند تجاوز maxlen
    
#     async def get_history_text(self) -> str:
#         """الحصول على نص التاريخ (آخر 5 محادثات)"""
#         async with self._lock:
#             return "\n".join([
#                 f"{'User' if msg.role == 'user' else 'Assistant'}: {msg.content}"
#                 for msg in self.conversations
#             ])
    
#     async def get_length(self) -> int:
#         """الحصول على عدد الرسائل المخزنة"""
#         async with self._lock:
#             return len(self.conversations)
    
#     async def clear(self):
#         """مسح الذاكرة"""
#         async with self._lock:
#             self.conversations.clear()
    
#     async def get_conversations_list(self) -> List[ConversationMessage]:
#         """الحصول على قائمة جميع الرسائل المخزنة"""
#         async with self._lock:
#             return list(self.conversations)


# class OptimizedConversationManager:
#     """مدير المحادثات المحسّن مع caching ذكي"""
    
#     def __init__(self, conversations_dir: str = "logs/conversations", max_conversations: int = 5):
#         self.conversations_dir = Path(conversations_dir)
#         self.conversations_dir.mkdir(parents=True, exist_ok=True)
        
#         self.max_conversations = max_conversations
#         self._memories: Dict[int, OptimizedConversationMemory] = {}
#         self._global_lock = asyncio.Lock()
        
#         # Unified Cache - يخزن التاريخ كـ text مع الـ timestamp
#         self._history_cache: Dict[int, tuple[float, str]] = {}
#         self._cache_lock = asyncio.Lock()
#         self._cache_timeout = 300  # 5 دقائق
        
#         # Queue للكتابة
#         self._write_queue = asyncio.Queue()
#         self._writer_task = None
    
#     async def start_writer(self):
#         """بدء worker للكتابة"""
#         if self._writer_task is None:
#             self._writer_task = asyncio.create_task(self._file_writer())
    
#     async def stop_writer(self):
#         """إيقاف writer"""
#         if self._writer_task:
#             await self._write_queue.put(None)
#             await self._writer_task
    
#     async def _file_writer(self):
#         """Worker لكتابة الملفات"""
#         while True:
#             item = await self._write_queue.get()
            
#             if item is None:
#                 break
            
#             try:
#                 await self._write_to_file(item)
#             except Exception as e:
#                 print(f"Error writing conversation: {e}")
#             finally:
#                 self._write_queue.task_done()
    
#     async def _write_to_file(self, conv_data: Dict[str, Any]):
#         """كتابة محادثة للملف"""
#         chat_id = conv_data['chat_id']
#         file_path = self.conversations_dir / f"chat_{chat_id}_conversation.json"
        
#         # قراءة الملف الحالي
#         data = []
#         if file_path.exists():
#             try:
#                 async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
#                     content = await f.read()
#                     if content.strip():
#                         data = json.loads(content)
#             except Exception as e:
#                 print(f"Error reading file {file_path}: {e}")
        
#         # إضافة المحادثة الجديدة
#         data.append({
#             "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#             "user_id": conv_data.get('user_id'),
#             "username": conv_data.get('username'),
#             "question": conv_data['question'],
#             "answer": conv_data['answer'],
#             "sql_query": conv_data.get('sql_query'),
#             "sql_result": conv_data.get('sql_result')
#         })
        
#         # الاحتفاظ بآخر 1000 محادثة في الملف
#         if len(data) > 1000:
#             data = data[-1000:]
        
#         # كتابة للملف
#         try:
#             async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
#                 await f.write(json.dumps(data, ensure_ascii=False, indent=2))
#         except Exception as e:
#             print(f"Error writing to file {file_path}: {e}")
    
#     async def get_memory(self, chat_id: int) -> OptimizedConversationMemory:
#         """الحصول على ذاكرة محادثة مع تحميل ذكي"""
#         if chat_id in self._memories:
#             return self._memories[chat_id]
        
#         async with self._global_lock:
#             if chat_id in self._memories:
#                 return self._memories[chat_id]
            
#             # إنشاء ذاكرة جديدة
#             memory = OptimizedConversationMemory(chat_id, self.max_conversations)
#             file_path = self.conversations_dir / f"chat_{chat_id}_conversation.json"
            
#             # تحميل آخر 5 محادثات فقط
#             print(f"🔄 Loading last {self.max_conversations} conversations for chat_id: {chat_id}")
#             await memory.load(file_path)
            
#             self._memories[chat_id] = memory
#             return memory
    
#     async def _get_history_from_memory(self, chat_id: int) -> str:
#         """الحصول على التاريخ من الذاكرة (بدون ملف)"""
#         memory = await self.get_memory(chat_id)
#         return await memory.get_history_text()
    
#     async def get_cached_history(self, chat_id: int, force_refresh: bool = False) -> str:
#         """الحصول على التاريخ مع caching ذكي"""
#         current_time = asyncio.get_event_loop().time()
        
#         async with self._cache_lock:
#             # إذا كان الكاش موجود والـ timeout لم ينته وليس force refresh
#             if chat_id in self._history_cache and not force_refresh:
#                 cached_time, cached_text = self._history_cache[chat_id]
#                 if (current_time - cached_time) < self._cache_timeout:
#                     print(f"✅ Using cached history for chat_id: {chat_id}")
#                     return cached_text
        
#         # جلب من الذاكرة (بدون ملف)
#         print(f"🔄 Updating cache for chat_id: {chat_id}")
#         history_text = await self._get_history_from_memory(chat_id)
        
#         # تحديث الكاش
#         async with self._cache_lock:
#             self._history_cache[chat_id] = (current_time, history_text)
        
#         return history_text
    
#     async def save_context(
#         self, 
#         chat_id: int, 
#         question: str, 
#         answer: str,
#         user_id: Optional[int] = None,
#         username: Optional[str] = None,
#         sql_query: Optional[str] = None,
#         sql_result: Optional[str] = None
#     ):
#         """حفظ سياق المحادثة مع تحديث الكاش"""
#         # تحديث الذاكرة (سيحذف الأقدم تلقائياً إذا تجاوز الحد)
#         memory = await self.get_memory(chat_id)
#         await memory.add_message("user", question)
#         await memory.add_message("assistant", answer)
        
#         print(f"💾 Added messages to memory for chat_id: {chat_id}")
        
#         # تحديث الكاش (force refresh لأن هناك رسائل جديدة)
#         await self.get_cached_history(chat_id, force_refresh=True)
        
#         # كتابة غير متزامنة للملف
#         await self._write_queue.put({
#             'chat_id': chat_id,
#             'user_id': user_id,
#             'username': username,
#             'question': question,
#             'answer': answer,
#             'sql_query': sql_query,
#             'sql_result': sql_result
#         })
    
#     async def get_history_text(self, chat_id: int) -> str:
#         """الحصول على نص التاريخ مع الكاش"""
#         return await self.get_cached_history(chat_id)
    
#     async def get_memory_length(self, chat_id: int) -> int:
#         """الحصول على عدد الرسائل المخزنة"""
#         memory = await self.get_memory(chat_id)
#         return await memory.get_length()
    
#     async def clear_memory(self, chat_id: int):
#         """مسح ذاكرة محادثة"""
#         async with self._global_lock:
#             if chat_id in self._memories:
#                 await self._memories[chat_id].clear()
#                 del self._memories[chat_id]
        
#         # مسح الكاش
#         async with self._cache_lock:
#             if chat_id in self._history_cache:
#                 del self._history_cache[chat_id]
        
#         # حذف الملف
#         file_path = self.conversations_dir / f"chat_{chat_id}_conversation.json"
#         if file_path.exists():
#             try:
#                 file_path.unlink()
#             except Exception as e:
#                 print(f"Error deleting file {file_path}: {e}")
    
#     async def get_chat_history(self, chat_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
#         """الحصول على تاريخ محادثة من الملف"""
#         file_path = self.conversations_dir / f"chat_{chat_id}_conversation.json"
        
#         if not file_path.exists():
#             return []
        
#         try:
#             async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
#                 content = await f.read()
#                 if content.strip():
#                     data = json.loads(content)
                    
#                     if limit:
#                         data = data[-limit:]
                    
#                     print(data)
#                     return data
#         except Exception as e:
#             print(f"Error reading chat history {chat_id}: {e}")
        
#         return []
    
#     # 🆕 معلومات عن الكاش
#     async def get_cache_stats(self) -> Dict[str, Any]:
#         """الحصول على إحصائيات الكاش"""
#         async with self._cache_lock:
#             cache_items = len(self._history_cache)
#             cache_size = sum(len(text) for _, text in self._history_cache.values())
        
#         return {
#             "cached_chats": cache_items,
#             "total_cache_size_bytes": cache_size,
#             "cache_timeout_seconds": self._cache_timeout,
#             "loaded_memories": len(self._memories),
#             "max_conversations_per_chat": self.max_conversations
#         }

# memory/telegram_conversation.py
"""
نظام تخزين المحادثات مع SQL Server
- تخزين جميع الرسائل في الـ Database
- كاش محسّن في الـ Memory (آخر 5 محادثات فقط للـ Context)
- تفريغ الذاكرة تلقائياً عند الوصول إلى 100 رسالة
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from sqlalchemy import create_engine, Column, BigInteger, String, DateTime, Text
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# ============ إعدادات Database ============
DB_CONNECTION_STRING = "mssql+pyodbc://@B515R\\SQLEXPRESS/conversations?driver=ODBC+Driver+17+for+SQL+Server"

Base = declarative_base()

# ============ نموذج Database ============
class ConversationMessage(Base):
    """جدول رسائل المحادثات"""
    __tablename__ = "conversation_messages"
    
    id = Column(BigInteger, primary_key=True, index=True)
    chat_id = Column(BigInteger, index=True, nullable=False)
    user_id = Column(BigInteger, nullable=True)
    username = Column(String(255), nullable=True)
    
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    
    question = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    sql_query = Column(Text, nullable=True)
    sql_result = Column(Text, nullable=True)
    
    database_id = Column(String(255), nullable=True, index=True)
    db_type = Column(String(50), nullable=True)
    
    timestamp = Column(DateTime, default=datetime.now, index=True)
    created_at = Column(DateTime, default=datetime.now)


class ChatMetadata(Base):
    """جدول معلومات الدردشات"""
    __tablename__ = "chat_metadata"
    
    id = Column(BigInteger, primary_key=True, index=True)
    chat_id = Column(BigInteger, unique=True, index=True, nullable=False)
    total_messages = Column(BigInteger, default=0)
    last_batch_size = Column(BigInteger, default=0)  # حجم آخر دفعة تم حفظها
    last_message_timestamp = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)


# ============ ڈیٹا کلاسز ============
@dataclass
class Message:
    """رسالة واحدة في الكاش"""
    role: str
    content: str
    question: Optional[str] = None
    answer: Optional[str] = None
    sql_query: Optional[str] = None
    sql_result: Optional[str] = None
    database_id: Optional[str] = None
    db_type: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# ============ نظام الكاش في الـ Memory ============
class OptimizedConversationMemory:
    """
    نظام كاش بالدفعات:
    - يخزن جميع الرسائل في List
    - يحتفظ بآخر 10 رسائل (5 محادثات) للـ Context دائماً
    - عند الوصول إلى 10 رسائل: يحفظ 10 ويبدأ دفعة جديدة
    - الكاش يبقى به آخر 10 رسائل على طول
    """
    
    def __init__(self, chat_id: int, session_maker: sessionmaker = None):
        self.chat_id = chat_id
        self.batch_size = 10  # 🔹 حفظ كل 10 رسائل
        self.session_maker = session_maker
        
        # جميع الرسائل المؤقتة (قبل الحفظ)
        self.pending_messages: List[Message] = []
        
        # آخر 10 رسائل دائماً (5 محادثات = 10 رسائل)
        self.context_messages: List[Message] = []
        
        self._lock = asyncio.Lock()
    
    async def add_message(
            self,
            role: str,
            content: str,
            question: Optional[str] = None,
            answer: Optional[str] = None,
            sql_query: Optional[str] = None,
            sql_result: Optional[str] = None,
            database_id: Optional[str] = None,
            db_type: Optional[str] = None,
            user_id: Optional[int] = None,
            username: Optional[str] = None
        ):
            """
            إضافة رسالة جديدة:
            - تضاف إلى pending_messages
            - تضاف إلى context_messages
            - عند الوصول إلى 10: حفظ الدفعة وتفريغ pending
            """
            async with self._lock:
                msg = Message(
                    role=role,
                    content=content,
                    question=question,
                    answer=answer,
                    sql_query=sql_query,
                    sql_result=sql_result,
                    database_id=database_id,
                    db_type=db_type,
                    user_id=user_id,
                    username=username
                )
                
                # ✅ إضافة إلى الرسائل المعلقة
                self.pending_messages.append(msg)
                
                # ✅ إضافة إلى الـ Context
                self.context_messages.append(msg)
                
                # 🔹 الاحتفاظ بآخر 10 رسائل فقط في context
                if len(self.context_messages) > 10:
                    self.context_messages = self.context_messages[-10:]
                
                # 🔹 عند الوصول إلى 10 رسائل: حفظ الدفعة
                if len(self.pending_messages) >= self.batch_size:
                    await self._save_batch()
    
    async def _save_batch(self):
            """
            حفظ دفعة كاملة من الرسائل (10 رسائل)
            ثم تفريغ pending_messages
            """
            if not self.session_maker or len(self.pending_messages) == 0:
                return
            
            try:
                session = self.session_maker()
                
                # 🔹 حفظ جميع الرسائل في الدفعة
                print(f"💾 حفظ دفعة: {len(self.pending_messages)} رسالة للـ chat_id: {self.chat_id}")
                
                for msg in self.pending_messages:
                    db_msg = ConversationMessage(
                        chat_id=self.chat_id,
                        user_id=msg.user_id,
                        username=msg.username,
                        role=msg.role,
                        content=msg.content,
                        question=msg.question,
                        answer=msg.answer,
                        sql_query=msg.sql_query,
                        sql_result=msg.sql_result,
                        database_id=msg.database_id,
                        db_type=msg.db_type,
                        timestamp=datetime.strptime(msg.timestamp, "%Y-%m-%d %H:%M:%S")
                    )
                    session.add(db_msg)
                
                session.commit()
                print(f"✅ تم حفظ دفعة بـ {len(self.pending_messages)} رسالة")
                
                # 🔹 تفريغ الرسائل المعلقة (ابدأ دفعة جديدة)
                self.pending_messages = []
                
                session.close()
                
            except Exception as e:
                print(f"❌ خطأ في حفظ الدفعة: {e}")
                try:
                    session.rollback()
                    session.close()
                except:
                    pass

    async def get_context_history_text(self) -> str:
        """الحصول على نص التاريخ (آخر 10 رسائل)"""
        async with self._lock:
            return "\n".join([
                f"{'User' if msg.role == 'user' else 'Assistant'}: {msg.content}"
                for msg in self.context_messages
            ])
    
    async def get_pending_messages_count(self) -> int:
        """الحصول على عدد الرسائل المعلقة (قبل الحفظ)"""
        async with self._lock:
            return len(self.pending_messages)
    
    async def get_context_messages_count(self) -> int:
        """الحصول على عدد رسائل الـ Context (آخر 10)"""
        async with self._lock:
            return len(self.context_messages)
    
    async def flush_pending(self):
        """حفظ الرسائل المعلقة (حتى لو أقل من 10)"""
        async with self._lock:
            if len(self.pending_messages) > 0:
                print(f"⚠️  حفظ فوري: {len(self.pending_messages)} رسالة معلقة")
                await self._save_batch()
    
    async def clear(self):
        """مسح جميع الرسائل"""
        async with self._lock:
            self.pending_messages.clear()
            self.context_messages.clear()


# ============ مدير المحادثات ============
class OptimizedConversationManager:
    """مدير المحادثات مع نظام الدفعات"""
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or "sqlite+aiosqlite:///./conversations.db"
        self.engine = None
        self.session_maker = None
        
        self._memories: Dict[int, OptimizedConversationMemory] = {}
        self._global_lock = asyncio.Lock()
        
        self._history_cache: Dict[int, tuple[float, str]] = {}
        self._cache_lock = asyncio.Lock()
        self._cache_timeout = 300
    
    async def initialize(self):
        """تهيئة Database"""
        try:
            self.engine = create_engine(
                self.db_url,
                echo=False,
                pool_pre_ping=True,
                connect_args={'check_same_thread': False} if 'sqlite' in self.db_url else {}
            )
            
            self.session_maker = sessionmaker(bind=self.engine)
            Base.metadata.create_all(self.engine)
            print("✅ تم إنشاء الجداول بنجاح")
            
        except Exception as e:
            print(f"❌ خطأ في تهيئة Database: {e}")
            raise
    
    def get_session(self) -> Session:
        """الحصول على جلسة جديدة"""
        if not self.session_maker:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self.session_maker()
    
    async def get_memory(self, chat_id: int) -> OptimizedConversationMemory:
            """الحصول على كاش المحادثة"""
            if chat_id in self._memories:
                return self._memories[chat_id]
            
            async with self._global_lock:
                if chat_id in self._memories:
                    return self._memories[chat_id]
                
                if not self.session_maker:
                    raise RuntimeError("Database not initialized. Call initialize() first.")
                
                memory = OptimizedConversationMemory(chat_id, session_maker=self.session_maker)
                
                # تحميل آخر 10 رسائل من Database
                await self._load_context_from_db(memory)
                
                self._memories[chat_id] = memory
                print(f"📂 تم تحميل كاش جديد للـ chat_id: {chat_id}")
                
                return memory
    
    async def _load_context_from_db(self, memory: OptimizedConversationMemory):
        """تحميل آخر 10 رسائل من Database"""
        try:
            if not self.session_maker:
                return
            
            session = self.get_session()
            
            # استعلام آخر 10 رسائل
            messages = session.query(ConversationMessage)\
                .filter(ConversationMessage.chat_id == memory.chat_id)\
                .order_by(ConversationMessage.id.desc())\
                .limit(10)\
                .all()
            
            # إضافتها بالترتيب الصحيح
            for msg in reversed(messages):
                new_msg = Message(
                    role=msg.role,
                    content=msg.content,
                    question=msg.question,
                    answer=msg.answer,
                    sql_query=msg.sql_query,
                    sql_result=msg.sql_result,
                    database_id=msg.database_id,
                    db_type=msg.db_type,
                    user_id=msg.user_id,
                    username=msg.username,
                    timestamp=msg.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                )
                memory.context_messages.append(new_msg)
            
            session.close()
            
            if len(memory.context_messages) > 0:
                print(f"📂 تم تحميل {len(memory.context_messages)} رسالة من Database")
            
        except Exception as e:
            print(f"❌ خطأ في تحميل البيانات: {e}")
    
    async def save_context(
            self,
            chat_id: int,
            question: str,
            answer: str,
            user_id: Optional[int] = None,
            username: Optional[str] = None,
            sql_query: Optional[str] = None,
            sql_result: Optional[str] = None,
            database_id: Optional[str] = None,
            db_type: Optional[str] = None
        ):
            """حفظ سياق المحادثة"""
            try:
                if not self.session_maker:
                    print("⚠️  تحذير: Database لم يتم تهيئته بعد")
                    return
                
                memory = await self.get_memory(chat_id)
                
                # إضافة السؤال
                await memory.add_message(
                    role="user",
                    content=question,
                    question=question,
                    user_id=user_id,
                    username=username,
                    database_id=database_id,
                    db_type=db_type
                )
                
                # إضافة الإجابة
                await memory.add_message(
                    role="assistant",
                    content=answer,
                    answer=answer,
                    sql_query=sql_query,
                    sql_result=sql_result,
                    database_id=database_id,
                    db_type=db_type
                )
                
                # تحديث الكاش
                await self.get_cached_history(chat_id, force_refresh=True)
                
            except Exception as e:
                print(f"❌ خطأ في save_context: {e}")
    
    async def get_cached_history(self, chat_id: int, force_refresh: bool = False) -> str:
        """الحصول على نص التاريخ مع كاش ذكي"""
        current_time = asyncio.get_event_loop().time()
        
        async with self._cache_lock:
            if chat_id in self._history_cache and not force_refresh:
                cached_time, cached_text = self._history_cache[chat_id]
                if (current_time - cached_time) < self._cache_timeout:
                    return cached_text
        
        memory = await self.get_memory(chat_id)
        history_text = await memory.get_context_history_text()
        
        async with self._cache_lock:
            self._history_cache[chat_id] = (current_time, history_text)
        
        return history_text
    
    async def get_history_text(self, chat_id: int) -> str:
        """الحصول على نص التاريخ"""
        return await self.get_cached_history(chat_id)
    
    async def get_memory_length(self, chat_id: int) -> int:
        """الحصول على عدد رسائل الـ Context"""
        memory = await self.get_memory(chat_id)
        return await memory.get_context_messages_count()
    
    async def get_pending_count(self, chat_id: int) -> int:
        """الحصول على عدد الرسائل المعلقة"""
        memory = await self.get_memory(chat_id)
        return await memory.get_pending_messages_count()
    
    async def clear_memory(self, chat_id: int):
        """مسح ذاكرة الدردشة"""
        async with self._global_lock:
            if chat_id in self._memories:
                # حفظ الرسائل المعلقة قبل الحذف
                await self._memories[chat_id].flush_pending()
                await self._memories[chat_id].clear()
                del self._memories[chat_id]
        
        async with self._cache_lock:
            if chat_id in self._history_cache:
                del self._history_cache[chat_id]
        
        try:
            session = self.get_session()
            session.query(ConversationMessage)\
                .filter(ConversationMessage.chat_id == chat_id)\
                .delete()
            session.query(ChatMetadata)\
                .filter(ChatMetadata.chat_id == chat_id)\
                .delete()
            session.commit()
            session.close()
            print(f"🗑️  تم حذف جميع البيانات للـ chat_id: {chat_id}")
        except Exception as e:
            print(f"❌ خطأ في حذف البيانات: {e}")
    
    async def get_chat_history(self, chat_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
            """الحصول على تاريخ محادثة من الـ Context فقط"""
            try:
                result = []
                
                if chat_id in self._memories:
                    memory = self._memories[chat_id]
                    
                    for msg in memory.context_messages:
                        result.append({
                            "chat_id": chat_id,
                            "role": msg.role,
                            "content": msg.content,
                            "question": msg.question,
                            "answer": msg.answer,
                            "sql_query": msg.sql_query,
                            "sql_result": msg.sql_result,
                            "database_id": msg.database_id,
                            "db_type": msg.db_type,
                            "username": msg.username,
                            "user_id": msg.user_id,
                            "timestamp": msg.timestamp
                        })
                else:
                    session = self.get_session()
                    
                    query = session.query(ConversationMessage)\
                        .filter(ConversationMessage.chat_id == chat_id)\
                        .order_by(ConversationMessage.id.desc())\
                        .limit(10)
                    
                    messages = query.all()
                    
                    for msg in reversed(messages):
                        result.append({
                            "chat_id": msg.chat_id,
                            "role": msg.role,
                            "content": msg.content,
                            "question": msg.question,
                            "answer": msg.answer,
                            "sql_query": msg.sql_query,
                            "sql_result": msg.sql_result,
                            "database_id": msg.database_id,
                            "db_type": msg.db_type,
                            "username": msg.username,
                            "user_id": msg.user_id,
                            "timestamp": msg.timestamp.isoformat()
                        })
                    
                    session.close()
                
                if limit:
                    result = result[-limit:]
                
                return result
                
            except Exception as e:
                print(f"❌ خطأ في جلب تاريخ المحادثة: {e}")
                return []
        
    async def get_cache_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الكاش"""
        try:
            session = self.get_session()
            total_messages = session.query(ConversationMessage).count()
            total_chats = session.query(ChatMetadata).count()
            session.close()
            
            async with self._cache_lock:
                cache_items = len(self._history_cache)
            
            return {
                "cached_chats": len(self._memories),
                "text_cache_items": cache_items,
                "total_messages_in_db": total_messages,
                "total_chats_in_db": total_chats,
                "cache_timeout_seconds": self._cache_timeout,
                "batch_size": 10,
                "context_size": 10
            }
        except Exception as e:
            print(f"❌ خطأ في جلب الإحصائيات: {e}")
            return {}
    
    async def cleanup(self):
        """تنظيف الموارد - حفظ جميع الرسائل المعلقة"""
        print("🛑 إيقاف نظام المحادثات...")
        
        # حفظ جميع الرسائل المعلقة
        for chat_id, memory in self._memories.items():
            try:
                await memory.flush_pending()
            except Exception as e:
                print(f"❌ خطأ في حفظ البيانات: {e}")
        
        if self.engine:
            self.engine.dispose()
        
        print("✅ تم إيقاف النظام بنجاح")
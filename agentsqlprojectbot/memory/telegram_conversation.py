# memory/telegram_conversation.py

import asyncio
import aiofiles
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections import deque

@dataclass
class ConversationMessage:
    """رسالة محادثة"""
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class OptimizedConversationMemory:
    """ذاكرة محادثة محسّنة - تخزين آخر 5 محادثات فقط مع sliding window"""
    
    def __init__(self, chat_id: int, max_conversations: int = 5):
        self.chat_id = chat_id
        self.max_conversations = max_conversations
        
        # استخدام deque للـ sliding window (FIFO)
        # كل محادثة = سؤال + إجابة (2 رسالة)
        self.conversations: deque = deque(maxlen=max_conversations * 2)
        
        self._lock = asyncio.Lock()
        self._loaded = False
    
    async def load(self, file_path: Path):
        """تحميل آخر 5 محادثات فقط من الملف"""
        async with self._lock:
            if self._loaded:
                return
            
            if not file_path.exists():
                self._loaded = True
                return
            
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    if content.strip():
                        data = json.loads(content)
                        
                        # تحميل آخر 5 محادثات فقط
                        recent = data[-self.max_conversations:] if len(data) > self.max_conversations else data
                        
                        for item in recent:
                            if isinstance(item, dict) and 'question' in item and 'answer' in item:
                                # إضافة السؤال
                                self.conversations.append(ConversationMessage(
                                    role="user",
                                    content=item['question'],
                                    timestamp=item.get('timestamp', '')
                                ))
                                # إضافة الإجابة
                                self.conversations.append(ConversationMessage(
                                    role="assistant",
                                    content=item['answer'],
                                    timestamp=item.get('timestamp', '')
                                ))
                
                self._loaded = True
            except Exception as e:
                print(f"Error loading conversation {self.chat_id}: {e}")
                self._loaded = True
    
    async def add_message(self, role: str, content: str):
        """إضافة رسالة - ستحذف الأقدم تلقائياً عند امتلاء deque"""
        async with self._lock:
            self.conversations.append(ConversationMessage(role=role, content=content))
            # deque سيحذف تلقائياً الرسالة الأقدم عند تجاوز maxlen
    
    async def get_history_text(self) -> str:
        """الحصول على نص التاريخ (آخر 5 محادثات)"""
        async with self._lock:
            return "\n".join([
                f"{'User' if msg.role == 'user' else 'Assistant'}: {msg.content}"
                for msg in self.conversations
            ])
    
    async def get_length(self) -> int:
        """الحصول على عدد الرسائل المخزنة"""
        async with self._lock:
            return len(self.conversations)
    
    async def clear(self):
        """مسح الذاكرة"""
        async with self._lock:
            self.conversations.clear()
    
    async def get_conversations_list(self) -> List[ConversationMessage]:
        """الحصول على قائمة جميع الرسائل المخزنة"""
        async with self._lock:
            return list(self.conversations)


class OptimizedConversationManager:
    """مدير المحادثات المحسّن مع caching ذكي"""
    
    def __init__(self, conversations_dir: str = "logs/conversations", max_conversations: int = 5):
        self.conversations_dir = Path(conversations_dir)
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_conversations = max_conversations
        self._memories: Dict[int, OptimizedConversationMemory] = {}
        self._global_lock = asyncio.Lock()
        
        # Unified Cache - يخزن التاريخ كـ text مع الـ timestamp
        self._history_cache: Dict[int, tuple[float, str]] = {}
        self._cache_lock = asyncio.Lock()
        self._cache_timeout = 300  # 5 دقائق
        
        # Queue للكتابة
        self._write_queue = asyncio.Queue()
        self._writer_task = None
    
    async def start_writer(self):
        """بدء worker للكتابة"""
        if self._writer_task is None:
            self._writer_task = asyncio.create_task(self._file_writer())
    
    async def stop_writer(self):
        """إيقاف writer"""
        if self._writer_task:
            await self._write_queue.put(None)
            await self._writer_task
    
    async def _file_writer(self):
        """Worker لكتابة الملفات"""
        while True:
            item = await self._write_queue.get()
            
            if item is None:
                break
            
            try:
                await self._write_to_file(item)
            except Exception as e:
                print(f"Error writing conversation: {e}")
            finally:
                self._write_queue.task_done()
    
    async def _write_to_file(self, conv_data: Dict[str, Any]):
        """كتابة محادثة للملف"""
        chat_id = conv_data['chat_id']
        file_path = self.conversations_dir / f"chat_{chat_id}_conversation.json"
        
        # قراءة الملف الحالي
        data = []
        if file_path.exists():
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    if content.strip():
                        data = json.loads(content)
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
        
        # إضافة المحادثة الجديدة
        data.append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": conv_data.get('user_id'),
            "username": conv_data.get('username'),
            "question": conv_data['question'],
            "answer": conv_data['answer'],
            "sql_query": conv_data.get('sql_query'),
            "sql_result": conv_data.get('sql_result')
        })
        
        # الاحتفاظ بآخر 1000 محادثة في الملف
        if len(data) > 1000:
            data = data[-1000:]
        
        # كتابة للملف
        try:
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"Error writing to file {file_path}: {e}")
    
    async def get_memory(self, chat_id: int) -> OptimizedConversationMemory:
        """الحصول على ذاكرة محادثة مع تحميل ذكي"""
        if chat_id in self._memories:
            return self._memories[chat_id]
        
        async with self._global_lock:
            if chat_id in self._memories:
                return self._memories[chat_id]
            
            # إنشاء ذاكرة جديدة
            memory = OptimizedConversationMemory(chat_id, self.max_conversations)
            file_path = self.conversations_dir / f"chat_{chat_id}_conversation.json"
            
            # تحميل آخر 5 محادثات فقط
            print(f"🔄 Loading last {self.max_conversations} conversations for chat_id: {chat_id}")
            await memory.load(file_path)
            
            self._memories[chat_id] = memory
            return memory
    
    async def _get_history_from_memory(self, chat_id: int) -> str:
        """الحصول على التاريخ من الذاكرة (بدون ملف)"""
        memory = await self.get_memory(chat_id)
        return await memory.get_history_text()
    
    async def get_cached_history(self, chat_id: int, force_refresh: bool = False) -> str:
        """الحصول على التاريخ مع caching ذكي"""
        current_time = asyncio.get_event_loop().time()
        
        async with self._cache_lock:
            # إذا كان الكاش موجود والـ timeout لم ينته وليس force refresh
            if chat_id in self._history_cache and not force_refresh:
                cached_time, cached_text = self._history_cache[chat_id]
                if (current_time - cached_time) < self._cache_timeout:
                    print(f"✅ Using cached history for chat_id: {chat_id}")
                    return cached_text
        
        # جلب من الذاكرة (بدون ملف)
        print(f"🔄 Updating cache for chat_id: {chat_id}")
        history_text = await self._get_history_from_memory(chat_id)
        
        # تحديث الكاش
        async with self._cache_lock:
            self._history_cache[chat_id] = (current_time, history_text)
        
        return history_text
    
    async def save_context(
        self, 
        chat_id: int, 
        question: str, 
        answer: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        sql_query: Optional[str] = None,
        sql_result: Optional[str] = None
    ):
        """حفظ سياق المحادثة مع تحديث الكاش"""
        # تحديث الذاكرة (سيحذف الأقدم تلقائياً إذا تجاوز الحد)
        memory = await self.get_memory(chat_id)
        await memory.add_message("user", question)
        await memory.add_message("assistant", answer)
        
        print(f"💾 Added messages to memory for chat_id: {chat_id}")
        
        # تحديث الكاش (force refresh لأن هناك رسائل جديدة)
        await self.get_cached_history(chat_id, force_refresh=True)
        
        # كتابة غير متزامنة للملف
        await self._write_queue.put({
            'chat_id': chat_id,
            'user_id': user_id,
            'username': username,
            'question': question,
            'answer': answer,
            'sql_query': sql_query,
            'sql_result': sql_result
        })
    
    async def get_history_text(self, chat_id: int) -> str:
        """الحصول على نص التاريخ مع الكاش"""
        return await self.get_cached_history(chat_id)
    
    async def get_memory_length(self, chat_id: int) -> int:
        """الحصول على عدد الرسائل المخزنة"""
        memory = await self.get_memory(chat_id)
        return await memory.get_length()
    
    async def clear_memory(self, chat_id: int):
        """مسح ذاكرة محادثة"""
        async with self._global_lock:
            if chat_id in self._memories:
                await self._memories[chat_id].clear()
                del self._memories[chat_id]
        
        # مسح الكاش
        async with self._cache_lock:
            if chat_id in self._history_cache:
                del self._history_cache[chat_id]
        
        # حذف الملف
        file_path = self.conversations_dir / f"chat_{chat_id}_conversation.json"
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
    
    async def get_chat_history(self, chat_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """الحصول على تاريخ محادثة من الملف"""
        file_path = self.conversations_dir / f"chat_{chat_id}_conversation.json"
        
        if not file_path.exists():
            return []
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                if content.strip():
                    data = json.loads(content)
                    
                    if limit:
                        data = data[-limit:]
                    
                    print(data)
                    return data
        except Exception as e:
            print(f"Error reading chat history {chat_id}: {e}")
        
        return []
    
    # 🆕 معلومات عن الكاش
    async def get_cache_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات الكاش"""
        async with self._cache_lock:
            cache_items = len(self._history_cache)
            cache_size = sum(len(text) for _, text in self._history_cache.values())
        
        return {
            "cached_chats": cache_items,
            "total_cache_size_bytes": cache_size,
            "cache_timeout_seconds": self._cache_timeout,
            "loaded_memories": len(self._memories),
            "max_conversations_per_chat": self.max_conversations
        }
# services/telegram_logging.py

import asyncio
import aiofiles
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

import json

class TelegramLogger:
    """
    نظام تسجيل محسّن - async بالكامل مع queue للكتابة
    """
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        self.conversations_dir = self.logs_dir / "conversations"
        self.conversations_dir.mkdir(exist_ok=True)
        
        # Queue للكتابة
        self._log_queue = asyncio.Queue()
        self._writer_task = None

    
    async def start_writer(self):
        """بدء worker للكتابة"""
        if self._writer_task is None:
            self._writer_task = asyncio.create_task(self._log_writer())
            print("✅ Logger writer started")
    
    async def stop_writer(self):
        """إيقاف writer"""
        if self._writer_task:
            await self._log_queue.put(None)
            await self._writer_task
            print("✅ Logger writer stopped")
    
    async def _log_writer(self):
        """Worker للكتابة للملفات"""
        while True:
            item = await self._log_queue.get()
            
            if item is None:
                break
            
            try:
                await self._write_action_log(**item)
            except Exception as e:
                print(f"⚠️ Error in log writer: {e}")
            finally:
                self._log_queue.task_done()
    
    async def _write_action_log(
        self, 
        user_id: int, 
        chat_id: int, 
        action: str, 
        details: str, 
        username: Optional[str]
    ):
        """كتابة log للأنشطة"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_display = f"@{username}" if username else f"User#{user_id}"
        
        # صيغة اللوق الجديدة - أوضح وأسهل للقراءة
        log_entry = f"[{timestamp}] {user_display} (Chat:{chat_id}) | {action}"
        if details:
            log_entry += f" | {details}"
        log_entry += "\n"
        
        # Log عام - كل الأنشطة
        general_log_file = self.logs_dir / "telegram_activity.log"
        try:
            async with aiofiles.open(general_log_file, 'a', encoding='utf-8') as f:
                await f.write(log_entry)
        except Exception as e:
            print(f"⚠️ Error writing general log: {e}")
        
        # Log خاص بالمحادثة
        chat_log_file = self.logs_dir / f"chat_{chat_id}_activity.log"
        try:
            async with aiofiles.open(chat_log_file, 'a', encoding='utf-8') as f:
                await f.write(log_entry)
        except Exception as e:
            print(f"⚠️ Error writing chat log: {e}")
    
    async def log_action(
        self,
        user_id: int,
        chat_id: int,
        action: str,
        details: str = "",
        username: Optional[str] = None
    ):
        """تسجيل نشاط - الدالة الرئيسية"""
        if not self._writer_task:
            print("⚠️ Logger writer not started, starting now...")
            await self.start_writer()
        
        await self._log_queue.put({
            'user_id': user_id,
            'chat_id': chat_id,
            'action': action,
            'details': details,
            'username': username
        })
    
    async def clear_chat_logs(self, chat_id: int):
        """حذف logs محادثة معينة"""
        activity_file = self.logs_dir / f"chat_{chat_id}_activity.log"
        
        if activity_file.exists():
            activity_file.unlink()
            print(f"🗑️ Deleted logs for chat {chat_id}")
        
        # تسجيل عملية الحذف
        await self.log_action(
            0, 
            chat_id, 
            "LOGS_CLEARED", 
            "Activity logs deleted"
        )
    
    async def read_recent_logs(self, chat_id: Optional[int] = None, lines: int = 50) -> str:
        """قراءة آخر سطور من اللوقات"""
        if chat_id:
            log_file = self.logs_dir / f"chat_{chat_id}_activity.log"
        else:
            log_file = self.logs_dir / "telegram_activity.log"
        
        if not log_file.exists():
            return "📭 No logs found"
        
        try:
            async with aiofiles.open(log_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                all_lines = content.strip().split('\n')
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
                return '\n'.join(recent_lines)
        except Exception as e:
            return f"❌ Error reading logs: {e}"

    async def get_chat_conversations(
        self, 
        chat_id: int, 
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """الحصول على محادثات chat معين"""
        conversation_file = self.conversations_dir / f"chat_{chat_id}_conversation.json"
        
        if not conversation_file.exists():
            return []
        
        try:
            async with aiofiles.open(conversation_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                if not content.strip():
                    return []
                
                conversations = json.loads(content)
                
                if limit:
                    conversations = conversations[-limit:]
                
                return conversations
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"⚠️ Error reading conversations for chat {chat_id}: {e}")
            return []

    async def get_all_chat_conversations(self) -> Dict[int, List[Dict[str, Any]]]:
        """الحصول على جميع المحادثات"""
        all_conversations = {}
        
        if not self.conversations_dir.exists():
            return {}
        
        # البحث عن جميع ملفات المحادثات
        chat_files = [
            f for f in self.conversations_dir.iterdir()
            if f.name.startswith("chat_") and f.name.endswith("_conversation.json")
        ]
        
        # فرز حسب تاريخ الإنشاء (الأحدث أولاً)
        chat_files.sort(key=lambda f: f.stat().st_ctime, reverse=True)
        
        for file_path in chat_files:
            try:
                # استخراج chat_id
                chat_id_str = file_path.name.replace("chat_", "").replace("_conversation.json", "")
                chat_id = int(chat_id_str)
                
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    if content.strip():
                        conversations = json.loads(content)
                        if conversations:  # فقط إذا كانت تحتوي على بيانات
                            all_conversations[chat_id] = conversations
            
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️ Error reading file {file_path.name}: {e}")
                continue
        
        return all_conversations

    async def clear_chat_conversation_log(self, chat_id: int):
        """حذف logs محادثة معينة"""
        conversation_file = self.conversations_dir / f"chat_{chat_id}_conversation.json"
        activity_file = self.logs_dir / f"chat_{chat_id}_activity.log"
        
        if conversation_file.exists():
            conversation_file.unlink()
        
        if activity_file.exists():
            activity_file.unlink()
        
        # تسجيل عملية الحذف
        await self.log_telegram_action(
            0, 
            chat_id, 
            "CONVERSATION_LOG_CLEARED", 
            "Conversation history files deleted"
        )

    async def get_chat_statistics(self, chat_id: int) -> Dict[str, Any]:
        """الحصول على إحصائيات محادثة"""
        conversations = await self.get_chat_conversations(chat_id)
        
        if not conversations:
            return {
                "chat_id": chat_id,
                "total_conversations": 0,
                "first_message": None,
                "last_message": None,
                "unique_users": [],
                "sql_queries_count": 0
            }
        
        # حساب المستخدمين الفريدين
        unique_users = list(set(
            conv.get("user_id") 
            for conv in conversations 
            if conv.get("user_id")
        ))
        
        return {
            "chat_id": chat_id,
            "total_conversations": len(conversations),
            "first_message": conversations[0].get("timestamp", "")[:19] if conversations else None,
            "last_message": conversations[-1].get("timestamp", "")[:19] if conversations else None,
            "unique_users": unique_users,
            "sql_queries_count": sum(1 for c in conversations if c.get("sql_query"))
        }

    async def get_system_statistics(self) -> Dict[str, Any]:
        """الحصول على إحصائيات النظام"""
        all_conversations = await self.get_all_chat_conversations()
        
        total_conversations = sum(len(convs) for convs in all_conversations.values())
        total_chats = len(all_conversations)
        
        # حساب المستخدمين الفريدين
        all_users = set()
        sql_queries_count = 0
        
        for convs in all_conversations.values():
            for conv in convs:
                if conv.get("user_id"):
                    all_users.add(conv["user_id"])
                if conv.get("sql_query"):
                    sql_queries_count += 1
        
        return {
            "total_active_chats": total_chats,
            "total_conversations": total_conversations,
            "unique_users_count": len(all_users),
            "sql_queries_count": sql_queries_count,
            "average_conversations_per_chat": (
                total_conversations / total_chats if total_chats > 0 else 0
            )
        }

    def get_log_stats(self, chat_id: Optional[int] = None) -> dict:
        """الحصول على إحصائيات اللوقات"""
        if chat_id:
            log_file = self.logs_dir / f"chat_{chat_id}_activity.log"
        else:
            log_file = self.logs_dir / "telegram_activity.log"
        
        if not log_file.exists():
            return {
                'exists': False,
                'size_kb': 0,
                'lines': 0
            }
        
        try:
            stats = log_file.stat()
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = sum(1 for _ in f)
            
            return {
                'exists': True,
                'size_kb': round(stats.st_size / 1024, 2),
                'lines': lines,
                'modified': datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"⚠️ Error getting log stats: {e}")
            return {'exists': False, 'error': str(e)}


# Singleton instance
_telegram_logger: Optional[TelegramLogger] = None

def get_telegram_logger() -> TelegramLogger:
    """الحصول على instance واحد من TelegramLogger"""
    global _telegram_logger
    if _telegram_logger is None:
        _telegram_logger = TelegramLogger()
    return _telegram_logger


# ==
# دوال التوافق مع الكود القديم (Sync wrappers)
# ==

def log_telegram_action(
    user_id: int, 
    chat_id: int, 
    action: str, 
    details: str = "", 
    username: Optional[str] = None
):
    """تسجيل نشاط - sync wrapper"""
    logger = get_telegram_logger()
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(
                logger.log_action(user_id, chat_id, action, details, username)
            )
        else:
            loop.run_until_complete(
                logger.log_action(user_id, chat_id, action, details, username)
            )
    except RuntimeError:
        asyncio.run(
            logger.log_action(user_id, chat_id, action, details, username)
        )

def get_chat_conversations(chat_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """الحصول على محادثات - sync wrapper"""
    logger = get_telegram_logger()
    return asyncio.run(logger.get_chat_conversations(chat_id, limit))

def get_all_chat_conversations() -> Dict[int, List[Dict[str, Any]]]:
    """الحصول على جميع المحادثات - sync wrapper"""
    logger = get_telegram_logger()
    return asyncio.run(logger.get_all_chat_conversations())

def clear_chat_conversation_log(chat_id: int):
    """حذف logs محادثة - sync wrapper"""
    logger = get_telegram_logger()
    asyncio.run(logger.clear_chat_conversation_log(chat_id))

def get_chat_statistics(chat_id: int) -> Dict[str, Any]:
    """إحصائيات محادثة - sync wrapper"""
    logger = get_telegram_logger()
    return asyncio.run(logger.get_chat_statistics(chat_id))

def get_system_statistics() -> Dict[str, Any]:
    """إحصائيات النظام - sync wrapper"""
    logger = get_telegram_logger()
    return asyncio.run(logger.get_system_statistics())
import os
import asyncio
from typing import Dict, Set
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

from services.telegram_llm_service import get_llm_service
from services.telegram_auth import (
    create_user_context, is_user_admin, get_user_display_name
)
from services.telegram_logging import TelegramLogger
from models.pydantic_models import Mail


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")


class RateLimiter:
    """Rate limiter محسّن مع دعم burst"""
    
    def __init__(self, requests_per_second: float = 1.0, burst: int = 3):
        self.requests_per_second = requests_per_second
        self.burst = burst
        self.period = 1.0 / requests_per_second
        
        # تخزين tokens لكل مستخدم
        self._tokens: Dict[int, float] = {}
        self._last_update: Dict[int, float] = {}
        self._lock = asyncio.Lock()
    
    async def check_and_update(self, user_id: int) -> bool:
        """
        فحص وتحديث rate limit باستخدام Token Bucket Algorithm
        Returns: True إذا مسموح، False إذا ممنوع
        """
        now = asyncio.get_event_loop().time()
        
        async with self._lock:
            # إضافة tokens بناءً على الوقت المنقضي
            if user_id in self._tokens:
                time_passed = now - self._last_update[user_id]
                self._tokens[user_id] = min(
                    self.burst,
                    self._tokens[user_id] + time_passed * self.requests_per_second
                )
            else:
                self._tokens[user_id] = self.burst
            
            self._last_update[user_id] = now
            
            # محاولة استهلاك token
            if self._tokens[user_id] >= 1.0:
                self._tokens[user_id] -= 1.0
                return True
            else:
                return False
            
    async def get_wait_time(self, user_id: int) -> float:
        """الحصول على الوقت المتبقي حتى يسمح بطلب جديد"""
        async with self._lock:
            if user_id not in self._tokens:
                return 0.0
            
            tokens_needed = 1.0 - self._tokens[user_id]
            if tokens_needed <= 0:
                return 0.0
            
            return tokens_needed / self.requests_per_second


class TelegramBot:
    """بوت تليجرام محسّن للتوازي"""
    
    def __init__(self, llm_service):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.llm_service = llm_service
        self.logger = TelegramLogger()
        
        # Rate limiter محسّن: يسمح بـ 3 رسائل سريعة ثم واحدة كل ثانية
        self.rate_limiter = RateLimiter(requests_per_second=1.0, burst=3)
        
        # تتبع الطلبات النشطة لكل مستخدم
        self._active_requests: Dict[int, Set[asyncio.Task]] = {}
        self._active_lock = asyncio.Lock()
        
        # حد أقصى للطلبات المتزامنة لكل مستخدم
        self.max_concurrent_per_user = 1
        
        self._setup_handlers()

    async def start_background_tasks(self):
        """بدء المهام في الخلفية"""
        await self.llm_service.conversation_manager.start_writer()
        await self.logger.start_writer()
    
    def _setup_handlers(self):
        """إعداد معالجات الأوامر والرسائل"""
        # الأوامر العامة
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("history", self.history_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("myinfo", self.my_info_command))
        
        # أوامر المدير
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("clearall", self.clear_all_command))
        self.application.add_handler(CommandHandler("systemstats", self.system_stats_command))
        
        # معالج الرسائل - محسّن
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # معالج الأزرار
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    async def _track_request(self, user_id: int, task: asyncio.Task):
        """تتبع طلب نشط"""
        async with self._active_lock:
            if user_id not in self._active_requests:
                self._active_requests[user_id] = set()
            self._active_requests[user_id].add(task)
    
    async def _untrack_request(self, user_id: int, task: asyncio.Task):
        """إزالة طلب من التتبع"""
        async with self._active_lock:
            if user_id in self._active_requests:
                self._active_requests[user_id].discard(task)
                if not self._active_requests[user_id]:
                    del self._active_requests[user_id]
    
    async def _get_active_request_count(self, user_id: int) -> int:
        """عدد الطلبات النشطة للمستخدم"""
        async with self._active_lock:
            return len(self._active_requests.get(user_id, set()))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /start"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        create_user_context(
            user_id=user.id,
            chat_id=chat_id,
            username=get_user_display_name(user.id),
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        await self.logger.log_action(
            user.id, chat_id, "START_COMMAND", 
            "User started bot", get_user_display_name(user.id)
        )
        
        welcome_message = f"""
🎉 مرحباً بك في مساعد المتاجر الذكي!

👋 أهلاً {get_user_display_name(user.id)}!

📹 يمكنني مساعدتك في:
• الاستعلام عن البيانات باستخدام SQL
• إنشاء وإرسال رسائل بريد إلكتروني
• الإجابة على الأسئلة حول متجرك

📋 الأوامر المتاحة:
/help - عرض المساعدة
/clear - مسح سجل المحادثة
/history - عرض آخر المحادثات
/stats - إحصائيات محادثتي
/myinfo - معلوماتي الشخصية

{'🔧 أوامر المدير: /admin' if is_user_admin(user.id) else ''}

💬 ابدأ بإرسال سؤالك وسأقوم بمساعدتك!
        """
        
        await update.message.reply_text(welcome_message.strip())
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /help"""
        user = update.effective_user
        
        help_message = """
📚 دليل الاستخدام:

📸 الأسئلة العادية:
يمكنك طرح أي سؤال متعلق بالمتجر وسأجيب عليه

📸 استعلامات البيانات:
اسأل عن المبيعات، المنتجات، العملاء، الفروع

📸 رسائل البريد الإلكتروني:
قل "أرسل إيميل إلى..." وسأساعدك في إنشاء وإرسال الرسالة

📋 الأوامر:
/clear - مسح تاريخ المحادثة
/history - عرض آخر 10 محادثات  
/stats - إحصائيات محادثتي
/myinfo - معلوماتي في النظام

💡 نصائح:
• كن واضحاً في أسئلتك
• يمكنني الرجوع لمحادثاتنا السابقة
• أسأل عن أي شيء تريد معرفته عن المتجر
        """
        
        await update.message.reply_text(help_message, parse_mode=None)
        await self.logger.log_action(
            user.id, update.effective_chat.id, 
            "HELP_COMMAND", "User requested help", get_user_display_name(user.id)
        )
    
    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /clear"""
        chat_id = update.effective_chat.id
        
        current_length = await self.llm_service.conversation_manager.get_memory_length(chat_id)
        
        keyboard = [
            [
                InlineKeyboardButton("✅ نعم، امسح التاريخ", callback_data="clear_confirm"),
                InlineKeyboardButton("❌ إلغاء", callback_data="clear_cancel")
            ]
        ]
        
        await update.message.reply_text(
            f"⚠️ تأكيد مسح التاريخ\n\n"
            f"سيتم مسح {current_length} رسالة من تاريخ محادثتك.\n"
            f"هل أنت متأكد؟",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=None
        )
    
    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /history"""
        chat_id = update.effective_chat.id
        
        history = await self.llm_service.conversation_manager.get_chat_history(
            chat_id, limit=5
        )
        
        if not history:
            await update.message.reply_text("🔭 لا توجد محادثات سابقة في هذه المحادثة.")
            return
        
        history_text = "📚 آخر محادثاتك:\n\n"
        
        for i, conv in enumerate(reversed(history), 1):
            timestamp = conv.get('timestamp', 'غير معروف')[:16]
            question = conv.get('question', '')[:80]
            answer = conv.get('answer', '')[:80]
            
            history_text += f"{i}. `{timestamp}`\n"
            history_text += f"🙋‍♂️ Q: {question}{'...' if len(conv.get('question', '')) > 80 else ''}\n"
            history_text += f"🤖 ANS: {answer}{'...' if len(conv.get('answer', '')) > 80 else ''}\n\n"
        
        keyboard = [[InlineKeyboardButton("📊 إحصائيات محادثتي", callback_data="show_my_stats")]]
        
        await update.message.reply_text(
            history_text,
            parse_mode=None,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /stats"""
        chat_id = update.effective_chat.id
        
        stats = await self.logger.get_chat_statistics(chat_id)
        memory_length = await self.llm_service.conversation_manager.get_memory_length(chat_id)
        
        stats_message = f"""
📊 إحصائيات محادثتك الشخصية:

💬 إجمالي المحادثات: {stats['total_conversations']}
📊 استعلامات SQL: {stats['sql_queries_count']}

⏰ أول رسالة: {stats['first_message'] or 'غير متاح'}
⏰ آخر رسالة: {stats['last_message'] or 'غير متاح'}

💡 هذه إحصائيات محادثتك الشخصية معي فقط
        """
        
        await update.message.reply_text(stats_message.strip())
    
    async def my_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /myinfo"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        stats = await self.logger.get_chat_statistics(chat_id)
        memory_length = await self.llm_service.conversation_manager.get_memory_length(chat_id)
        
        user_display = get_user_display_name(user.id)
        is_admin = is_user_admin(user.id)
        
        info_message = f"""
👤 معلوماتك الشخصية:

📱 الاسم: {user_display}
🆔 معرف المستخدم: {user.id}
💬 معرف المحادثة: {chat_id}
🛡 نوع الحساب: {'مدير' if is_admin else 'مستخدم عادي'}

📊 إحصائياتك في هذه المحادثة:
💬 إجمالي المحادثات: {stats['total_conversations']}
📊 استعلامات SQL: {stats['sql_queries_count']}

⏰ أول رسالة: {stats['first_message'] or 'غير متاح'}
⏰ آخر رسالة: {stats['last_message'] or 'غير متاح'}

{'🔧 لديك صلاحيات إدارية - استخدم /admin للوصول للوحة التحكم' if is_admin else '💡 هذه معلوماتك الشخصية فقط'}
        """
        
        await update.message.reply_text(info_message.strip())
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج لوحة تحكم المدير"""
        user = update.effective_user
        
        if not is_user_admin(user.id):
            await update.message.reply_text("🚫 هذا الأمر متاح للمدراء فقط.")
            return
        
        keyboard = [
            [InlineKeyboardButton("🗑️ مسح جميع المحادثات", callback_data="admin_clear_all")],
            [InlineKeyboardButton("📊 إحصائيات النظام", callback_data="admin_system_stats")],
            [InlineKeyboardButton("👥 المحادثات النشطة", callback_data="admin_active_users")]
        ]
        
        await update.message.reply_text(
            "🛡 لوحة تحكم المدير\n\nاختر العملية المطلوبة:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=None
        )
    
    async def clear_all_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر مسح جميع المحادثات"""
        user = update.effective_user
        
        if not is_user_admin(user.id):
            await update.message.reply_text("🚫 هذا الأمر متاح للمدراء فقط.")
            return
        
        keyboard = [
            [InlineKeyboardButton("⚠️ نعم، امسح كل شيء", callback_data="admin_clear_all_confirm")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin_clear_all_cancel")]
        ]
        
        await update.message.reply_text(
            "⚠️ تحذير: مسح جميع البيانات\n\n"
            "سيتم مسح جميع محادثات كل المستخدمين!\n"
            "هذا الإجراء لا يمكن التراجع عنه.\n\n"
            "هل أنت متأكد؟",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=None
        )
    
    async def system_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج إحصائيات النظام"""
        user = update.effective_user
        
        if not is_user_admin(user.id):
            await update.message.reply_text("🚫 هذا الأمر متاح للمدراء فقط.")
            return
        
        stats = await self.logger.get_system_statistics()
        
        stats_message = f"""
📊 إحصائيات النظام العامة:

💬 إجمالي المحادثات: {stats['total_conversations']:,}
🗨️ المحادثات النشطة: {stats['total_active_chats']}
👥 المستخدمون الفريدون: {stats['unique_users_count']}
📊 استعلامات SQL: {stats['sql_queries_count']:,}
📈 متوسط المحادثات لكل محادثة: {stats['average_conversations_per_chat']:.1f}
        """
        
        await update.message.reply_text(stats_message.strip())
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الرسائل النصية - محسّن للتوازي"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        question = update.message.text
        
        # فحص عدد الطلبات النشطة
        active_count = await self._get_active_request_count(user.id)
        if active_count >= self.max_concurrent_per_user:
            await update.message.reply_text(
                "⏳ لديك طلبات قيد المعالجة. يرجى الانتظار حتى تنتهي قبل إرسال طلب جديد."
            )
            return
        
        # فحص rate limit
        if not await self.rate_limiter.check_and_update(user.id):
            wait_time = await self.rate_limiter.get_wait_time(user.id)
            await update.message.reply_text(
                f"⏳ يرجى الانتظار {wait_time:.1f} ثانية قبل إرسال السؤال التالي."
            )
            return
        
        # إنشاء task للمعالجة
        task = asyncio.create_task(
            self._process_question_wrapper(update, context, user, chat_id, question)
        )
        
        # تتبع الـ task
        await self._track_request(user.id, task)
    
    async def _process_question_wrapper(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user,
        chat_id: int,
        question: str
    ):
        """Wrapper للمعالجة مع تتبع وتنظيف"""
        task = asyncio.current_task()
        try:
            await self._process_question(update, context, user, chat_id, question)
        finally:
            await self._untrack_request(user.id, task)
    
    async def _process_question(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE,
        user, 
        chat_id: int, 
        question: str
    ):
        """معالجة السؤال بشكل مستقل - محسّن"""
        try:
            # إنشاء سياق المستخدم
            create_user_context(
                user_id=user.id,
                chat_id=chat_id,
                username=get_user_display_name(user.id),
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # إرسال "يكتب..." وتسجيل في نفس الوقت
            await self.logger.log_action(
                user.id, chat_id, "QUESTION_ASKED",
                f"Question: {question[:100]}...", get_user_display_name(user.id)
            )
            # معالجة السؤال
            answer, sql_query, sql_result, history_len, mail = await self.llm_service.handle_question(
                user_question=question,
                username=get_user_display_name(user.id),
                chat_id=chat_id,
                user_id=user.id
            )
            # إعداد الرد
            reply_text = answer
            if sql_query:
                reply_text += f"\n\n📊 تم تنفيذ استعلام البيانات بنجاح"
            
            reply_markup = None
            if mail and mail.email and any(mail.email):
                keyboard = [
                    [InlineKeyboardButton("📧 إرسال الإيميل", callback_data=f"send_email_{chat_id}")],
                    [InlineKeyboardButton("👁️ معاينة الإيميل", callback_data=f"preview_email_{chat_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                context.user_data['pending_email'] = {
                    'subject': mail.subject,
                    'body': mail.body,
                    'email': mail.email
                }
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=reply_text,
                parse_mode=None,
                reply_markup=reply_markup
            )
            
            await self.logger.log_action(
                user.id, chat_id, "QUESTION_ANSWERED",
                f"SQL: {sql_query}, Email: {mail}", get_user_display_name(user.id)
            )
        
        except Exception as e:
            error_message = f"❌ حدث خطأ أثناء معالجة سؤالك:\n`{str(e)}`"
            await context.bot.send_message(
                chat_id=chat_id,
                text=error_message,
                parse_mode=None
            )
            
            await self.logger.log_action(
                user.id, chat_id, "QUESTION_ERROR",
                f"Error: {str(e)}", get_user_display_name(user.id)
            )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأزرار التفاعلية"""
        query = update.callback_query
        user = query.from_user
        chat_id = query.message.chat_id
        data = query.data
        
        await query.answer()
        
        # مسح محادثة المستخدم
        if data == "clear_confirm":
            await self.llm_service.conversation_manager.clear_memory(chat_id)
            await query.edit_message_text("✅ تم مسح تاريخ محادثتك بنجاح.")
            await self.logger.log_action(
                user.id, chat_id, "MEMORY_CLEARED",
                "User confirmed memory clear", get_user_display_name(user.id)
            )
        
        elif data == "clear_cancel":
            await query.edit_message_text("❌ تم إلغاء عملية مسح التاريخ.")
    
        # عرض إحصائيات المستخدم
        elif data == "show_my_stats":
            stats = await self.logger.get_chat_statistics(chat_id)
            stats_text = f"""
📊 تفاصيل إحصائيات محادثتك:

💬 إجمالي المحادثات: {stats['total_conversations']}
📊 استعلامات SQL: {stats['sql_queries_count']}
⏰ أول رسالة: {stats['first_message'] or 'غير متاح'}
⏰ آخر رسالة: {stats['last_message'] or 'غير متاح'}

💡 هذه إحصائياتك الشخصية فقط
            """
            await query.edit_message_text(stats_text.strip())
        
        # معالجة أوامر المدير
        elif data.startswith("admin_"):
            if not is_user_admin(user.id):
                await query.edit_message_text("🚫 غير مسموح لك بالوصول لهذه الوظيفة.")
                return
            
            await self._handle_admin_callback(query, user, chat_id, data)
        
        # معالجة رسائل البريد
        elif data.startswith("send_email_"):
            await self._handle_email_send(query, context, user, chat_id)
        
        elif data.startswith("preview_email_"):
            await self._handle_email_preview(query, context, chat_id)
        
        elif data == "cancel_email":
            if 'pending_email' in context.user_data:
                del context.user_data['pending_email']
            await query.edit_message_text("❌ تم إلغاء إرسال الإيميل.")
    
    async def _handle_admin_callback(self, query, user, chat_id: int, data: str):
        """معالجة أوامر المدير"""
        if data == "admin_clear_all":
            keyboard = [
                [InlineKeyboardButton("⚠️ نعم، امسح كل شيء", callback_data="admin_clear_all_confirm")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin_clear_all_cancel")]
            ]
            await query.edit_message_text(
                "⚠️ تحذير: مسح جميع البيانات\n\n"
                "سيتم مسح جميع محادثات كل المستخدمين!\n"
                "هذا الإجراء لا يمكن التراجع عنه.\n\n"
                "هل أنت متأكد؟",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=None
            )
        
        elif data == "admin_clear_all_confirm":
            await self.llm_service.conversation_manager.clear_all_memories()
            await query.edit_message_text("✅ تم مسح جميع محادثات النظام بنجاح.")
            await self.logger.log_action(
                user.id, chat_id, "ALL_MEMORIES_CLEARED",
                "Admin cleared all system memories", get_user_display_name(user.id)
            )
        
        elif data == "admin_clear_all_cancel":
            await query.edit_message_text("❌ تم إلغاء عملية مسح جميع البيانات.")
        
        elif data == "admin_system_stats":
            stats = await self.logger.get_system_statistics()
            stats_message = f"""
📊 إحصائيات النظام:

💬 إجمالي المحادثات: {stats['total_conversations']:,}
🗨️ المحادثات النشطة: {stats['total_active_chats']}
👥 المستخدمون الفريدون: {stats['unique_users_count']}
📊 استعلامات SQL: {stats['sql_queries_count']:,}
📈 المتوسط لكل محادثة: {stats['average_conversations_per_chat']:.1f}
            """
            await query.edit_message_text(stats_message.strip())
        
        elif data == "admin_active_users":
            active_chats = await self.llm_service.conversation_manager.get_active_chats()
            
            if not active_chats:
                await query.edit_message_text("🔭 لا توجد محادثات نشطة في النظام.")
                return
            
            users_text = "👥 المحادثات النشطة:\n\n"
            
            for i, chat_id_item in enumerate(active_chats[:10], 1):
                history = await self.llm_service.conversation_manager.get_chat_history(
                    chat_id_item, limit=1
                )
                if history:
                    last_conv = history[-1]
                    username = last_conv.get('username', f'User{last_conv.get("user_id", "Unknown")}')
                    timestamp = last_conv.get('timestamp', 'غير معروف')[:10]
                    
                    users_text += f"{i}. Chat {chat_id_item}\n"
                    users_text += f"👤 {username} | ⏰ {timestamp}\n\n"
            
            if len(active_chats) > 10:
                users_text += f"... وعدد {len(active_chats) - 10} محادثة أخرى"
            
            await query.edit_message_text(users_text.strip(), parse_mode=None)
    
    async def _handle_email_send(self, query, context, user, chat_id: int):
        """معالجة إرسال الإيميل"""
        if 'pending_email' not in context.user_data:
            await query.edit_message_text("❌ لم يتم العثور على بيانات الإيميل.")
            return
        
        email_data = context.user_data['pending_email']
        mail = Mail(
            subject=email_data['subject'],
            body=email_data['body'],
            email=email_data['email']
        )
        
        try:
            result = await self.llm_service.send_email(mail)
            await query.edit_message_text(f"✅ {result}")
            await self.logger.log_action(
                user.id, chat_id, "EMAIL_SENT",
                f"Email sent to {len(email_data['email'])} recipients", get_user_display_name(user.id)
            )
        except Exception as e:
            await query.edit_message_text(f"❌ فشل في إرسال الإيميل: {str(e)}")
        finally:
            if 'pending_email' in context.user_data:
                del context.user_data['pending_email']
    
    async def _handle_email_preview(self, query, context, chat_id: int):
        """معالجة معاينة الإيميل"""
        if 'pending_email' not in context.user_data:
            await query.edit_message_text("❌ لم يتم العثور على بيانات الإيميل.")
            return
        
        email_data = context.user_data['pending_email']
        preview_text = f"""
📧 معاينة الإيميل:

إلى: {', '.join(email_data['email'])}
الموضوع: {email_data['subject']}

المحتوى:
{email_data['body']}
        """
        
        keyboard = [
            [InlineKeyboardButton("📧 إرسال الآن", callback_data=f"send_email_{chat_id}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_email")]
        ]
        
        await query.edit_message_text(
            preview_text.strip(),
            parse_mode=None,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def cleanup(self):
        """تنظيف الموارد"""
        await self.llm_service.cleanup()
        await self.llm_service.conversation_manager.stop_writer()
        await self.logger.stop_writer()
    
    def run(self):
        """تشغيل البوت"""
        print("🚀 Starting Telegram Bot...")
        print(f"Bot Token: {BOT_TOKEN[:10]}...")
        print(f"⚡ التوازي: مفعّل (max {self.max_concurrent_per_user} طلب لكل مستخدم)")
        print(f"⏱️ Rate Limit: {self.rate_limiter.requests_per_second} req/sec (burst: {self.rate_limiter.burst})")
        
        self.application.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True
        )


def run_telegram_bot():
    """تشغيل البوت"""
    bot = TelegramBot(get_llm_service())
    
    # إعداد cleanup عند الإيقاف
    import atexit
    atexit.register(lambda: asyncio.run(bot.cleanup()))
    
    bot.run()


if __name__ == "__main__":
    run_telegram_bot()
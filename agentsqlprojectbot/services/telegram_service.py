# services/telegram_service.py
import os
import asyncio
from typing import Any, Dict, Set
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from models.pydantic_models import Mail

from services.telegram_llm_service import get_llm_service
from services.telegram_auth import (
    create_user_context, get_user_display_name, get_user_manager
)
from services.telegram_logging import TelegramLogger
from services.organization_manager import get_organization_manager
from services.database_manager import get_database_manager

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")


class RateLimiter:
    """Rate limiter محسّن مع دعم burst"""
    
    def __init__(self, requests_per_second: float = 1.0, burst: int = 3):
        self.requests_per_second = requests_per_second
        self.burst = burst
        self.period = 1.0 / requests_per_second
        
        self._tokens: Dict[int, float] = {}
        self._last_update: Dict[int, float] = {}
        self._lock = asyncio.Lock()
    
    async def check_and_update(self, user_id: int) -> bool:
        now = asyncio.get_event_loop().time()
        
        async with self._lock:
            if user_id in self._tokens:
                time_passed = now - self._last_update[user_id]
                self._tokens[user_id] = min(
                    self.burst,
                    self._tokens[user_id] + time_passed * self.requests_per_second
                )
            else:
                self._tokens[user_id] = self.burst
            
            self._last_update[user_id] = now
            
            if self._tokens[user_id] >= 1.0:
                self._tokens[user_id] -= 1.0
                return True
            else:
                return False
            
    async def get_wait_time(self, user_id: int) -> float:
        async with self._lock:
            if user_id not in self._tokens:
                return 0.0
            
            tokens_needed = 1.0 - self._tokens[user_id]
            if tokens_needed <= 0:
                return 0.0
            
            return tokens_needed / self.requests_per_second


class TelegramBot:
    """بوت تليجرام محسّن مع دعم المؤسسات"""
    
    def __init__(self, llm_service):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.llm_service = llm_service
        self.logger = TelegramLogger()
        
        # Managers
        self.org_manager = get_organization_manager()
        self.db_manager = get_database_manager()
        self.user_manager = get_user_manager()
        
        self.rate_limiter = RateLimiter(requests_per_second=1.0, burst=3)
        
        self._active_requests: Dict[int, Set[asyncio.Task]] = {}
        self._active_lock = asyncio.Lock()
        
        self.max_concurrent_per_user = 1
        
        self._setup_handlers()

    async def start_background_tasks(self):
        """بدء المهام في الخلفية"""
        # await self.llm_service.conversation_manager.start_writer()
        await self.logger.start_writer()
    
    
    # إضافة/تعديل في TelegramBot class
    

    async def add_database_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إضافة قاعدة بيانات - محدث مع صلاحيات"""
        user = update.effective_user
        
        # فحص صلاحية إضافة قاعدة بيانات
        can_add = await self.org_manager.can_user_add_personal_database(user.id)
        
        if not can_add:
            await update.message.reply_text(
                "❌ **غير مسموح بإضافة قواعد بيانات شخصية**\n\n"
                "أنت عضو في مؤسسة، يمكنك فقط استخدام قواعد البيانات "
                "التي يضيفها مدير المؤسسة.\n\n"
                "📞 تواصل مع مدير المؤسسة لإضافة قواعد بيانات جديدة.",
                
            )
            return
        
        # التحقق من نوع المستخدم
        org = await self.org_manager.get_user_organization(user.id)
        
        if org:
            # المستخدم مدير مؤسسة - إضافة قاعدة بيانات للمؤسسة
            is_owner = await self.org_manager.is_organization_owner(user.id, org.org_id)
            if not is_owner:
                await update.message.reply_text("🚫 هذا الأمر متاح لمالك المؤسسة فقط")
                return
            
            await self._add_org_database(update, context, user, org)
        else:
            # المستخدم عادي - إضافة قاعدة بيانات شخصية
            await self._add_personal_database(update, context, user)


    async def _add_personal_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user):
        """إضافة قاعدة بيانات شخصية للمستخدم العادي"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "📝 **إضافة قاعدة بيانات شخصية**\n\n"
                "الاستخدام:\n"
                "`/adddb <اسم_القاعدة> <رابط_الاتصال>`\n\n"
                "مثال:\n"
                "`/adddb MyDB postgresql://user:pass@localhost/mydb`\n\n"
                "⚠️ **تحذير:** رابط الاتصال يحتوي على معلومات حساسة، "
                "تأكد من إرساله في محادثة خاصة فقط!",
                
            )
            return
        
        db_name = context.args[0]
        connection_string = context.args[1]
        
        # إضافة الاتصال الشخصي
        connection = await self.db_manager.add_connection(
            name=db_name,
            connection_string=connection_string,
            created_by=user.id,
            owner_type="user",  # قاعدة بيانات شخصية
            owner_id=str(user.id)
        )
        
        if not connection:
            await update.message.reply_text(
                "❌ فشل الاتصال بقاعدة البيانات\n"
                "تحقق من صحة رابط الاتصال"
            )
            return
        
        # تعيينها كقاعدة بيانات نشطة تلقائياً
        self.user_manager.set_current_database_sync(user.id, connection.connection_id, connection.db_type)
        
        await update.message.reply_text(
            f"✅ تم إضافة قاعدة البيانات '{db_name}' بنجاح!\n\n"
            f"🆔 معرف الاتصال: `{connection.connection_id}`\n"
            f"✨ تم تعيينها كقاعدة بيانات نشطة تلقائياً\n\n"
            f"يمكنك الآن البدء في الاستعلام عن البيانات!",
            
        )
        
        # حذف الرسالة الأصلية لحماية البيانات الحساسة
        try:
            await update.message.delete()
        except:
            pass


    async def _add_org_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user, org):
        """إضافة قاعدة بيانات للمؤسسة (للمدير فقط)"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "📝 **إضافة قاعدة بيانات للمؤسسة**\n\n"
                "الاستخدام:\n"
                "`/adddb <اسم_القاعدة> <رابط_الاتصال>`\n\n"
                "مثال:\n"
                "`/adddb CompanyDB postgresql://user:pass@localhost/companydb`\n\n"
                "⚠️ **تحذير:** رابط الاتصال يحتوي على معلومات حساسة، "
                "تأكد من إرساله في محادثة خاصة فقط!\n\n"
                "📊 ستكون القاعدة متاحة لجميع أعضاء المؤسسة",
                
            )
            return
        
        db_name = context.args[0]
        connection_string = context.args[1]
        
        # إضافة الاتصال للمؤسسة
        connection, db_type = await self.db_manager.add_connection(
            name=db_name,
            connection_string=connection_string,
            created_by=user.id,
            owner_type="organization",
            owner_id=org.org_id
        )
        
        if not connection:
            await update.message.reply_text(
                "❌ فشل الاتصال بقاعدة البيانات\n"
                "تحقق من صحة رابط الاتصال"
            )
            return
        
        # ربط بالمؤسسة
        await self.org_manager.add_database_connection(
            org.org_id, user.id, connection.connection_id
        )
        
        await update.message.reply_text(
            f"✅ تم إضافة قاعدة البيانات '{db_name}' للمؤسسة '{org.name}' بنجاح!\n\n"
            f"🆔 معرف الاتصال: `{connection.connection_id}`\n"
            f"📊 يمكن لجميع أعضاء المؤسسة ({len(org.members)} عضو) الآن استخدامها\n\n"
            f"💡 يمكن للأعضاء اختيارها عبر: /selectdb",
            
        )
        
        # حذف الرسالة الأصلية لحماية البيانات الحساسة
        try:
            await update.message.delete()
        except:
            pass
        
        # إشعار جميع الأعضاء
        await self._notify_org_members_new_db(org, db_name, connection.connection_id)


    async def _notify_org_members_new_db(self, org, db_name: str, db_id: str):
        """إشعار أعضاء المؤسسة بقاعدة بيانات جديدة"""
        notification_text = (
            f"📢 **قاعدة بيانات جديدة متاحة!**\n\n"
            f"� المؤسسة: {org.name}\n"
            f"🗄️ القاعدة: {db_name}\n\n"
            f"يمكنك استخدامها الآن عبر: /selectdb"
        )
        
        for member_id in org.members:
            if member_id != org.owner_id:  # لا نرسل للمدير لأنه أضافها
                await self.application.bot.send_message(
                    chat_id=member_id,
                    text=notification_text,
                    
                )
    
    # تحديث أمر /myinfo لعرض معلومات المؤسسة
    

    async def my_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معلومات المستخدم - محدث"""
        user = update.effective_user
        user_info = self.user_manager.get_user_sync(user.id)
        
        if not user_info:
            await update.message.reply_text("⚠️ لم يتم العثور على معلوماتك")
            return
        
        # معلومات أساسية
        info_text = f"👤 **معلوماتك في النظام**\n\n"
        info_text += f"🆔 المعرف: `{user.id}`\n"
        info_text += f"📛 الاسم: {self.user_manager.get_display_name_sync(user.id)}\n"
        info_text += f"👔 الدور: {self._get_role_emoji(user_info.role)} {self._translate_role(user_info.role)}\n"
        info_text += f"📅 تاريخ التسجيل: {user_info.first_seen[:10]}\n"
        info_text += f"💬 عدد التفاعلات: {user_info.interaction_count}\n"
        
        # معلومات المؤسسة
        org = await self.org_manager.get_user_organization(user.id)
        if org:
            is_owner = await self.org_manager.is_organization_owner(user.id, org.org_id)
            info_text += f"\n🏢 **معلومات المؤسسة**\n"
            info_text += f"📛 الاسم: {org.name}\n"
            info_text += f"👤 دورك: {'👑 المدير' if is_owner else '👥 عضو'}\n"
            info_text += f"👥 عدد الأعضاء: {len(org.members)}\n"
            info_text += f"🗄️ قواعد البيانات: {len(org.database_connections)}\n"
            
            if not is_owner:
                info_text += f"\n⚠️ **ملاحظة:** لا يمكنك مغادرة المؤسسة ذاتياً\n"
                info_text += f"يجب على المدير إزالتك أولاً"
        else:
            info_text += f"\n📋 **الحالة:** مستخدم مستقل (غير منتمٍ لمؤسسة)\n"
            info_text += f"💡 يمكنك:\n"
            info_text += f"  • إنشاء مؤسسة: /createorg\n"
            info_text += f"  • الانضمام لمؤسسة: /join\n"
            info_text += f"  • إضافة قاعدة بيانات شخصية: /adddb"
        
        # معلومات قاعدة البيانات النشطة
        if user_info.current_database:
            db_conn = await self.db_manager.get_connection(user_info.current_database)
            if db_conn:
                info_text += f"\n\n🗄️ **قاعدة البيانات النشطة**\n"
                info_text += f"📌 {db_conn.name}\n"
                info_text += f"🔗 النوع: {'مؤسسية' if db_conn.owner_type == 'organization' else 'شخصية'}"
        else:
            info_text += f"\n\n⚠️ لم يتم اختيار قاعدة بيانات\n"
            info_text += f"استخدم /selectdb لاختيار قاعدة بيانات"
        
        await update.message.reply_text(info_text, )


    def _get_role_emoji(self, role: str) -> str:
        """الحصول على emoji الدور"""
        emojis = {
            "admin": "🔐",
            "org_owner": "👑",
            "org_member": "👥",
            "user": "👤"
        }
        return emojis.get(role, "❓")


    def _translate_role(self, role: str) -> str:
        """ترجمة الدور للعربية"""
        translations = {
            "admin": "مدير النظام",
            "org_owner": "مدير مؤسسة",
            "org_member": "عضو مؤسسة",
            "user": "مستخدم عادي"
        }
        return translations.get(role, role)


    
    # إضافة أمر جديد: /orginfo (معلومات المؤسسة المفصلة)
    

    async def org_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معلومات تفصيلية عن المؤسسة"""
        user = update.effective_user
        
        org = await self.org_manager.get_user_organization(user.id)
        
        if not org:
            await update.message.reply_text(
                "⚠️ أنت لست عضواً في أي مؤسسة\n\n"
                "يمكنك:\n"
                "• إنشاء مؤسسة: /createorg\n"
                "• الانضمام لمؤسسة: /join <كود_الدعوة>"
            )
            return
        
        is_owner = await self.org_manager.is_organization_owner(user.id, org.org_id)
        
        # معلومات أساسية
        info_text = f"🏢 **{org.name}**\n\n"
        info_text += f"🆔 المعرف: `{org.org_id}`\n"
        info_text += f"📅 تاريخ الإنشاء: {org.created_at[:10]}\n"
        info_text += f"👑 المدير: {self.user_manager.get_display_name_sync(org.owner_id)}\n"
        info_text += f"👤 دورك: {'👑 المدير' if is_owner else '👥 عضو'}\n\n"
        
        # الأعضاء
        info_text += f"👥 **الأعضاء ({len(org.members)}):**\n"
        for i, member_id in enumerate(org.members[:10], 1):
            member_name = self.user_manager.get_display_name_sync(member_id)
            role_emoji = "👑" if member_id == org.owner_id else "👤"
            info_text += f"{i}. {role_emoji} {member_name}\n"
        
        if len(org.members) > 10:
            info_text += f"... و {len(org.members) - 10} أعضاء آخرين\n"
        
        # قواعد البيانات
        info_text += f"\n🗄️ **قواعد البيانات ({len(org.database_connections)}):**\n"
        if org.database_connections:
            for i, db_id in enumerate(org.database_connections[:5], 1):
                db_conn = await self.db_manager.get_connection(db_id)
                if db_conn:
                    info_text += f"{i}. {db_conn.name}\n"
            
            if len(org.database_connections) > 5:
                info_text += f"... و {len(org.database_connections) - 5} قواعد أخرى\n"
        else:
            info_text += "لا توجد قواعد بيانات مضافة بعد\n"
        
        # أزرار الإجراءات
        keyboard = []
        if is_owner:
            keyboard.append([InlineKeyboardButton("➕ إضافة قاعدة بيانات", callback_data="org_add_db")])
            keyboard.append([InlineKeyboardButton("🔗 إنشاء رابط دعوة", callback_data="org_create_invite")])
            keyboard.append([InlineKeyboardButton("👥 إدارة الأعضاء", callback_data="org_manage_members")])
        
        keyboard.append([InlineKeyboardButton("🗄️ اختيار قاعدة بيانات", callback_data="org_select_db")])
        
        await update.message.reply_text(
            info_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            
        )


    
    # تحديث _setup_handlers لإضافة الأمر الجديد
    

    def _setup_handlers(self):
        """إعداد معالجات الأوامر والرسائل - محدث"""
        # الأوامر العامة
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("clear", self.clear_command))
        self.application.add_handler(CommandHandler("history", self.history_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("myinfo", self.my_info_command))
        
        # 🆕 أوامر المؤسسات
        self.application.add_handler(CommandHandler("org", self.org_menu_command))
        self.application.add_handler(CommandHandler("orginfo", self.org_info_command))  # جديد
        self.application.add_handler(CommandHandler("createorg", self.create_org_command))
        self.application.add_handler(CommandHandler("adddb", self.add_database_command))  # محدث
        self.application.add_handler(CommandHandler("selectdb", self.select_database_command))
        self.application.add_handler(CommandHandler("invite", self.create_invite_command))
        self.application.add_handler(CommandHandler("join", self.join_org_command))
        
        # معالج الرسائل
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        # معالج الأزرار
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))



    async def _track_request(self, user_id: int, task: asyncio.Task):
        async with self._active_lock:
            if user_id not in self._active_requests:
                self._active_requests[user_id] = set()
            self._active_requests[user_id].add(task)
    
    async def _untrack_request(self, user_id: int, task: asyncio.Task):
        async with self._active_lock:
            if user_id in self._active_requests:
                self._active_requests[user_id].discard(task)
                if not self._active_requests[user_id]:
                    del self._active_requests[user_id]
    
    async def _get_active_request_count(self, user_id: int) -> int:
        async with self._active_lock:
            return len(self._active_requests.get(user_id, set()))
    
    # ==
    # 🆕 أوامر المؤسسات
    # ==
    
    async def org_menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """قائمة المؤسسة"""
        user = update.effective_user
        
        org = await self.org_manager.get_user_organization(user.id)
        
        if not org:
            keyboard = [[InlineKeyboardButton("➕ إنشاء مؤسسة", callback_data="create_org_prompt")]]
            await update.message.reply_text(
                "🏢 لست عضواً في أي مؤسسة\n\n"
                "يمكنك:\n"
                "• إنشاء مؤسسة جديدة: /createorg\n"
                "• الانضمام لمؤسسة: /join <كود_الدعوة>",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        is_owner = await self.org_manager.is_organization_owner(user.id, org.org_id)
        
        # إحصائيات المؤسسة
        members_count = len(org.members)
        dbs_count = len(org.database_connections)
        
        # الأزرار حسب الصلاحيات
        keyboard = []
        
        if is_owner:
            keyboard.append([InlineKeyboardButton("➕ إضافة قاعدة بيانات", callback_data="org_add_db")])
            keyboard.append([InlineKeyboardButton("🔗 إنشاء رابط دعوة", callback_data="org_create_invite")])
            keyboard.append([InlineKeyboardButton("👥 إدارة الأعضاء", callback_data="org_manage_members")])
        
        keyboard.append([InlineKeyboardButton("🗄️ اختيار قاعدة بيانات", callback_data="org_select_db")])
        keyboard.append([InlineKeyboardButton("📊 معلومات المؤسسة", callback_data="org_info")])
        
        role_text = "👑 المالك" if is_owner else "👤 عضو"
        
        await update.message.reply_text(
            f"🏢 **{org.name}**\n\n"
            f"👤 دورك: {role_text}\n"
            f"👥 الأعضاء: {members_count}\n"
            f"🗄️ قواعد البيانات: {dbs_count}\n\n"
            f"اختر إجراءً:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            
        )
    
    async def create_org_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إنشاء مؤسسة جديدة"""
        user = update.effective_user
        
        # تحقق إذا كان المستخدم في مؤسسة
        existing_org = await self.org_manager.get_user_organization(user.id)
        if existing_org:
            await update.message.reply_text(
                f"⚠️ أنت بالفعل عضو في مؤسسة '{existing_org.name}'\n"
                f"لا يمكن الانضمام لأكثر من مؤسسة."
            )
            return
        
        # طلب اسم المؤسسة
        if not context.args:
            await update.message.reply_text(
                "📝 الاستخدام:\n"
                "`/createorg <اسم_المؤسسة>`\n\n"
                "مثال:\n"
                "`/createorg شركة التقنية المتقدمة`",
                
            )
            return
        
        org_name = " ".join(context.args)
        
        if len(org_name) < 3:
            await update.message.reply_text("⚠️ اسم المؤسسة يجب أن يكون 3 أحرف على الأقل")
            return
        try:
            # إنشاء المؤسسة والحصول على بيانات الدخول
            result = await self.org_manager.create_organization(
                owner_id=user.id,
                name=org_name
            )
            
            org = result['org']
            username = result['dashboard_username']
            password = result['dashboard_password']
            
            # تحديث دور المستخدم
            await self.user_manager.update_user_role(user.id, "org_owner")
            
            # إرسال رسالة النجاح مع بيانات الدخول
            success_message = (
                f"✅ تم إنشاء مؤسسة '{org_name}' بنجاح!\n\n"
                f"🆔 معرف المؤسسة: `{str(result['org'].org_id)}`\n\n"
                f"📊 **بيانات دخول الداش بورد:**\n"
                f"🔗 الرابط: https://yoursite.com/dashboard\n"
                f"👤 اسم المستخدم: `{username}`\n"
                f"🔐 كلمة المرور: `{password}`\n\n"
                f"⚠️ احفظ هذه البيانات في مكان آمن!\n\n"
                f"يمكنك الآن:\n"
                f"• إضافة قواعد بيانات: /adddb\n"
                f"• إنشاء روابط دعوة: /invite\n"
                f"• إدارة المؤسسة: /org"
            )
            
            await update.message.reply_text(
                success_message,
                parse_mode=None
            )
            
            # تسجيل الفعل
            await self.logger.log_action(
                user.id, update.effective_chat.id,
                "ORG_CREATED", f"Created org: {org.name}",
                get_user_display_name(user.id)
            )
        
        except Exception as e:
            await update.message.reply_text(
                f"❌ حدث خطأ أثناء إنشاء المؤسسة: {str(e)}"
            )
            print(f"❌ خطأ: {e}")


    async def select_database_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """اختيار قاعدة بيانات للاستعلام"""
        user = update.effective_user
        
        # الحصول على قواعد البيانات المتاحة
        user_info = self.user_manager.get_user_sync(user.id)
        
        if not user_info:
            await update.message.reply_text("⚠️ خطأ في تحميل معلومات المستخدم")
            return
        if not await self.db_manager.verify_user_can_access_database(user.id, user_info.current_database):
            user_info.current_database = None

        # قواعد بيانات شخصية
        personal_dbs = await self.db_manager.get_user_connections(user.id)
        
        # قواعد بيانات المؤسسة
        org_dbs = []
        org = await self.org_manager.get_user_organization(user.id)
        if org:
            # احصل على الاتصالات النشطة مباشرة
            org_dbs = await self.db_manager.get_organization_connections(org.org_id)
        
        if not personal_dbs and not org_dbs:
            await update.message.reply_text(
                "📭 لا توجد قواعد بيانات متاحة\n\n"
                "يمكنك:\n"
                "• إضافة قاعدة بيانات شخصية: /adddb (إذا كنت مالك مؤسسة)\n"
                "• الانضمام لمؤسسة: /join"
            )
            return
        
        # إنشاء الأزرار
        keyboard = []
        
        if personal_dbs:
            keyboard.append([InlineKeyboardButton("--- 🔹 قواعد البيانات الشخصية ---", callback_data="ignore")])
            for db in personal_dbs:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{'✅ ' if user_info.current_database == db.connection_id else ''}{db.name}",
                        callback_data=f"select_db_{db.connection_id}"
                    )
                ])
        
        if org_dbs:
            keyboard.append([InlineKeyboardButton(f"--- 🏢 قواعد بيانات {org.name} ---", callback_data="ignore")])
            for db in org_dbs:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{'✅ ' if user_info.current_database == db.connection_id else ''}{db.name}",
                        callback_data=f"select_db_{db.connection_id}"
                    )
                ])
        
        current_db_name = "لم يتم التحديد"
        if user_info.current_database:
            current_conn = await self.db_manager.get_connection(user_info.current_database)
            if current_conn and await self.db_manager.verify_user_can_access_database(user.id, user_info.current_database):
                current_db_name = current_conn.name
            else:
                # إذا كان الاتصال محذوفاً، امسح التحديد
                user_info.current_database = None
        
        await update.message.reply_text(
            f"🗄️ **اختيار قاعدة البيانات**\n\n"
            f"الحالية: {current_db_name}\n\n"
            f"اختر قاعدة بيانات للاستعلام:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            
        )
    
    async def create_invite_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إنشاء رابط دعوة (للمدير فقط)"""
        user = update.effective_user
        
        org = await self.org_manager.get_user_organization(user.id)
        
        if not org:
            await update.message.reply_text("⚠️ يجب أن تكون عضواً في مؤسسة أولاً")
            return
        
        is_owner = await self.org_manager.is_organization_owner(user.id, org.org_id)
        if not is_owner:
            await update.message.reply_text("🚫 هذا الأمر متاح لمالك المؤسسة فقط")
            return
        
        # معالجة الخيارات
        max_uses = 1
        expires_hours = 24
        
        if context.args:
            try:
                max_uses = int(context.args[0])
                if len(context.args) > 1:
                    expires_hours = int(context.args[1])
            except ValueError:
                await update.message.reply_text(
                    "⚠️ استخدام خاطئ\n\n"
                    "الاستخدام: `/invite [عدد_الاستخدامات] [ساعات_الصلاحية]`\n\n"
                    "مثال: `/invite 5 48` (5 استخدامات، صالح 48 ساعة)",
                    
                )
                return
        
        # إنشاء الدعوة
        invitation = await self.org_manager.create_invitation(
            org_id=org.org_id,
            creator_id=user.id,
            max_uses=max_uses,
            expires_hours=expires_hours
        )
        
        if not invitation:
            await update.message.reply_text("❌ فشل في إنشاء رابط الدعوة")
            return
        
        invite_command = f"/join {invitation.invite_code}"
        
        await update.message.reply_text(
            f"🎉 تم إنشاء رابط دعوة جديد!\n\n"
            f"🏢 المؤسسة: {org.name}\n"
            f"🔢 عدد الاستخدامات: {max_uses}\n"
            f"⏰ صالح لمدة: {expires_hours} ساعة\n\n"
            f"📋 الأمر للانضمام:\n"
            f"`{invite_command}`\n\n"
            f"⚠️ شارك هذا الرمز مع الأعضاء الجدد فقط",
            
        )
    
    async def join_org_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """الانضمام لمؤسسة عبر رمز دعوة"""
        user = update.effective_user
        
        # تحقق من الانضمام السابق
        existing_org = await self.org_manager.get_user_organization(user.id)
        if existing_org:
            await update.message.reply_text(
                f"⚠️ أنت بالفعل عضو في مؤسسة '{existing_org.name}'\n"
                f"لا يمكن الانضمام لأكثر من مؤسسة."
            )
            return
        
        if not context.args:
            await update.message.reply_text(
                "📝 الاستخدام:\n"
                "`/join <كود_الدعوة>`\n\n"
                "مثال:\n"
                "`/join AbCd1234EfGh5678`",
                
            )
            return
        
        invite_code = context.args[0]
        
        # استخدام الدعوة
        success, message, credentials = await self.org_manager.use_invitation(invite_code, user.id, user.full_name)
        
        if success:
            # تحديث دور المستخدم
            await self.user_manager.update_user_role(user.id, "org_member")
            
            await update.message.reply_text(
                f"✅ {message}\n\n"
                f"👤 اسم المستخدم: `{credentials['username']}`\n"
                f"🔐 كلمة المرور: `{credentials['password']}`\n\n"
                f"يمكنك الآن:\n"
                f"• عرض معلومات المؤسسة: /org\n"
                f"• اختيار قاعدة بيانات: /selectdb",
                
            )
            
            await self.logger.log_action(
                user.id, update.effective_chat.id,
                "JOINED_ORG", f"Joined via invite: {invite_code}",
                get_user_display_name(user.id)
            )
        else:
            await update.message.reply_text(f"❌ {message}")
    
    # ==
    # الأوامر الأصلية (محدثة قليلاً)
    # ==
    
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

🔹 يمكنني مساعدتك في:
• الاستعلام عن البيانات باستخدام SQL
• إنشاء وإرسال رسائل بريد إلكتروني
• الإجابة على الأسئلة حول متجرك

📋 الأوامر المتاحة:
/help - عرض المساعدة
/org - إدارة المؤسسة
/selectdb - اختيار قاعدة بيانات
/clear - مسح سجل المحادثة
/history - عرض آخر المحادثات

💬 ابدأ بإرسال سؤالك وسأقوم بمساعدتك!
        """
        
        await update.message.reply_text(welcome_message.strip())

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الأزرار التفاعلية - محدثة"""
        query = update.callback_query
        user = query.from_user
        chat_id = query.message.chat_id
        data = query.data
        
        await query.answer()
        
        try:
            # معالجات المؤسسات
            if data.startswith("org_"):
                await self._handle_org_callback(query, user, chat_id, data)
            
            # معالجات اختيار قاعدة البيانات
            elif data.startswith("select_db_"):
                await self._handle_select_database(query, user, chat_id, data)
            
            # مسح محادثة المستخدم
            elif data == "clear_confirm":
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
            
            # معالجة رسائل البريد
            elif data.startswith("send_email_"):
                await self._handle_email_send(query, context, user, chat_id)
            
            elif data.startswith("preview_email_"):
                await self._handle_email_preview(query, context, chat_id)
            
            elif data == "cancel_email":
                if 'pending_email' in context.user_data:
                    del context.user_data['pending_email']
                await query.edit_message_text("❌ تم إلغاء إرسال الإيميل.")
            
            # معالجات أخرى
            elif data == "ignore":
                await query.answer("تم")
            
        except Exception as e:
            await query.edit_message_text(f"خطأ: {str(e)}")
            await self.logger.log_action(
                user.id, chat_id, "CALLBACK_ERROR",
                f"Data: {data}, Error: {str(e)}", 
                get_user_display_name(user.id)
            )


    async def _handle_select_database(self, query, user, chat_id: int, data: str):
        """معالجة اختيار قاعدة بيانات"""
        db_id = data.replace("select_db_", "")
        
        # التحقق من الصلاحية
        can_access, reason = await self.db_manager.verify_user_can_access_database(
            user.id, db_id
        )
        
        if not can_access:
            await query.answer(f"خطأ: {reason}", show_alert=True)
            return
        
        conn = await self.db_manager.get_connection(db_id)

        # تعيين قاعدة البيانات النشطة
        self.user_manager.set_current_database_sync(user.id, db_id, conn.db_type)
        
        
        await query.edit_message_text(
            f"✅ تم اختيار قاعدة البيانات: **{conn.name}**\n\n"
            f"النوع: {'مؤسسية' if conn.owner_type == 'organization' else 'شخصية'}\n"
            f"آخر استخدام: {conn.last_used[:10] if conn.last_used else 'لم تستخدم بعد'}\n\n"
            f"يمكنك الآن طرح أسئلتك على هذه القاعدة!",
            
        )
        
        await self.logger.log_action(
            user.id, chat_id, "DATABASE_SELECTED",
            f"Database: {conn.name}",
            get_user_display_name(user.id)
        )


    async def _handle_org_callback(self, query, user, chat_id: int, data: str):
        """معالجة أزرار المؤسسات"""
        
        if data == "create_org_prompt":
            await query.edit_message_text(
                "📝 **إنشاء مؤسسة جديدة**\n\n"
                "استخدم الأمر: `/createorg <اسم_المؤسسة>`\n\n"
                "مثال: `/createorg شركة التقنية`\n\n"
                "⚠️ تأكد من أنك لست عضواً في مؤسسة أخرى",
                
            )
        
        elif data == "org_add_db":
            await query.edit_message_text(
                "📊 **إضافة قاعدة بيانات**\n\n"
                "استخدم الأمر: `/adddb <الاسم> <رابط_الاتصال>`\n\n"
                "مثال:\n"
                "`/adddb CompanyDB postgresql://user:pass@host/db`\n\n"
                "⚠️ هذا الرابط سيكون متاحاً لجميع أعضاء المؤسسة",
                
            )
        
        elif data == "org_create_invite":
            await query.edit_message_text(
                "🔗 **إنشاء رابط دعوة**\n\n"
                "استخدم الأمر: `/invite [عدد_الاستخدامات] [ساعات_الصلاحية]`\n\n"
                "أمثلة:\n"
                "`/invite` - استخدام واحد، صالح 24 ساعة\n"
                "`/invite 5 48` - 5 استخدامات، صالح 48 ساعة\n"
                "`/invite 10 72` - 10 استخدامات، صالح 72 ساعة\n\n"
                "⚠️ شارك الرابط فقط مع من تثق به",
                
            )
        
        elif data == "org_manage_members":
            org = await self.org_manager.get_user_organization(user.id)
            if not org:
                await query.edit_message_text("المؤسسة غير موجودة")
                return
            
            is_owner = await self.org_manager.is_organization_owner(user.id, org.org_id)
            if not is_owner:
                await query.edit_message_text("هذا الخيار متاح للمدير فقط")
                return
            
            # عرض قائمة الأعضاء مع أزرار الإزالة
            keyboard = []
            
            for member_id in org.members:
                if member_id != org.owner_id:
                    member_name = self.user_manager.get_display_name_sync(member_id)
                    keyboard.append([
                        InlineKeyboardButton(
                            f"❌ {member_name}",
                            callback_data=f"org_remove_member_{member_id}"
                        )
                    ])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="org_back_menu")])
            
            await query.edit_message_text(
                f"👥 **إدارة أعضاء المؤسسة**\n\n"
                f"إجمالي الأعضاء: {len(org.members)}\n\n"
                f"اختر عضواً لإزالته:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif data.startswith("org_remove_member_"):
            member_id = int(data.replace("org_remove_member_", ""))
            org = await self.org_manager.get_user_organization(user.id)
            
            if not org:
                await query.answer("خطأ: المؤسسة غير موجودة", show_alert=True)
                return
            
            is_owner = await self.org_manager.is_organization_owner(user.id, org.org_id)
            if not is_owner:
                await query.answer("خطأ: أنت لست مدير المؤسسة", show_alert=True)
                return
            
            # إزالة العضو
            success = await self.org_manager.remove_member(org.org_id, user.id, member_id)
            
            if success:
                member_name = self.user_manager.get_display_name_sync(member_id)
                
                # إشعار العضو بالإزالة
                try:
                    await self.application.bot.send_message(
                        chat_id=member_id,
                        text=f"⚠️ تم إزالتك من مؤسسة '{org.name}' بواسطة المدير"
                    )
                except:
                    pass
                
                await query.edit_message_text(
                    f"✅ تم إزالة {member_name} من المؤسسة بنجاح"
                )
                
                await self.logger.log_action(
                    user.id, user.id, "MEMBER_REMOVED",
                    f"Removed: {member_name}, Org: {org.name}",
                    get_user_display_name(user.id)
                )
            else:
                await query.answer("فشل في إزالة العضو", show_alert=True)
        
        elif data == "org_select_db":
            org = await self.org_manager.get_user_organization(user.id)
            if not org:
                await query.answer("⚠️ لا توجد مؤسسة", show_alert=True)
                return

            # الحصول على اتصالات المؤسسة بشكل صحيح (await + active only)
            org_connections = await self.db_manager.get_organization_connections(org.org_id)
            if not org_connections:
                await query.answer("لا توجد قواعد بيانات متاحة", show_alert=True)
                return

            current_user = self.user_manager.get_user_sync(user.id)
            
            keyboard = []
            for conn in org_connections:
                is_selected = current_user and current_user.current_database == conn.connection_id
                emoji = "✅ " if is_selected else ""
                keyboard.append([
                    InlineKeyboardButton(f"{emoji}{conn.name}", callback_data=f"select_db_{conn.connection_id}")
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="org_back_menu")])
            
            await query.edit_message_text(
                f"🗄️ **اختيار قاعدة البيانات**\n\n"
                f"المؤسسة: {org.name}\n\n"
                f"قواعد البيانات المتاحة:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        
        elif data == "org_info":
            org = await self.org_manager.get_user_organization(user.id)
            if not org:
                await query.edit_message_text("المؤسسة غير موجودة")
                return
            
            stats = await self.org_manager.get_organization_statistics(org.org_id)
            
            info_text = f"🏢 **{org.name}**\n\n"
            info_text += f"📊 **الإحصائيات:**\n"
            info_text += f"  👥 الأعضاء: {stats['members_count']}\n"
            info_text += f"  🗄️ قواعد البيانات: {stats['databases_count']}\n"
            info_text += f"  🔗 دعوات نشطة: {stats['active_invitations']}\n"
            info_text += f"  ✓ دعوات مستخدمة: {stats['expired_invitations']}\n"
            info_text += f"📅 تاريخ الإنشاء: {stats['created_at'][:10]}\n"
            
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="org_back_menu")]]
            
            await query.edit_message_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                
            )
        
        elif data == "org_back_menu":
            # العودة لقائمة المؤسسة الرئيسية
            org = await self.org_manager.get_user_organization(user.id)
            if not org:
                await query.edit_message_text("المؤسسة غير موجودة")
                return
            
            is_owner = await self.org_manager.is_organization_owner(user.id, org.org_id)
            
            keyboard = []
            
            if is_owner:
                keyboard.append([InlineKeyboardButton("➕ إضافة قاعدة بيانات", callback_data="org_add_db")])
                keyboard.append([InlineKeyboardButton("🔗 إنشاء رابط دعوة", callback_data="org_create_invite")])
                keyboard.append([InlineKeyboardButton("👥 إدارة الأعضاء", callback_data="org_manage_members")])
            
            keyboard.append([InlineKeyboardButton("🗄️ اختيار قاعدة بيانات", callback_data="org_select_db")])
            keyboard.append([InlineKeyboardButton("📊 معلومات المؤسسة", callback_data="org_info")])
            
            await query.edit_message_text(
                f"🏢 {org.name}\n\n"
                f"دورك: {'👑 المدير' if is_owner else '👥 عضو'}\n"
                f"أعضاء: {len(org.members)} | قواعد: {len(org.database_connections)}\n\n"
                f"اختر خياراً:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )


    
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
    # معالج الأوامر الإضافية


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
            """عرض السجل مع تنسيق محسّن"""
            user = update.effective_user
            chat_id = update.effective_chat.id
            
            try:
                # جلب التاريخ
                conversations = await self.llm_service.conversation_manager.get_chat_history(
                    chat_id, limit=10
                )
                
                if not conversations:
                    await update.message.reply_text(
                        "📭 لا يوجد سجل محادثات بعد"
                    )
                    return
                
                # بناء الرسالة بشكل منظم
                history_text = "📋 *آخر المحادثات:*\n"
                history_text += "=" * 40 + "\n\n"                
                for i, conv in enumerate(conversations, 1):
                    question = conv['question'] or 'بدون سؤال'
                    role = "👤" if conv['role'] == 'user' else "🤖"
                    
                    # صيغة مختصرة إذا كان النص طويل
                    if len(question) >= 60:
                        question = question + "..."
                    
                    history_text += f"{i}. {role} {question}\n"
                    
                    # إضافة الإجابة إذا كانت موجودة
                    answer = conv['answer']
                    if answer:
                        answer_preview = answer
                        history_text += f"   💬 _{answer_preview}_\n"
                    
                
                # إرسال الرسالة بتنسيق أفضل
                await update.message.reply_text(
                    history_text,
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
                
                # تسجيل الإجراء
                await self.logger.log_action(
                    user.id, 
                    chat_id, 
                    "HISTORY_VIEWED",
                    f"User viewed {len(conversations)} conversation entries",
                    get_user_display_name(user.id)
                )
                
            except Exception as e:
                print(f"❌ خطأ في عرض السجل: {e}")
                await update.message.reply_text(
                    "❌ حدث خطأ أثناء جلب السجل. حاول لاحقاً",
                    parse_mode="Markdown"
                )


    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /stats"""
        chat_id = update.effective_chat.id
        
        stats = await self.logger.get_chat_statistics(chat_id)
        
        stats_message = f"""
📊 إحصائيات محادثتك الشخصية:

💬 إجمالي المحادثات: {stats['total_conversations']}
📊 استعلامات SQL: {stats['sql_queries_count']}

⏰ أول رسالة: {stats['first_message'] or 'غير متاح'}
⏰ آخر رسالة: {stats['last_message'] or 'غير متاح'}

💡 هذه إحصائيات محادثتك الشخصية معي فقط
        """
        
        await update.message.reply_text(stats_message.strip())

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الرسائل النصية - محسّن للتوازي"""
        user = update.effective_user
        chat_id = update.effective_chat.id
        question = update.message.text
        user_info = self.user_manager.get_user_sync(user.id)
        result = await self.db_manager.verify_user_can_access_database(user.id, user_info.current_database)
        can_access = result[0]

        if not user_info.current_database :
            await update.message.reply_text(
                f"اختر قاعدة بيانات ثم اكمل"
            )
            return
        elif not can_access:
            await update.message.reply_text(
                f"اختر قاعدة بيانات ثم اكمل"
            )
            return
        # else:
        #     await update.message.reply_text(
        #         f"{user_info.current_database}\n"
        #         f"{await self.db_manager.verify_user_can_access_database(user.id, user_info.current_database)}\n"
        #         f"{can_access}\n"
        #         f"{not user_info.current_database and can_access}"
        #     )
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
            self._process_question_wrapper(update, context, user, chat_id, question, user_info.current_database, user_info.current_database_type)
        )
        
        # تتبع الـ task
        await self._track_request(user.id, task)
    
    async def _process_question_wrapper(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user,
        chat_id: int,
        question: str,
        db_id: Any,
        db_type: str
    ):
        """Wrapper للمعالجة مع تتبع وتنظيف"""
        task = asyncio.current_task()
        try:
            await self._process_question(update, context, user, chat_id, question, db_id, db_type)
        finally:
            await self._untrack_request(user.id, task)
    
    async def _process_question(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE,
        user, 
        chat_id: int, 
        question: str,
        db_id: Any,
        db_type: str
    ):
        """معالجة السؤال بشكل مستقل - محسّن"""
        try:
            
            # إرسال "يكتب..." وتسجيل في نفس الوقت
            await self.logger.log_action(
                user.id, chat_id, "QUESTION_ASKED",
                f"Question: {question[:100]}...", f"{user.first_name} {user.last_name}"
            )
            org = await self.org_manager.get_user_organization(user.id)
            # معالجة السؤال مع قاعدة البيانات المحددة
            if org:
                answer, sql_query, sql_result, history_len, mail = await self.llm_service.handle_question(
                    user_question=question,
                    username=user.full_name,
                    chat_id=chat_id,
                    user_id=user.id,
                    database_id=db_id,  # 🆕 تمرير معرف قاعدة البيانات
                    org_id=org.org_id,
                    db_type=db_type
                )
            else:
                answer, sql_query, sql_result, history_len, mail = await self.llm_service.handle_question(
                    user_question=question,
                    username=user.full_name,
                    chat_id=chat_id,
                    user_id=user.id,
                    database_id=db_id,  # 🆕 تمرير معرف قاعدة البيانات
                    db_type=db_type
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
                f"SQL: {sql_query}, Email: {mail}", user.full_name
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
                f"Error: {str(e)}", user.full_name
            )

# استكمال تحديث help_command في telegram_service.py

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /help - محدث"""
        user = update.effective_user
        org = await self.org_manager.get_user_organization(user.id)
        
        help_message = """📚 **دليل الاستخدام الشامل**

    ═══════════════════════════════════

    🔹 **الأسئلة العادية:**
    يمكنك طرح أي سؤال متعلق بالمتجر وسأجيب عليه

    🔹 **استعلامات البيانات:**
    اسأل عن المبيعات، المنتجات، العملاء، الفروع

    🔹 **رسائل البريد الإلكتروني:**
    قل "أرسل إيميل إلى..." وسأساعدك في إنشاء وإرسال الرسالة

    ═══════════════════════════════════

    """
        
        if org:
            is_owner = await self.org_manager.is_organization_owner(user.id, org.org_id)
            
            if is_owner:
                help_message += """👑 **أوامر مدير المؤسسة:**

    📊 **إدارة قواعد البيانات:**
    /adddb <الاسم> <رابط_الاتصال>
    - إضافة قاعدة بيانات للمؤسسة
    - مثال: `/adddb CompanyDB postgresql://user:pass@localhost/db`

    👥 **إدارة الأعضاء:**
    /invite [عدد_الاستخدامات] [ساعات_الصلاحية]
    - إنشاء رابط دعوة آمن
    - مثال: `/invite 5 48` (5 استخدامات، صالح 48 ساعة)

    /org
    - عرض قائمة إدارة المؤسسة
    - إزالة الأعضاء، إضافة قواعد بيانات

    /orginfo
    - عرض معلومات تفصيلية عن المؤسسة

    ℹ️ **التفاصيل:**
    • أعضاء المؤسسة لا يمكنهم مغادرة المؤسسة ذاتياً
    • يجب عليك إزالتهم إذا أردت
    • جميع الأعضاء يمكنهم استخدام قواعد البيانات المضافة

    """
            else:
                help_message += """👥 **أوامر عضو المؤسسة:**

    /selectdb
    - اختيار قاعدة بيانات للاستعلام عليها
    - تتوفر قواعد البيانات التي أضافها مدير المؤسسة

    /orginfo
    - عرض معلومات المؤسسة والأعضاء والقواعد

    /myinfo
    - عرض معلوماتك الشخصية وحالتك في المؤسسة

    ℹ️ **التفاصيل:**
    • لا يمكنك إضافة قواعد بيانات شخصية
    • لا يمكنك مغادرة المؤسسة ذاتياً
    • تواصل مع مدير المؤسسة للمشاكل

    """
        else:
            help_message += """👤 **أوامر المستخدم المستقل:**

    🏢 **إدارة المؤسسات:**
    /createorg <اسم_المؤسسة>
    - إنشاء مؤسسة جديدة
    - مثال: `/createorg شركة التقنية المتقدمة`

    /join <كود_الدعوة>
    - الانضمام لمؤسسة عبر رابط دعوة
    - احصل على الكود من مدير المؤسسة

    📊 **إدارة قواعد البيانات:**
    /adddb <الاسم> <رابط_الاتصال>
    - إضافة قاعدة بيانات شخصية
    - مثال: `/adddb MyDB postgresql://user:pass@localhost/mydb`

    /selectdb
    - اختيار قاعدة بيانات للاستعلام عليها

    ℹ️ **التفاصيل:**
    • يمكنك إنشاء مؤسسة ودعوة أعضاء
    • قواعد البيانات الشخصية لك وحدك
    • عند الانضمام لمؤسسة، لا يمكنك إضافة قواعد شخصية

    """
        
        help_message += """
    ═══════════════════════════════════

    🔹 **الأوامر المشتركة:**

    /myinfo - معلومات حسابك والمؤسسة
    /clear - مسح سجل المحادثة
    /history - عرض آخر 10 محادثات
    /stats - إحصائيات محادثاتك

    ═══════════════════════════════════

    💡 **نصائح:**
    • كن واضحاً في أسئلتك
    • يمكن الرجوع لسجل المحادثات
    • اختر قاعدة البيانات قبل الاستعلام
    • تواصل مع الدعم عند المشاكل
    """
        
        await update.message.reply_text(help_message, )
        await self.logger.log_action(
            user.id, update.effective_chat.id, 
            "HELP_COMMAND", "User requested help", get_user_display_name(user.id)
        )
    async def cleanup(self):
        """تنظيف الموارد"""
        await self.llm_service.cleanup()
        # await self.llm_service.conversation_manager.stop_writer()
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
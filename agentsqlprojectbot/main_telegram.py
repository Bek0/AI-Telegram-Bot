# /main_telegram.py

import os
import sys
import asyncio
import logging
import signal
from pathlib import Path
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/bot.log', encoding='utf-8')
    ]
)

# إضافة المجلد الحالي إلى مسار Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

class BotValidator:
    """مدقق صحة البيئة والمتطلبات"""
    
    REQUIRED_ENV_VARS = {
        'TELEGRAM_BOT_TOKEN': 'توكن بوت تليجرام مطلوب',
        # 'GOOGLE_APPLICATION_CREDENTIALS': 'ملف اعتماد Google Cloud مطلوب',
        'BOT_EMAIL': 'إيميل البوت مطلوب للإيميلات',
        'BOT_EMAIL_PASS': 'كلمة مرور البوت مطلوبة',
        'MASTER_PASSWORD_HASH': 'هاش كلمة مرور المدير الرئيسي (SHA-256)'
    }
    
    OPTIONAL_ENV_VARS = {
        'DATABASE_URI': 'رابط قاعدة البيانات (اختياري)',
        'ADMIN_TELEGRAM_IDS': 'معرفات المدراء (اختياري)'
    }
    
    REQUIRED_DIRECTORIES = [
        'logs',
        'logs/conversations',
        'services',
        'memory',
        'models'
    ]
    
    @staticmethod
    def validate_environment() -> bool:
        """التحقق من صحة متغيرات البيئة المطلوبة"""
        missing_vars = []
        
        for var, description in BotValidator.REQUIRED_ENV_VARS.items():
            if not os.getenv(var):
                missing_vars.append(f"  • {var}: {description}")
        
        if missing_vars:
            logger.error("❌ متغيرات البيئة المطلوبة غير موجودة:")
            for var in missing_vars:
                logger.error(var)
            logger.error("\nيرجى إنشاء ملف .env وإضافة هذه المتغيرات.")
            return False
        
        logger.info("✅ تم التحقق من متغيرات البيئة بنجاح")
        
        # عرض المتغيرات الاختيارية
        for var, description in BotValidator.OPTIONAL_ENV_VARS.items():
            if os.getenv(var):
                logger.info(f"✅ {var}: مكوّن")
            else:
                logger.warning(f"⚠️  {var}: غير مكوّن ({description})")
        
        return True
    
    @staticmethod
    def check_dependencies() -> bool:
        """التحقق من وجود المكتبات المطلوبة"""
        required_modules = [
            ('telegram', 'python-telegram-bot'),
            # ('langchain_google_vertexai', 'langchain-google-vertexai'),
            ('langchain_community', 'langchain-community'),
            ('aiofiles', 'aiofiles'),
            ('dotenv', 'python-dotenv')
        ]
        
        missing_modules = []
        
        for module_name, package_name in required_modules:
            try:
                __import__(module_name)
            except ImportError:
                missing_modules.append(package_name)
        
        if missing_modules:
            logger.error("❌ المكتبات المطلوبة غير مثبتة:")
            for module in missing_modules:
                logger.error(f"  • {module}")
            logger.error("\nيرجى تثبيت المتطلبات: pip install -r requirements.txt")
            return False
        
        logger.info("✅ تم التحقق من المكتبات المطلوبة بنجاح")
        return True
    
    @staticmethod
    def create_directories() -> bool:
        """إنشاء المجلدات المطلوبة"""
        try:
            for directory in BotValidator.REQUIRED_DIRECTORIES:
                Path(directory).mkdir(parents=True, exist_ok=True)
            
            logger.info("✅ تم إنشاء/التحقق من المجلدات المطلوبة")
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء المجلدات: {e}")
            return False
    
    @staticmethod
    def check_google_credentials() -> bool:
        """التحقق من ملف Google credentials"""
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not credentials_path:
            logger.error("❌ GOOGLE_APPLICATION_CREDENTIALS غير محدد")
            return False
        
        if not os.path.exists(credentials_path):
            logger.error(f"❌ ملف Google credentials غير موجود: {credentials_path}")
            return False
        
        logger.info(f"✅ تم العثور على ملف Google credentials: {credentials_path}")
        return True


class BotRunner:
    """مدير تشغيل البوت - محسّن للتوازي"""
    
    def __init__(self):
        self.bot = None
        self.llm_service = None
        self.shutdown_event = asyncio.Event()
    
    def print_startup_banner(self):
        """طباعة معلومات بدء التشغيل"""
        banner = """
╔════════════════════════════════════════════════════════════╗
║      🤖 بوت المتاجر الذكي - إصدار محسّن للتوازي         ║
║              Enhanced Parallel Version v2.0               ║
╚════════════════════════════════════════════════════════════╝
"""
        print(banner)
        
        # معلومات التكوين
        print("📋 معلومات التكوين:")
        print(f"  📱 توكن البوت: {os.getenv('TELEGRAM_BOT_TOKEN', 'غير محدد')[:20]}...")
        
        admin_ids = os.getenv('ADMIN_TELEGRAM_IDS', 'غير محدد')
        print(f"  🔐 معرفات المدراء: {admin_ids}")
        
        db_uri = os.getenv('DATABASE_URI', '')
        db_status = "متصل" if db_uri else "غير متصل"
        print(f"  🗄️  قاعدة البيانات: {db_status}")
        
        email = os.getenv('BOT_EMAIL', 'غير محدد')
        print(f"  📧 البريد الإلكتروني: {email}")
        
        # print(f"  🌍 Google Vertex AI: {'مكوّن' if os.getenv('GOOGLE_APPLICATION_CREDENTIALS') else 'غير مكوّن'}")
        print(f"  ⚡ التوازي: مفعّل (ThreadPoolExecutor)")
        print(f"  🔄 Rate Limiting: مفعّل (Token Bucket)")
        print(f"  💾 Caching: مفعّل (History + SQL)")
        print("═" * 60)
    
    async def initialize_services(self):
        """تهيئة الخدمات"""
        logger.info("🔄 جاري تهيئة الخدمات...")
        
        try:
            # تهيئة LLM Service
            from services.telegram_llm_service import get_llm_service
            self.llm_service = get_llm_service()
            logger.info("✅ تم تهيئة خدمة LLM (مع ThreadPoolExecutor)")
            await self.llm_service.startup()
            # # بدء writers بالتوازي
            # await asyncio.gather(
            #     self.llm_service.conversation_manager.start_writer(),
            #     self._start_logger_writer()
            # )
            logger.info("✅ تم تهيئة جميع الخدمات بنجاح")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ فشل في تهيئة الخدمات: {e}", exc_info=True)
            return False
    
    async def _start_logger_writer(self):
        """بدء logger writer"""
        from services.telegram_logging import TelegramLogger
        logger_service = TelegramLogger()
        await logger_service.start_writer()
    
    async def cleanup_services(self):
        """تنظيف الخدمات"""
        logger.info("🧹 جاري تنظيف الخدمات...")
        
        try:
            if self.llm_service:
                # إيقاف الـ writers بالتوازي
                # await asyncio.gather(
                #     self.llm_service.conversation_manager.stop_writer(),
                #     self._stop_logger_writer(),
                #     return_exceptions=True
                # )
                
                # تنظيف الموارد
                await self.llm_service.cleanup()
                logger.info("✅ تم إيقاف conversation writer")
            
            logger.info("✅ تم تنظيف جميع الخدمات")
            
        except Exception as e:
            logger.error(f"⚠️  خطأ أثناء التنظيف: {e}")
    
    async def _stop_logger_writer(self):
        """إيقاف logger writer"""
        from services.telegram_logging import TelegramLogger
        logger_service = TelegramLogger()
        await logger_service.stop_writer()
    
    def setup_signal_handlers(self):
        """إعداد معالجات الإشارات للإيقاف الآمن"""
        def signal_handler(signum, frame):
            logger.info(f"\n🛑 تم استقبال إشارة {signum} - جاري الإيقاف الآمن...")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def run(self):
        """تشغيل البوت"""
        logger.info("🚀 بدء تشغيل بوت تليجرام...")
        
        # التحقق من صحة البيئة
        if not BotValidator.validate_environment():
            sys.exit(1)
        
        # التحقق من المكتبات
        if not BotValidator.check_dependencies():
            sys.exit(1)
        
        # # # التحقق من Google credentials
        # # if not BotValidator.check_google_credentials():
        # #     sys.exit(1)
        
        # إنشاء المجلدات
        if not BotValidator.create_directories():
            sys.exit(1)
        
        # طباعة معلومات التشغيل
        self.print_startup_banner()
        
        try:
            # إعداد معالجات الإشارات
            self.setup_signal_handlers()
            
            # تهيئة الخدمات
            logger.info("🔧 جاري تهيئة الخدمات...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            if not loop.run_until_complete(self.initialize_services()):
                logger.error("❌ فشل في تهيئة الخدمات")
                sys.exit(1)
            
            # استيراد وتشغيل البوت
            from services.telegram_service import TelegramBot
            
            logger.info("✅ جميع الأنظمة جاهزة!")
            logger.info("🔄 جاري تشغيل البوت...")
            logger.info("💡 اضغط Ctrl+C للتوقف")
            print("─" * 60)
            
            # إنشاء البوت
            self.bot = TelegramBot(self.llm_service)
            
            # تشغيل البوت
            self.bot.run()
            
        except KeyboardInterrupt:
            logger.info("\n🛑 تم إيقاف البوت بواسطة المستخدم")
            
        except ImportError as e:
            logger.error(f"❌ خطأ في استيراد ملفات البوت: {e}", exc_info=True)
            logger.error("💡 تأكد من وجود جميع الملفات المطلوبة")
            sys.exit(1)
            
        except Exception as e:
            logger.error(f"❌ خطأ غير متوقع: {e}", exc_info=True)
            sys.exit(1)
            
        finally:
            # تنظيف الموارد
            try:
                logger.info("🧹 جاري تنظيف الموارد...")
                loop = asyncio.get_event_loop()
                loop.run_until_complete(self.cleanup_services())
                # ✅ إضافة: إغلاق Connection Pool
                from db_connection import dispose_engines
                dispose_engines()
                logger.info("👋 شكراً لاستخدام البوت!")
            except Exception as e:
                logger.error(f"⚠️  خطأ أثناء التنظيف النهائي: {e}")
            finally:
                try:
                    loop.close()
                except:
                    pass


def main():
    """نقطة الدخول الرئيسية"""
    runner = BotRunner()
    runner.run()


if __name__ == "__main__":
    main()
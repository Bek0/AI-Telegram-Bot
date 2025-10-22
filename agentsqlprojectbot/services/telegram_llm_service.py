# services/telegram_llm_service.py
import asyncio
from typing import Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from models.pydantic_models import Summary, Mail
from memory.telegram_conversation import OptimizedConversationManager
from services.send_email import EmailService
from services.sql_service import SQLService
from services.database_manager import get_database_manager
from utils.prompts import (
    TEMPLATE_INSTRUCTIONS, SCHEMA, SCHEMA_EXAMPLES,
    EMAIL_TEMPLATE, PROMPT_TEMPLATE
)

from services.token_cost_calculator import TokenCostCalculator

load_dotenv()

class TelegramLLMService:
    """خدمة LLM محسّنة للتواز الكامل مع تسجيل قاعدة بيانات ودعم قواعد بيانات متعددة والمؤسسات"""
    
    def __init__(self, max_workers: int = 10):
        # LLMs
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        self.small_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
        
        # Parsers
        self.summary_parser = PydanticOutputParser(pydantic_object=Summary)
        self.mail_parser = PydanticOutputParser(pydantic_object=Mail)
        
        # Services
        self.conversation_manager = OptimizedConversationManager(
            conversations_dir="logs/conversations",
            max_conversations=5
        )
        self.email_service = EmailService()
        
        # Database Manager
        self.db_manager = get_database_manager()
        
        # Thread Pool للعمليات blocking
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="LLM_Worker"
        )
        
        # Chains
        self.summary_chain = self._create_summary_chain()
        self.mail_chain = self._create_mail_chain()
        
        # Schema data
        self.schema_text = "\n".join([
            f"{table}: {', '.join(cols)}" 
            for table, cols in SCHEMA.items()
        ])
        self.schema_examples_text = "\n".join([
            f"{table}: {rows}" 
            for table, rows in SCHEMA_EXAMPLES.items()
        ])
        
        # Cache for history
        self._history_cache = {}
        self._cache_lock = asyncio.Lock()
        self._cache_timeout = 60
        
        self.cost_calculator = TokenCostCalculator()
        
        # تخزين مؤقت للمراحل أثناء المحادثة
        self._current_conversation_stages = []
    
    def _create_summary_chain(self):
        """إنشاء chain لمعالجة الأسئلة"""
        global prompt_summary
        prompt_summary = PromptTemplate(
            template=PROMPT_TEMPLATE,
            input_variables=["schema_text", "history_text", "user_question", "format_instructions"]
        )
        return prompt_summary | self.llm | self.summary_parser
    
    def _create_mail_chain(self):
        """إنشاء chain لتوليد الإيميلات"""
        global prompt_mail
        prompt_mail = PromptTemplate(
            template=EMAIL_TEMPLATE,
            input_variables=["user_question", "sql_result", 
                           "format_instructions", "history_text", "template_instructions"]
        )
        return prompt_mail | self.llm | self.mail_parser
    
    async def _get_cached_history(self, chat_id: int) -> str:
        """الحصول على التاريخ مع caching ذكي"""
        return await self.conversation_manager.get_cached_history(chat_id)

    async def _generate_summary(
        self, 
        user_question: str, 
        chat_id: int, 
        username: str, 
        timestamp: str,
        database_id: Optional[str] = None
    ) -> Summary:
        """توليد ملخص السؤال مع SQL query"""
        history_text = await self._get_cached_history(chat_id)
        
        schema_text = self.schema_text
        schema_examples = self.schema_examples_text
    
        input_data = {
            "schema_text": schema_text,
            "schema_examples": schema_examples,
            "history_text": history_text,
            "user_question": user_question,
            "format_instructions": self.summary_parser.get_format_instructions()
        }
        
        loop = asyncio.get_event_loop()
        input_text = prompt_summary.format(**input_data)
        input_tokens = await self.cost_calculator.count_tokens(
            self.llm, 
            input_text, 
            self.executor
        )
        
        summary = await loop.run_in_executor(
            self.executor,
            lambda: self.summary_chain.invoke(input_data)
        )
        
        summary_text = str(summary)
        output_tokens = await self.cost_calculator.count_tokens(
            self.llm,
            summary_text,
            self.executor
        )
        
        print("Summary Generation input - gemini-2.5-flash")
        print("input tokens:", input_tokens)
        print(input_text)
        print("Summary Generation output - gemini-2.5-flash")
        print("output tokens:", output_tokens)
        print(summary_text)
        stage_data = self.cost_calculator.create_stage_record(
            stage_number=1,
            stage_name="Summary Generation",
            model="gemini-2.5-flash",
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        
        self._current_conversation_stages.append(stage_data)
        
        return summary, history_text
    
    async def _process_sql_query(
        self, 
        summary: Summary, 
        user_question: str, 
        chat_id: int, 
        username: str, 
        timestamp: str,
        database_id: Optional[str] = None
    ) -> str:
        """معالجة SQL query وإرجاع الإجابة"""
        if not summary.sql_query:
            return summary.answer or "لم يتم العثور على إجابة"
        
        if database_id:
            db = await self.db_manager.get_database_instance(database_id)
            if not db:
                return "❌ فشل في الاتصال بقاعدة البيانات المحددة"
            sql_service = SQLService(db=db)
        else:
            return "❌ لم يتم تحديد قاعدة بيانات"
        
        sql_result = await sql_service.execute_async(summary.sql_query)
        
        prompt = f"""
You are a helpful assistant for a Telegram bot.
Use only the following SQL result to answer the user's question.
Do not invent, assume, or estimate anything.

User question: {user_question}
SQL query: {summary.sql_query}
SQL result: {sql_result}

If the SQL result is empty, respond in natural language indicating no records were found.
Provide a clear and concise answer. Use Arabic or English based on the user's question language.
Keep the response suitable for Telegram messaging (not too long, well formatted).
"""
                
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            self.executor,
            lambda: self.small_llm.invoke(prompt)
        )
        
        output_tokens = await self.cost_calculator.count_tokens(
            self.small_llm,
            response.content,
            self.executor
        )
        
        input_tokens = await self.cost_calculator.count_tokens(
            self.small_llm,
            prompt,
            self.executor
        )
        print("SQL Response Generation input - gemini-2.0-flash")
        print("input tokens:", input_tokens)
        print(prompt)
        print("SQL Response Generation output - gemini-2.0-flash")
        print("output tokens:", output_tokens)
        print(response.content)
        stage_data = self.cost_calculator.create_stage_record(
            stage_number=2,
            stage_name="SQL Response Generation",
            model="gemini-2.0-flash",
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        
        self._current_conversation_stages.append(stage_data)
        
        return response.content
    
    async def _generate_email(
        self, 
        summary: Summary, 
        user_question: str, 
        chat_id: int, 
        username: str, 
        timestamp: str,
        database_id: Optional[str] = None,
        history_text: str = None
    ) -> Mail:
        """توليد محتوى الإيميل"""
        tasks = []
        
        if summary.sql_query and database_id:
            db = await self.db_manager.get_database_instance(database_id)
            if db:
                sql_service = SQLService(db=db)
                tasks.append(sql_service.execute_async(summary.sql_query))
            else:
                tasks.append(asyncio.sleep(0))
        
        results = await asyncio.gather(*tasks)
        sql_result = results[0] if len(results) > 0 else None
        
        input_data = {
            "user_question": user_question,
            "history_text": history_text,
            "sql_result": sql_result or "",
            "format_instructions": self.mail_parser.get_format_instructions(),
            "template_instructions": TEMPLATE_INSTRUCTIONS
        }
        
        loop = asyncio.get_event_loop()
        input_text = prompt_mail.format(**input_data)
        input_tokens = await self.cost_calculator.count_tokens(
            self.llm,
            input_text,
            self.executor
        )
        
        mail = await loop.run_in_executor(
            self.executor,
            lambda: self.mail_chain.invoke(input_data)
        )
        
        output_tokens = await self.cost_calculator.count_tokens(
            self.llm,
            str(mail),
            self.executor
        )
        print("Email Generation input - gemini-2.5-flash")
        print("input tokens:", input_tokens)
        print(input_text)
        print("Email Generation output - gemini-2.5-flash")
        print("output tokens:", output_tokens)
        print(str(mail))
        stage_data = self.cost_calculator.create_stage_record(
            stage_number=3,
            stage_name="Email Generation",
            model="gemini-2.5-flash",
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )
        
        self._current_conversation_stages.append(stage_data)
        
        return mail
    
    async def handle_question(
        self, 
        user_question: str, 
        username: str, 
        chat_id: int,
        user_id: int = None,
        database_id: Optional[str] = None,
        org_id: Optional[str] = None
    ) -> Tuple[str, Optional[str], Optional[str], int, Optional[Mail], Optional[str]]:
        """معالجة السؤال بشكل كامل مع دعم قواعد بيانات متعددة والمؤسسات"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # مسح التخزين المؤقت للمحادثة السابقة
        self._current_conversation_stages = []
        
        # الخطوة 1: توليد الملخص
        summary, history_text = await self._generate_summary(
            user_question, chat_id, username, timestamp, database_id
        )
        
        answer = None
        sql_query = summary.sql_query
        sql_result = None
        mail = None
        
        # الخطوة 2: معالجة حسب النوع
        if summary.way and summary.way.lower() == "sqlquery":
            answer = await self._process_sql_query(
                summary, user_question, chat_id, username, timestamp, database_id
            )

        elif summary.way and summary.way.lower() == "email":
            try:
                mail = await self._generate_email(
                    summary, user_question, chat_id, username, timestamp, database_id, history_text
                )
                
                answer = f"تم إنشاء معاينة الإيميل للمرسل إليهم: {', '.join(mail.email)}"
            except Exception as e:
                print(f"❌ خطأ في توليد الإيميل: {e}")
                answer = "حدث خطأ أثناء إنشاء الإيميل. يرجى المحاولة مرة أخرى."
        
        else:
            answer = summary.answer or "تم الرد من تاريخ المحادثة."
        
        if answer is None:
            answer = "عذراً، لم أتمكن من توليد إجابة"

        # الخطوة 3: حفظ السياق
        save_task = self.conversation_manager.save_context(
            chat_id=chat_id,
            question=user_question,
            answer=answer,
            user_id=user_id,
            username=username,
            sql_query=sql_query,
            sql_result=str(sql_result) if sql_result else None
        )
        
        memory_task = self.conversation_manager.get_memory_length(chat_id)
        
        await save_task
        history_len = await memory_task
        
        # الخطوة 4: حفظ المحادثة مع معرف المؤسسة وقاعدة البيانات
        conversation_id = self.cost_calculator.save_conversation(
            chat_id=chat_id,
            user_id=user_id,
            username=username,
            user_question=user_question,
            org_id=org_id,
            database_id=database_id
        )
        
        # الخطوة 5: حفظ جميع المراحل والإحصائيات
        if self._current_conversation_stages and conversation_id:
            total_input_tokens = sum(s["input_tokens"] for s in self._current_conversation_stages)
            total_output_tokens = sum(s["output_tokens"] for s in self._current_conversation_stages)
            total_tokens = sum(s["total_tokens"] for s in self._current_conversation_stages)
            total_input_cost = sum(float(s["cost"]["input"]) for s in self._current_conversation_stages)
            total_output_cost = sum(float(s["cost"]["output"]) for s in self._current_conversation_stages)
            total_cost = sum(float(s["cost"]["total"]) for s in self._current_conversation_stages)
            
            # ✅ حفظ كل مرحلة على حدة
            for stage in self._current_conversation_stages:
                self.cost_calculator.save_stage(
                    conversation_id=conversation_id,
                    chat_id=chat_id,
                    stage_number=stage["stage_number"],
                    stage_name=stage["stage_name"],
                    model=stage["model"],
                    input_tokens=stage["input_tokens"],
                    output_tokens=stage["output_tokens"],
                    total_tokens=stage["total_tokens"],
                    input_cost=float(stage["cost"]["input"]),
                    output_cost=float(stage["cost"]["output"]),
                    total_cost=float(stage["cost"]["total"])
                )
            
            # ✅ حفظ ملخص المحادثة
            self.cost_calculator.save_conversation_summary(
                conversation_id=conversation_id,
                chat_id=chat_id,
                total_stages=len(self._current_conversation_stages),
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                total_tokens=total_tokens,
                input_cost=total_input_cost,
                output_cost=total_output_cost,
                total_cost=total_cost,
                stages=self._current_conversation_stages
            )
            
            # ✅ تحديث استخدام النماذج
            for stage in self._current_conversation_stages:
                self.cost_calculator.update_model_usage(
                    chat_id=chat_id,
                    model=stage["model"],
                    input_tokens=stage["input_tokens"],
                    output_tokens=stage["output_tokens"],
                    total_tokens=stage["total_tokens"],
                    input_cost=float(stage["cost"]["input"]),
                    output_cost=float(stage["cost"]["output"]),
                    total_cost=float(stage["cost"]["total"]),
                    org_id=org_id
                )
            
            # ✅ تحديث استخدام المراحل
            for stage in self._current_conversation_stages:
                self.cost_calculator.update_stage_usage(
                    chat_id=chat_id,
                    stage_name=stage["stage_name"],
                    input_tokens=stage["input_tokens"],
                    output_tokens=stage["output_tokens"],
                    total_tokens=stage["total_tokens"],
                    input_cost=float(stage["cost"]["input"]),
                    output_cost=float(stage["cost"]["output"]),
                    total_cost=float(stage["cost"]["total"]),
                    org_id=org_id
                )
            
            
            # طباعة ملخص للتوكنات والتكاليف
            print(f"\n📊 استخدام التوكنات:")
            print(f"   • إجمالي التوكنات: {total_tokens}")
            print(f"   • التكاليف:")
            print(f"     - Input: ${total_input_cost:.8f}")
            print(f"     - Output: ${total_output_cost:.8f}")
            print(f"     - الإجمالي: ${total_cost:.8f}")
            print(f"   • عدد المراحل: {len(self._current_conversation_stages)}")
            if org_id:
                print(f"   • المؤسسة: {org_id}")
            if database_id:
                print(f"   • قاعدة البيانات: {database_id}")
            print()

        return answer, sql_query, sql_result, history_len, mail

    async def send_email(self, mail: Mail) -> str:
        """إرسال إيميل بشكل async"""
        return await self.email_service.send_async(
            subject=mail.subject,
            body=mail.body,
            recipients=mail.email
        )
    
    async def cleanup(self):
        """تنظيف الموارد"""
        await self.conversation_manager.stop_writer()
        self.executor.shutdown(wait=True)


# Singleton instance
_llm_service = None

def get_llm_service() -> TelegramLLMService:
    """الحصول على instance واحد من الخدمة"""
    global _llm_service
    if _llm_service is None:
        _llm_service = TelegramLLMService(max_workers=10)
    return _llm_service
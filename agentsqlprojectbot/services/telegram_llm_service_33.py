import asyncio
import json
import os
from typing import Tuple, Optional
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from models.pydantic_models import Summary, Mail
from memory.telegram_conversation import ConversationManager
from services.send_email import EmailService
from services.sql_service import SQLService
from utils.prompts import (
    TEMPLATE_INSTRUCTIONS, SCHEMA, SCHEMA_EXAMPLES,
    EMAIL_TEMPLATE, PROMPT_TEMPLATE
)

load_dotenv()

class TelegramLLMService:
    """خدمة LLM محسّنة للتوازي الكامل مع تسجيل JSON"""
    
    def __init__(self, max_workers: int = 10):
        # LLMs
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
        self.small_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
        
        # Parsers
        self.summary_parser = PydanticOutputParser(pydantic_object=Summary)
        self.mail_parser = PydanticOutputParser(pydantic_object=Mail)
        
        # Services
        self.conversation_manager = ConversationManager()
        self.email_service = EmailService()
        self.sql_service = SQLService()
        
        # Thread Pool للعمليات الـ blocking
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
        
        # Cache للـ history
        self._history_cache = {}
        self._cache_lock = asyncio.Lock()
        self._cache_timeout = 60
        
        # Token logging directory
        self.token_logs_dir = "token_logs"
        os.makedirs(self.token_logs_dir, exist_ok=True)
        
        # تخزين مؤقت للـ stages أثناء المحادثة
        self._current_conversation_stages = []
    
    def _create_summary_chain(self):
        """إنشاء chain لمعالجة الأسئلة"""
        prompt = PromptTemplate(
            template=PROMPT_TEMPLATE,
            input_variables=["schema_text", "history_text", "user_question", "format_instructions"]
        )
        return prompt | self.llm | self.summary_parser
    
    def _create_mail_chain(self):
        """إنشاء chain لتوليد الإيميلات"""
        prompt = PromptTemplate(
            template=EMAIL_TEMPLATE,
            input_variables=["user_question", "sql_result", 
                           "format_instructions", "history_text", "template_instructions"]
        )
        return prompt | self.llm | self.mail_parser
    
    async def _get_cached_history(self, chat_id: int) -> str:
        """الحصول على history مع caching"""
        async with self._cache_lock:
            if chat_id in self._history_cache:
                cached_time, cached_text = self._history_cache[chat_id]
                if (asyncio.get_event_loop().time() - cached_time) < self._cache_timeout:
                    return cached_text
        
        history_text = await self.conversation_manager.get_history_text(chat_id)
        
        async with self._cache_lock:
            self._history_cache[chat_id] = (asyncio.get_event_loop().time(), history_text)
        print(type(history_text))
        print(history_text)
        return history_text
    
    def _invalidate_cache(self, chat_id: int):
        """إلغاء الـ cache بعد إضافة رسالة جديدة"""
        if chat_id in self._history_cache:
            del self._history_cache[chat_id]
    
    async def _count_tokens(self, model: ChatGoogleGenerativeAI, text: str) -> int:
        """حساب عدد التوكنات للنص المعطى"""
        try:
            loop = asyncio.get_event_loop()
            token_count = await loop.run_in_executor(
                self.executor,
                lambda: model.get_num_tokens(text)
            )
            return token_count
        except Exception as e:
            print(f"Error counting tokens: {e}")
            return 0
    
    def _get_model_input_price(self, model_name: str) -> float:
        """الحصول على سعر توكنات الإدخال لكل مليون توكن"""
        if "gemini-2.5-flash" in model_name.lower():
            return 0.30
        elif "gemini-2.0-flash" in model_name.lower():
            return 0.10
        return 0.0

    def _get_model_output_price(self, model_name: str) -> float:
        """الحصول على سعر توكنات الإخراج لكل مليون توكن"""
        if "gemini-2.5-flash" in model_name.lower():
            return 2.50
        elif "gemini-2.0-flash" in model_name.lower():
            return 0.40
        return 0.0
    
    def _get_stage_name(self, stage_num: int, model: str) -> str:
        """الحصول على اسم المرحلة"""
        stages = {
            1: "Summary Generation",
            2: "SQL Response Generation" if "2.0" in model else "Email Generation",
            3: "Email Generation"
        }
        return stages.get(stage_num, f"Stage {stage_num}")
    
    def _load_json_file(self, filepath: str) -> dict:
        """تحميل ملف JSON، إرجاع dict فارغ إذا لم يوجد"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _convert_scientific_notation(self, obj):
        """تحويل الأرقام العلمية إلى أرقام عشرية عادية"""
        if isinstance(obj, dict):
            return {key: self._convert_scientific_notation(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_scientific_notation(item) for item in obj]
        elif isinstance(obj, float):
            # تحويل الأرقام الصغيرة جداً إلى format عادي
            if obj == 0:
                return 0.0
            elif abs(obj) < 0.001:  # للأرقام الصغيرة جداً
                return float(f"{obj:.8f}")
            else:
                return round(obj, 8)
        return obj
    
    def _save_json_file(self, filepath: str, data: dict):
        """حفظ dict في ملف JSON بدون scientific notation"""
        try:
            # تحويل جميع الأرقام العلمية إلى format عادي
            cleaned_data = self._convert_scientific_notation(data)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving JSON file {filepath}: {e}")
    
    def _add_stage_to_details(self, chat_id: int, username: str, 
                             user_question: str, timestamp: str, stage_data: dict):
        """إضافة stage إلى التخزين المؤقت"""
        self._current_conversation_stages.append({
            "chat_id": chat_id,
            "username": username,
            "user_question": user_question,
            "timestamp": timestamp,
            "stage_data": stage_data
        })

    def _save_conversation_to_details_file(self, chat_id: int, username: str, 
                                        user_question: str, timestamp: str):
        """حفظ كل الـ stages في ملف details.json مع ملخص شامل لكل سؤال"""
        details_file = f"{self.token_logs_dir}/chat_{chat_id}_details.json"
        
        # تحميل البيانات الموجودة
        data = self._load_json_file(details_file)
        
        # إنشاء الهيكل الأساسي إذا لم يكن موجوداً
        if not data:
            data = {
                "chat_id": chat_id,
                "username": username,
                "overall_statistics": {
                    "total_conversations": 0,
                    "total_tokens": {
                        "input": 0,
                        "output": 0,
                        "total": 0
                    },
                    "total_cost": {
                        "input": 0.0,
                        "output": 0.0,
                        "total": 0.0
                    },
                    "last_updated": ""
                },
                "conversations": []
            }
        
        # تجميع كل الـ stages للمحادثة الحالية
        stages_for_this_conversation = []
        for stage_info in self._current_conversation_stages:
            if (stage_info["chat_id"] == chat_id and 
                stage_info["timestamp"] == timestamp):
                stages_for_this_conversation.append(stage_info["stage_data"])
        
        # حساب الإحصائيات الإجمالية للسؤال
        if stages_for_this_conversation:
            total_input_tokens = sum(s["input_tokens"] for s in stages_for_this_conversation)
            total_output_tokens = sum(s["output_tokens"] for s in stages_for_this_conversation)
            total_tokens = sum(s["total_tokens"] for s in stages_for_this_conversation)
            
            # حساب التكلفة الإجمالية
            total_input_cost = 0.0
            total_output_cost = 0.0
            
            for stage in stages_for_this_conversation:
                input_price = self._get_model_input_price(stage["model"])
                output_price = self._get_model_output_price(stage["model"])
                input_cost = (stage["input_tokens"] / 1_000_000) * input_price
                output_cost = (stage["output_tokens"] / 1_000_000) * output_price
                total_input_cost += input_cost
                total_output_cost += output_cost
            
            total_cost = total_input_cost + total_output_cost
            
            # إحصائيات حسب النموذج
            models_used = {}
            for stage in stages_for_this_conversation:
                model = stage["model"]
                if model not in models_used:
                    models_used[model] = {
                        "name": model,
                        "times_used": 0,
                        "tokens": {
                            "input": 0,
                            "output": 0,
                            "total": 0
                        },
                        "cost": {
                            "input": 0.0,
                            "output": 0.0,
                            "total": 0.0
                        }
                    }
                
                models_used[model]["times_used"] += 1
                models_used[model]["tokens"]["input"] += stage["input_tokens"]
                models_used[model]["tokens"]["output"] += stage["output_tokens"]
                models_used[model]["tokens"]["total"] += stage["total_tokens"]
                
                input_price = self._get_model_input_price(model)
                output_price = self._get_model_output_price(model)
                input_cost = (stage["input_tokens"] / 1_000_000) * input_price
                output_cost = (stage["output_tokens"] / 1_000_000) * output_price
                
                models_used[model]["cost"]["input"] += input_cost
                models_used[model]["cost"]["output"] += output_cost
                models_used[model]["cost"]["total"] += (input_cost + output_cost)
            
            # تحويل models_used من dict إلى list مرتب
            models_list = sorted(
                models_used.values(), 
                key=lambda x: x["cost"]["total"], 
                reverse=True
            )
            
            # تحديد المرحلة الأكثر استهلاكاً للتوكنات
            most_expensive_stage = max(
                stages_for_this_conversation, 
                key=lambda x: x["total_tokens"]
            ) if stages_for_this_conversation else None
            
            # إضافة المحادثة الجديدة مع الملخص الشامل
            conversation_number = len(data["conversations"]) + 1
            
            conversation_entry = {
                "number": conversation_number,
                "timestamp": timestamp,
                "user_question": user_question,
                "summary": {
                    "total_stages": len(stages_for_this_conversation),
                    "tokens": {
                        "input": total_input_tokens,
                        "output": total_output_tokens,
                        "total": total_tokens,
                    },
                    "cost": {
                        "input": float(f"{total_input_cost:.8f}"),
                        "output": float(f"{total_output_cost:.8f}"),
                        "total": float(f"{total_cost:.8f}"),
                    },
                    "models_breakdown": models_list,
                    "most_expensive_stage": {
                        "name": most_expensive_stage["stage_name"],
                        "tokens": most_expensive_stage["total_tokens"],
                        "percentage": float(f"{(most_expensive_stage['total_tokens'] / total_tokens * 100):.1f}")
                    } if most_expensive_stage else None
                },
                "stages": stages_for_this_conversation
            }
            
            data["conversations"].append(conversation_entry)
            
            # تحديث الإحصائيات العامة
            data["overall_statistics"]["total_conversations"] = len(data["conversations"])
            data["overall_statistics"]["total_tokens"]["input"] += total_input_tokens
            data["overall_statistics"]["total_tokens"]["output"] += total_output_tokens
            data["overall_statistics"]["total_tokens"]["total"] += total_tokens
            data["overall_statistics"]["total_cost"]["input"] += total_input_cost
            data["overall_statistics"]["total_cost"]["output"] += total_output_cost
            data["overall_statistics"]["total_cost"]["total"] += total_cost
            data["overall_statistics"]["last_updated"] = timestamp
            
            # تقريب الأرقام في الإحصائيات العامة
            data["overall_statistics"]["total_cost"]["input"] = float(
                f"{data['overall_statistics']['total_cost']['input']:.8f}"
            )
            data["overall_statistics"]["total_cost"]["output"] = float(
                f"{data['overall_statistics']['total_cost']['output']:.8f}"
            )
            data["overall_statistics"]["total_cost"]["total"] = float(
                f"{data['overall_statistics']['total_cost']['total']:.8f}"
            )
        
        # حفظ الملف
        self._save_json_file(details_file, data)

    def _update_costs_file(self, chat_id: int, username: str, 
                      user_question: str, timestamp: str, 
                      all_stages: list, question_total_tokens: int, 
                      question_total_cost: float):
        """تحديث ملف التكاليف التراكمية مع تفاصيل كل stage وmodel في كل سؤال"""
        costs_file = f"{self.token_logs_dir}/chat_{chat_id}_costs.json"
        
        # تحميل البيانات الموجودة
        data = self._load_json_file(costs_file)
        
        # إنشاء الهيكل الأساسي إذا لم يكن موجوداً
        if not data:
            data = {
                "chat_id": chat_id,
                "username": username,
                "last_updated": timestamp,
                "overview": {
                    "total_conversations": 0,
                    "total_tokens": {
                        "input": 0,
                        "output": 0,
                        "total": 0
                    },
                    "total_cost": {
                        "input": 0.0,
                        "output": 0.0,
                        "total": 0.0
                    }
                },
                "models": [],
                "stages": [],
                "conversation_history": []
            }
        
        # حساب tokens و costs لهذا السؤال
        question_input_tokens = sum(s["input_tokens"] for s in all_stages)
        question_output_tokens = sum(s["output_tokens"] for s in all_stages)
        
        question_input_cost = 0.0
        question_output_cost = 0.0
        
        for stage in all_stages:
            input_price = self._get_model_input_price(stage["model"])
            output_price = self._get_model_output_price(stage["model"])
            question_input_cost += (stage["input_tokens"] / 1_000_000) * input_price
            question_output_cost += (stage["output_tokens"] / 1_000_000) * output_price
        
        # تحديث Overview
        data["overview"]["total_conversations"] += 1
        data["overview"]["total_tokens"]["input"] += question_input_tokens
        data["overview"]["total_tokens"]["output"] += question_output_tokens
        data["overview"]["total_tokens"]["total"] += question_total_tokens
        data["overview"]["total_cost"]["input"] += question_input_cost
        data["overview"]["total_cost"]["output"] += question_output_cost
        data["overview"]["total_cost"]["total"] += question_total_cost
        data["last_updated"] = timestamp
        
        # معالجة Models و Stages
        model_dict = {}
        stage_dict = {}
        
        # تحويل models من array إلى dict مؤقت للتحديث
        for model in data.get("models", []):
            model_dict[model["name"]] = model
        
        # تحويل stages من array إلى dict مؤقت للتحديث
        for stage in data.get("stages", []):
            stage_dict[stage["name"]] = stage
        
        # تحديث البيانات من all_stages
        for stage in all_stages:
            model_name = stage["model"]
            stage_name = stage["stage_name"]
            
            input_price = self._get_model_input_price(model_name)
            output_price = self._get_model_output_price(model_name)
            input_cost = (stage["input_tokens"] / 1_000_000) * input_price
            output_cost = (stage["output_tokens"] / 1_000_000) * output_price
            
            # تحديث Model
            if model_name not in model_dict:
                model_dict[model_name] = {
                    "name": model_name,
                    "tokens": {
                        "input": 0,
                        "output": 0,
                        "total": 0
                    },
                    "times_used": 0,
                    "cost": {
                        "input": 0.0,
                        "output": 0.0,
                        "total": 0.0
                    },
                    "pricing": {
                        "input_per_1m": input_price,
                        "output_per_1m": output_price
                    },
                    "percentage_of_total_cost": 0.0
                }
            
            model_dict[model_name]["tokens"]["input"] += stage["input_tokens"]
            model_dict[model_name]["tokens"]["output"] += stage["output_tokens"]
            model_dict[model_name]["tokens"]["total"] += stage["total_tokens"]
            model_dict[model_name]["times_used"] += 1
            model_dict[model_name]["cost"]["input"] += input_cost
            model_dict[model_name]["cost"]["output"] += output_cost
            model_dict[model_name]["cost"]["total"] += (input_cost + output_cost)
            
            # تحديث Stage
            if stage_name not in stage_dict:
                stage_dict[stage_name] = {
                    "name": stage_name,
                    "times_used": 0,
                    "tokens": {
                        "input": 0,
                        "output": 0,
                        "total": 0
                    },
                    "cost": {
                        "input": 0.0,
                        "output": 0.0,
                        "total": 0.0
                    },
                    "percentage_of_total_cost": 0.0
                }
            
            stage_dict[stage_name]["times_used"] += 1
            stage_dict[stage_name]["tokens"]["input"] += stage["input_tokens"]
            stage_dict[stage_name]["tokens"]["output"] += stage["output_tokens"]
            stage_dict[stage_name]["tokens"]["total"] += stage["total_tokens"]
            stage_dict[stage_name]["cost"]["input"] += input_cost
            stage_dict[stage_name]["cost"]["output"] += output_cost
            stage_dict[stage_name]["cost"]["total"] += (input_cost + output_cost)
        
        # حساب النسب المئوية
        total_cost = data["overview"]["total_cost"]["total"]
        if total_cost > 0:
            for model in model_dict.values():
                model["percentage_of_total_cost"] = round((model["cost"]["total"] / total_cost) * 100, 1)
            
            for stage in stage_dict.values():
                stage["percentage_of_total_cost"] = round((stage["cost"]["total"] / total_cost) * 100, 1)
        
        # تحويل dict إلى arrays مرتبة
        data["models"] = sorted(model_dict.values(), key=lambda x: x["cost"]["total"], reverse=True)
        data["stages"] = sorted(stage_dict.values(), key=lambda x: x["cost"]["total"], reverse=True)
        
        # =============
        # إعداد تفاصيل كل stage وكل model لهذا السؤال
        # =============
        
        # تجميع stages حسب النوع
        stages_breakdown = {}
        for stage in all_stages:
            stage_name = stage["stage_name"]
            if stage_name not in stages_breakdown:
                stages_breakdown[stage_name] = {
                    "name": stage_name,
                    "model": stage["model"],
                    "tokens": {
                        "input": stage["input_tokens"],
                        "output": stage["output_tokens"],
                        "total": stage["total_tokens"]
                    },
                    "cost": {
                        "input": 0.0,
                        "output": 0.0,
                        "total": 0.0
                    },
                    "percentage_of_question": 0.0
                }
                
                input_price = self._get_model_input_price(stage["model"])
                output_price = self._get_model_output_price(stage["model"])
                input_cost = (stage["input_tokens"] / 1_000_000) * input_price
                output_cost = (stage["output_tokens"] / 1_000_000) * output_price
                
                stages_breakdown[stage_name]["cost"]["input"] = float(f"{input_cost:.8f}")
                stages_breakdown[stage_name]["cost"]["output"] = float(f"{output_cost:.8f}")
                stages_breakdown[stage_name]["cost"]["total"] = float(f"{(input_cost + output_cost):.8f}")
        
        # حساب النسب المئوية لكل stage في هذا السؤال
        question_cost = question_input_cost + question_output_cost
        for stage_info in stages_breakdown.values():
            if question_cost > 0:
                stage_info["percentage_of_question"] = float(
                    f"{(stage_info['cost']['total'] / question_cost * 100):.1f}"
                )
        
        # تحويل إلى list مرتب
        stages_list = sorted(
            stages_breakdown.values(),
            key=lambda x: x["cost"]["total"],
            reverse=True
        )
        
        # تجميع models المستخدمة في هذا السؤال
        models_breakdown = {}
        for stage in all_stages:
            model_name = stage["model"]
            if model_name not in models_breakdown:
                models_breakdown[model_name] = {
                    "name": model_name,
                    "times_used": 0,
                    "tokens": {
                        "input": 0,
                        "output": 0,
                        "total": 0
                    },
                    "cost": {
                        "input": 0.0,
                        "output": 0.0,
                        "total": 0.0
                    },
                    # "pricing": {
                    #     "input_per_1m": self._get_model_input_price(model_name),
                    #     "output_per_1m": self._get_model_output_price(model_name)
                    # },
                    "percentage_of_question": 0.0
                }
            
            models_breakdown[model_name]["times_used"] += 1
            models_breakdown[model_name]["tokens"]["input"] += stage["input_tokens"]
            models_breakdown[model_name]["tokens"]["output"] += stage["output_tokens"]
            models_breakdown[model_name]["tokens"]["total"] += stage["total_tokens"]
            
            input_price = self._get_model_input_price(model_name)
            output_price = self._get_model_output_price(model_name)
            input_cost = (stage["input_tokens"] / 1_000_000) * input_price
            output_cost = (stage["output_tokens"] / 1_000_000) * output_price
            
            models_breakdown[model_name]["cost"]["input"] += input_cost
            models_breakdown[model_name]["cost"]["output"] += output_cost
            models_breakdown[model_name]["cost"]["total"] += (input_cost + output_cost)
        
        # حساب النسب المئوية لكل model في هذا السؤال
        for model_info in models_breakdown.values():
            if question_cost > 0:
                model_info["percentage_of_question"] = float(
                    f"{(model_info['cost']['total'] / question_cost * 100):.1f}"
                )
            
            # تقريب التكاليف
            model_info["cost"]["input"] = float(f"{model_info['cost']['input']:.8f}")
            model_info["cost"]["output"] = float(f"{model_info['cost']['output']:.8f}")
            model_info["cost"]["total"] = float(f"{model_info['cost']['total']:.8f}")
        
        # تحويل إلى list مرتب
        models_list = sorted(
            models_breakdown.values(),
            key=lambda x: x["cost"]["total"],
            reverse=True
        )
        
        # إضافة المحادثة إلى التاريخ مع التفاصيل الكاملة
        conversation_number = len(data["conversation_history"]) + 1
        data["conversation_history"].append({
            "number": conversation_number,
            "timestamp": timestamp,
            "question": user_question,
            "tokens": {
                "input": question_input_tokens,
                "output": question_output_tokens,
                "total": question_total_tokens
            },
            "cost": {
                "input": float(f"{question_input_cost:.8f}"),
                "output": float(f"{question_output_cost:.8f}"),
                "total": float(f"{question_cost:.8f}")
            },
            "stages_breakdown": stages_list,
            "models_breakdown": models_list
        })
        
        # تقريب الأرقام للوضوح
        data["overview"]["total_cost"]["input"] = float(f"{data['overview']['total_cost']['input']:.8f}")
        data["overview"]["total_cost"]["output"] = float(f"{data['overview']['total_cost']['output']:.8f}")
        data["overview"]["total_cost"]["total"] = float(f"{data['overview']['total_cost']['total']:.8f}")
        
        for model in data["models"]:
            model["cost"]["input"] = float(f"{model['cost']['input']:.8f}")
            model["cost"]["output"] = float(f"{model['cost']['output']:.8f}")
            model["cost"]["total"] = float(f"{model['cost']['total']:.8f}")
        
        for stage in data["stages"]:
            stage["cost"]["input"] = float(f"{stage['cost']['input']:.8f}")
            stage["cost"]["output"] = float(f"{stage['cost']['output']:.8f}")
            stage["cost"]["total"] = float(f"{stage['cost']['total']:.8f}")
        
        # حفظ الملف
        self._save_json_file(costs_file, data)

    async def _generate_summary(self, user_question: str, chat_id: int, 
                               username: str, timestamp: str) -> Tuple[Summary, dict]:
        """توليد ملخص السؤال مع SQL query"""
        history_text = await self._get_cached_history(chat_id)
        
        input_data = {
            "schema_text": self.schema_text,
            "schema_examples": self.schema_examples_text,
            "history_text": history_text,
            "user_question": user_question,
            "format_instructions": self.summary_parser.get_format_instructions()
        }
        
        prompt_template = PromptTemplate(
            template=PROMPT_TEMPLATE,
            input_variables=["schema_text", "history_text", "user_question", "format_instructions"]
        )
        full_prompt = prompt_template.format(**input_data)
        
        input_tokens = await self._count_tokens(self.llm, full_prompt)
        
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(
            self.executor,
            lambda: self.summary_chain.invoke(input_data)
        )
        
        output_text = f"{summary.answer or ''}\n{summary.sql_query or ''}"
        output_tokens = await self._count_tokens(self.llm, output_text)
        
        stage_data = {
            "stage_num": 1,
            "stage_name": "Summary Generation",
            "model": "gemini-2.5-flash",
            "input_text": full_prompt,
            "output_text": output_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
        
        # حفظ في التخزين المؤقت
        self._add_stage_to_details(chat_id, username, user_question, timestamp, stage_data)
        
        token_stats = {
            "model": "gemini-2.5-flash",
            "stage_name": "Summary Generation",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
        
        print(f"\n{'='*60}")
        print(f"📊 Summary Generation Tokens:")
        print(f"   Model: gemini-2.5-flash")
        print(f"   Input: {input_tokens} tokens")
        print(f"   Output: {output_tokens} tokens")
        print(f"   Total: {input_tokens + output_tokens} tokens")
        print(f"{'='*60}\n")
        
        return summary, token_stats
    
    async def _process_sql_query(self, summary: Summary, user_question: str, 
                                 chat_id: int, username: str, timestamp: str) -> Tuple[str, dict]:
        """معالجة SQL query وإرجاع الإجابة"""
        if not summary.sql_query:
            return summary.answer or "لم يتم العثور على إجابة", {}
        
        sql_result = await self.sql_service.execute_async(summary.sql_query)
        
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
        
        input_tokens = await self._count_tokens(self.small_llm, prompt)
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            self.executor,
            lambda: self.small_llm.invoke(prompt)
        )
        
        output_tokens = await self._count_tokens(self.small_llm, response.content)
        
        stage_data = {
            "stage_num": 2,
            "stage_name": "SQL Response Generation",
            "model": "gemini-2.0-flash",
            "input_text": prompt,
            "output_text": response.content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
        
        # حفظ في التخزين المؤقت
        self._add_stage_to_details(chat_id, username, user_question, timestamp, stage_data)
        
        token_stats = {
            "model": "gemini-2.0-flash",
            "stage_name": "SQL Response Generation",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
        
        print(f"\n{'='*60}")
        print(f"📊 SQL Response Generation Tokens:")
        print(f"   Model: gemini-2.0-flash")
        print(f"   Input: {input_tokens} tokens")
        print(f"   Output: {output_tokens} tokens")
        print(f"   Total: {input_tokens + output_tokens} tokens")
        print(f"{'='*60}\n")
        
        return response.content, token_stats
    
    async def _generate_email(self, summary: Summary, user_question: str, 
                             chat_id: int, username: str, timestamp: str) -> Tuple[Mail, dict]:
        """توليد محتوى الإيميل"""
        tasks = []
        
        if summary.sql_query:
            tasks.append(self.sql_service.execute_async(summary.sql_query))
        else:
            tasks.append(asyncio.create_task(asyncio.sleep(0, result="")))
        
        tasks.append(self._get_cached_history(chat_id))
        
        results = await asyncio.gather(*tasks)
        sql_result = results[0]
        history_text = results[1]
        
        input_data = {
            "user_question": user_question,
            "history_text": history_text,
            "sql_result": sql_result or "",
            "format_instructions": self.mail_parser.get_format_instructions(),
            "template_instructions": TEMPLATE_INSTRUCTIONS
        }
        
        prompt_template = PromptTemplate(
            template=EMAIL_TEMPLATE,
            input_variables=["user_question", "sql_result", 
                           "format_instructions", "history_text", "template_instructions"]
        )
        full_prompt = prompt_template.format(**input_data)
        
        input_tokens = await self._count_tokens(self.llm, full_prompt)
        
        loop = asyncio.get_event_loop()
        mail = await loop.run_in_executor(
            self.executor,
            lambda: self.mail_chain.invoke(input_data)
        )
        
        output_text = f"Subject: {mail.subject}\nTo: {', '.join(mail.email)}\n\n{mail.body}"
        output_tokens = await self._count_tokens(self.llm, output_text)
        
        stage_data = {
            "stage_num": 3,
            "stage_name": "Email Generation",
            "model": "gemini-2.5-flash",
            "input_text": full_prompt,
            "output_text": output_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
        
        # حفظ في التخزين المؤقت
        self._add_stage_to_details(chat_id, username, user_question, timestamp, stage_data)
        
        token_stats = {
            "model": "gemini-2.5-flash",
            "stage_name": "Email Generation",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
        
        print(f"\n{'='*60}")
        print(f"📊 Email Generation Tokens:")
        print(f"   Model: gemini-2.5-flash")
        print(f"   Input: {input_tokens} tokens")
        print(f"   Output: {output_tokens} tokens")
        print(f"   Total: {input_tokens + output_tokens} tokens")
        print(f"{'='*60}\n")
        
        return mail, token_stats
    
    async def handle_question(
        self, 
        user_question: str, 
        username: str, 
        chat_id: int,
        user_id: int = None
    ) -> Tuple[str, Optional[str], Optional[str], int, Optional[Mail]]:
        """معالجة السؤال بشكل كامل"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # مسح التخزين المؤقت للمحادثة السابقة
        self._current_conversation_stages = []
        
        all_stages_for_costs = []
        
        # الخطوة 1: توليد الملخص
        summary, summary_tokens = await self._generate_summary(
            user_question, chat_id, username, timestamp
        )
        all_stages_for_costs.append(summary_tokens)
        
        answer = None
        sql_query = summary.sql_query
        sql_result = None
        mail = None
        
        # الخطوة 2: معالجة حسب النوع
        if summary.way and summary.way.lower() == "sqlquery":
            answer, sql_tokens = await self._process_sql_query(
                summary, user_question, chat_id, username, timestamp
            )
            if sql_tokens:
                all_stages_for_costs.append(sql_tokens)
            
            if sql_query:
                sql_result = await self.sql_service.get_last_result()
        
        elif summary.way and summary.way.lower() == "email":
            try:
                mail, email_tokens = await self._generate_email(
                    summary, user_question, chat_id, username, timestamp
                )
                all_stages_for_costs.append(email_tokens)
                
                answer = f"تم إنشاء معاينة الإيميل للمرسل إليهم: {', '.join(mail.email)}"
            except Exception as e:
                print(f"Error generating email: {e}")
                answer = "حدث خطأ أثناء إنشاء الإيميل. يرجى المحاولة مرة أخرى."
        
        else:
            answer = summary.answer or "تم الرد من تاريخ المحادثة."
        if answer is None:
            answer = "sorry, no answer"
        # حساب التكلفة الكلية لهذا السؤال
        question_total_tokens = sum(s["total_tokens"] for s in all_stages_for_costs)
        question_total_cost = 0.0
        
        for stage in all_stages_for_costs:
            input_price = self._get_model_input_price(stage["model"])
            output_price = self._get_model_output_price(stage["model"])
            input_cost = (stage["input_tokens"] / 1_000_000) * input_price
            output_cost = (stage["output_tokens"] / 1_000_000) * output_price
            question_total_cost += (input_cost + output_cost)
        
        # حفظ في ملف details
        self._save_conversation_to_details_file(chat_id, username, user_question, timestamp)
        
        # تحديث ملف التكاليف
        self._update_costs_file(
            chat_id, username, user_question, timestamp,
            all_stages_for_costs, question_total_tokens, question_total_cost
        )
        
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
        
        self._invalidate_cache(chat_id)
        memory_task = self.conversation_manager.get_memory_length(chat_id)
        
        await save_task
        history_len = await memory_task
        
        # طباعة الملخص النهائي
        print("\n" + "="*60)
        print("📊 FINAL SUMMARY FOR THIS QUESTION:")
        print(f"   Question: {user_question[:50]}...")
        print(f"   Total Tokens: {question_total_tokens}")
        print(f"   Total Cost: ${question_total_cost:.6f}")
        print(f"   Stages: {len(all_stages_for_costs)}")
        print("="*60 + "\n")
        
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
        self.executor.shutdown(wait=True)

# Singleton instance
_llm_service = None

def get_llm_service() -> TelegramLLMService:
    """الحصول على instance واحد من الخدمة"""
    global _llm_service
    if _llm_service is None:
        _llm_service = TelegramLLMService(max_workers=10)
    return _llm_service
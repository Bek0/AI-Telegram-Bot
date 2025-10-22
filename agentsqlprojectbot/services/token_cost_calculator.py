# services/token_cost_calculator.py
"""
نظام متكامل لحساب التكلفة والتوكنات مع دعم المؤسسات
الإصدار الخامس - مع جداول منفصلة للمؤسسات والمستخدمين الفرديين
"""

import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy import text
from db_connection import SessionLocal_2


class TokenCostCalculator:
    """حساب التكاليف والتوكنات مع دعم المؤسسات والمستخدمين الفرديين"""
    
    def __init__(self):
        pass
    
    def _get_session(self):
        """إنشاء جلسة جديدة لكل عملية"""
        return SessionLocal_2()
    
    #  أسعار النماذج 
    
    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """الحصول على سعر النموذج من قاعدة البيانات"""
        session = self._get_session()
        try:
            query = text("""
                SELECT input_price_per_1m, output_price_per_1m
                FROM ModelPricing
                WHERE model_name LIKE :model AND active = 1
            """)
            
            result = session.execute(
                query,
                {"model": f"%{model}%"}
            ).fetchone()
            
            if result:
                return {
                    "input": float(result[0]),
                    "output": float(result[1])
                }
            
            return {"input": 0.0, "output": 0.0}
        except Exception as e:
            print(f"❌ خطأ في الحصول على أسعار النموذج: {e}")
            return {"input": 0.0, "output": 0.0}
        finally:
            session.close()
    
    #  حساب التوكنات 
    
    async def count_tokens(self, model: Any, text_content: str, executor) -> int:
        """حساب عدد التوكنات للنص المعطى"""
        try:
            loop = asyncio.get_event_loop()
            token_count = await loop.run_in_executor(
                executor,
                lambda: model.get_num_tokens(text_content)
            )
            return token_count
        except Exception as e:
            print(f"❌ خطأ في حساب التوكنات: {e}")
            return 0
    
    #  حساب التكاليف 
    
    def calculate_stage_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Dict[str, float]:
        """حساب تكلفة مرحلة واحدة"""
        pricing = self.get_model_pricing(model)
        
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        return {
            "input": float(f"{input_cost:.8f}"),
            "output": float(f"{output_cost:.8f}"),
            "total": float(f"{total_cost:.8f}")
        }
    
    def create_stage_record(
        self,
        stage_number: int,
        stage_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Dict[str, Any]:
        """إنشاء سجل مرحلة واحدة"""
        total_tokens = input_tokens + output_tokens
        cost = self.calculate_stage_cost(model, input_tokens, output_tokens)
        
        return {
            "stage_number": stage_number,
            "stage_name": stage_name,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": cost
        }
    
    #  حفظ البيانات 
    
    def save_conversation(
        self,
        chat_id: int,
        user_id: Optional[int],
        username: str,
        user_question: str,
        org_id: Optional[str] = None,
        database_id: Optional[str] = None
    ) -> Optional[int]:
        """حفظ محادثة جديدة وإرجاع معرفها"""
        session = self._get_session()
        try:
            insert_query = text("""
                INSERT INTO Conversations 
                (chat_id, user_id, username, user_question, org_id, database_id, timestamp)
                VALUES (:chat_id, :user_id, :username, :user_question, :org_id, :database_id, GETDATE())
            """)
            
            session.execute(
                insert_query,
                {
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "username": username,
                    "user_question": user_question,
                    "org_id": org_id,
                    "database_id": database_id
                }
            )
            session.flush()
            
            # الحصول على آخر ID المُدرج
            get_id_query = text("""
                SELECT TOP 1 conversation_id 
                FROM Conversations 
                WHERE chat_id = :chat_id 
                ORDER BY conversation_id DESC
            """)
            
            result = session.execute(get_id_query, {"chat_id": chat_id}).scalar()
            session.commit()
            
            if result:
                print(f"✅ تم حفظ المحادثة: ID={result} | org_id={org_id}")
                return result
            
            return None
        except Exception as e:
            session.rollback()
            print(f"❌ خطأ في حفظ المحادثة: {e}")
            return None
        finally:
            session.close()
    
    def save_stage(
        self,
        conversation_id: int,
        chat_id: int,
        stage_number: int,
        stage_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        input_cost: float,
        output_cost: float,
        total_cost: float
    ) -> bool:
        """حفظ مرحلة من المراحل"""
        session = self._get_session()
        try:
            query = text("""
                INSERT INTO ConversationStages 
                (conversation_id, chat_id, stage_number, stage_name, model_name, 
                 input_tokens, output_tokens, total_tokens, input_cost, output_cost, total_cost)
                VALUES 
                (:conversation_id, :chat_id, :stage_number, :stage_name, :model_name, 
                 :input_tokens, :output_tokens, :total_tokens, :input_cost, :output_cost, :total_cost)
            """)
            
            session.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "chat_id": chat_id,
                    "stage_number": stage_number,
                    "stage_name": stage_name,
                    "model_name": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "input_cost": input_cost,
                    "output_cost": output_cost,
                    "total_cost": total_cost
                }
            )
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"❌ خطأ في حفظ المرحلة: {e}")
            return False
        finally:
            session.close()
    
    def save_conversation_summary(
        self,
        conversation_id: int,
        chat_id: int,
        total_stages: int,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        input_cost: float,
        output_cost: float,
        total_cost: float,
        stages: List[Dict[str, Any]]
    ) -> bool:
        """حفظ ملخص المحادثة"""
        session = self._get_session()
        try:
            most_expensive_stage = max(
                stages, 
                key=lambda x: x["total_tokens"]
            ) if stages else None
            
            stage_percentage = (
                (most_expensive_stage["total_tokens"] / total_tokens * 100)
                if most_expensive_stage and total_tokens > 0 else 0
            )
            
            query = text("""
                INSERT INTO ConversationSummary 
                (conversation_id, chat_id, total_stages, input_tokens, output_tokens, total_tokens,
                 input_cost, output_cost, total_cost, most_expensive_stage_name, 
                 most_expensive_stage_tokens, most_expensive_stage_percentage)
                VALUES 
                (:conversation_id, :chat_id, :total_stages, :input_tokens, :output_tokens, :total_tokens,
                 :input_cost, :output_cost, :total_cost, :stage_name, :stage_tokens, :stage_percentage)
            """)
            
            session.execute(
                query,
                {
                    "conversation_id": conversation_id,
                    "chat_id": chat_id,
                    "total_stages": total_stages,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "input_cost": input_cost,
                    "output_cost": output_cost,
                    "total_cost": total_cost,
                    "stage_name": most_expensive_stage["stage_name"] if most_expensive_stage else None,
                    "stage_tokens": most_expensive_stage["total_tokens"] if most_expensive_stage else None,
                    "stage_percentage": stage_percentage
                }
            )
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"❌ خطأ في حفظ ملخص المحادثة: {e}")
            return False
        finally:
            session.close()
    
    #  تحديث الإحصائيات 
    
    def update_model_usage(
        self,
        chat_id: int,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        input_cost: float,
        output_cost: float,
        total_cost: float,
        org_id: Optional[str] = None
    ) -> bool:
        """تحديث استخدام النموذج للمستخدم أو المؤسسة"""
        session = self._get_session()
        try:
            pricing = self.get_model_pricing(model)
            
            # إذا كان المستخدم من مؤسسة
            if org_id:
                query = text("""
                    MERGE INTO OrgModelUsage AS target
                    USING (SELECT :org_id as org_id, :model_name as model_name) AS source
                    ON target.org_id = source.org_id AND target.model_name = source.model_name
                    WHEN MATCHED THEN
                        UPDATE SET 
                            times_used = times_used + 1,
                            input_tokens = input_tokens + :input_tokens,
                            output_tokens = output_tokens + :output_tokens,
                            total_tokens = total_tokens + :total_tokens,
                            input_cost = input_cost + CAST(:input_cost AS DECIMAL(18,8)),
                            output_cost = output_cost + CAST(:output_cost AS DECIMAL(18,8)),
                            total_cost = total_cost + CAST(:total_cost AS DECIMAL(18,8)),
                            last_updated = GETDATE()
                    WHEN NOT MATCHED THEN
                        INSERT (org_id, model_name, times_used, input_tokens, output_tokens, total_tokens,
                               input_cost, output_cost, total_cost)
                        VALUES (:org_id, :model_name, 1, :input_tokens, :output_tokens, :total_tokens,
                               CAST(:input_cost AS DECIMAL(18,8)), CAST(:output_cost AS DECIMAL(18,8)), 
                               CAST(:total_cost AS DECIMAL(18,8)));
                """)
                
                session.execute(
                    query,
                    {
                        "org_id": org_id,
                        "model_name": model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "input_cost": input_cost,
                        "output_cost": output_cost,
                        "total_cost": total_cost
                    }
                )
            else:
                # المستخدم الفردي
                query = text("""
                    MERGE INTO ModelUsage AS target
                    USING (SELECT :chat_id as chat_id, :model_name as model_name) AS source
                    ON target.chat_id = source.chat_id AND target.model_name = source.model_name
                    WHEN MATCHED THEN
                        UPDATE SET 
                            times_used = times_used + 1,
                            input_tokens = input_tokens + :input_tokens,
                            output_tokens = output_tokens + :output_tokens,
                            total_tokens = total_tokens + :total_tokens,
                            input_cost = input_cost + CAST(:input_cost AS DECIMAL(18,8)),
                            output_cost = output_cost + CAST(:output_cost AS DECIMAL(18,8)),
                            total_cost = total_cost + CAST(:total_cost AS DECIMAL(18,8)),
                            last_updated = GETDATE()
                    WHEN NOT MATCHED THEN
                        INSERT (chat_id, model_name, times_used, input_tokens, output_tokens, total_tokens,
                               input_cost, output_cost, total_cost, input_price_per_1m, output_price_per_1m)
                        VALUES (:chat_id, :model_name, 1, :input_tokens, :output_tokens, :total_tokens,
                               CAST(:input_cost AS DECIMAL(18,8)), CAST(:output_cost AS DECIMAL(18,8)), 
                               CAST(:total_cost AS DECIMAL(18,8)), :input_price, :output_price);
                """)
                
                session.execute(
                    query,
                    {
                        "chat_id": chat_id,
                        "model_name": model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "input_cost": input_cost,
                        "output_cost": output_cost,
                        "total_cost": total_cost,
                        "input_price": pricing["input"],
                        "output_price": pricing["output"]
                    }
                )
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"❌ خطأ في تحديث استخدام النموذج: {e}")
            return False
        finally:
            session.close()
    
    def update_stage_usage(
        self,
        chat_id: int,
        stage_name: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
        input_cost: float,
        output_cost: float,
        total_cost: float,
        org_id: Optional[str] = None
    ) -> bool:
        """تحديث استخدام المرحلة للمستخدم أو المؤسسة"""
        session = self._get_session()
        try:
            if org_id:
                query = text("""
                    MERGE INTO OrgStagesUsage AS target
                    USING (SELECT :org_id as org_id, :stage_name as stage_name) AS source
                    ON target.org_id = source.org_id AND target.stage_name = source.stage_name
                    WHEN MATCHED THEN
                        UPDATE SET 
                            times_used = times_used + 1,
                            input_tokens = input_tokens + :input_tokens,
                            output_tokens = output_tokens + :output_tokens,
                            total_tokens = total_tokens + :total_tokens,
                            input_cost = input_cost + CAST(:input_cost AS DECIMAL(18,8)),
                            output_cost = output_cost + CAST(:output_cost AS DECIMAL(18,8)),
                            total_cost = total_cost + CAST(:total_cost AS DECIMAL(18,8)),
                            last_updated = GETDATE()
                    WHEN NOT MATCHED THEN
                        INSERT (org_id, stage_name, times_used, input_tokens, output_tokens, total_tokens,
                               input_cost, output_cost, total_cost)
                        VALUES (:org_id, :stage_name, 1, :input_tokens, :output_tokens, :total_tokens,
                               CAST(:input_cost AS DECIMAL(18,8)), CAST(:output_cost AS DECIMAL(18,8)), 
                               CAST(:total_cost AS DECIMAL(18,8)));
                """)
                
                session.execute(
                    query,
                    {
                        "org_id": org_id,
                        "stage_name": stage_name,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "input_cost": input_cost,
                        "output_cost": output_cost,
                        "total_cost": total_cost
                    }
                )
            else:
                query = text("""
                    MERGE INTO StagesUsage AS target
                    USING (SELECT :chat_id as chat_id, :stage_name as stage_name) AS source
                    ON target.chat_id = source.chat_id AND target.stage_name = source.stage_name
                    WHEN MATCHED THEN
                        UPDATE SET 
                            times_used = times_used + 1,
                            input_tokens = input_tokens + :input_tokens,
                            output_tokens = output_tokens + :output_tokens,
                            total_tokens = total_tokens + :total_tokens,
                            input_cost = input_cost + CAST(:input_cost AS DECIMAL(18,8)),
                            output_cost = output_cost + CAST(:output_cost AS DECIMAL(18,8)),
                            total_cost = total_cost + CAST(:total_cost AS DECIMAL(18,8)),
                            last_updated = GETDATE()
                    WHEN NOT MATCHED THEN
                        INSERT (chat_id, stage_name, times_used, input_tokens, output_tokens, total_tokens,
                               input_cost, output_cost, total_cost)
                        VALUES (:chat_id, :stage_name, 1, :input_tokens, :output_tokens, :total_tokens,
                               CAST(:input_cost AS DECIMAL(18,8)), CAST(:output_cost AS DECIMAL(18,8)), 
                               CAST(:total_cost AS DECIMAL(18,8)));
                """)
                
                session.execute(
                    query,
                    {
                        "chat_id": chat_id,
                        "stage_name": stage_name,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": total_tokens,
                        "input_cost": input_cost,
                        "output_cost": output_cost,
                        "total_cost": total_cost
                    }
                )
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"❌ خطأ في تحديث استخدام المرحلة: {e}")
            return False
        finally:
            session.close()

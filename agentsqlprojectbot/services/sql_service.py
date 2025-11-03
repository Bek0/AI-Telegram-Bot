# # services/sql_service.py
# import asyncio
# from typing import Any, Optional
# from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool


# class SQLService:
#     """خدمة SQL محسّنة - async بالكامل"""
    
#     def __init__(self, db=None):
        
#         self.db = db
#         self.sql_tool = QuerySQLDatabaseTool(db=db)
#         self._last_result: Optional[Any] = None
#         self._lock = asyncio.Lock()
    
#     async def execute_async(self, query: str) -> Any:
#         """تنفيذ SQL query بشكل async"""
#         async with self._lock:
#             try:
#                 # تنفيذ في executor لأن sql_tool.invoke هي blocking
#                 loop = asyncio.get_event_loop()
#                 result = await loop.run_in_executor(
#                     None,
#                     lambda: self.sql_tool.invoke(query)
#                 )
#                 self._last_result = result
#                 return result
#             except Exception as e:
#                 error_msg = f"SQL Error: {str(e)}"
#                 self._last_result = error_msg
#                 return error_msg
    
#     async def get_last_result(self) -> Optional[Any]:
#         """الحصول على آخر نتيجة"""
#         async with self._lock:
#             return self._last_result
    
#     def execute_sync(self, query: str) -> Any:
#         """تنفيذ SQL بشكل متزامن (للتوافق مع الكود القديم)"""
#         try:
#             result = self.sql_tool.invoke(query)
#             return result
#         except Exception as e:
#             return f"SQL Error: {str(e)}"


# services/sql_service.py
"""
SQL Service مع Validation أمني
"""
import asyncio
import logging
from typing import Any, Optional
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool

# ✅ Import الـ Validator
from utils.sql_validator import SQLValidator

logger = logging.getLogger(__name__)


class SQLService:
    """خدمة SQL محسّنة - async مع أمان"""
    
    def __init__(self, db=None):
        self.db = db
        self.sql_tool = QuerySQLDatabaseTool(db=db) if db else None
        self._last_result: Optional[Any] = None
        self._lock = asyncio.Lock()
        
        # ✅ Validator instance
        self.validator = SQLValidator()
    
    async def execute_async(self, query: str) -> Any:
        """
        تنفيذ SQL query بشكل async مع Validation
        """
        # ✅ Validation قبل التنفيذ
        is_valid, error_msg = self.validator.validate(query)
        
        if not is_valid:
            error_response = f"🚫 Query rejected: {error_msg}"
            logger.error(f"SQL Validation failed: {error_msg}\nQuery: {query}")
            self._last_result = error_response
            return error_response
        
        # ✅ تنفيذ آمن
        async with self._lock:
            try:
                if not self.sql_tool:
                    return "Database not configured"
                
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.sql_tool.invoke(query)
                )
                
                self._last_result = result
                logger.info(f"✅ SQL executed successfully: {query[:100]}")
                return result
                
            except Exception as e:
                error_msg = f"SQL Execution Error: {str(e)}"
                logger.error(f"{error_msg}\nQuery: {query}")
                self._last_result = error_msg
                return error_msg
    
    async def get_last_result(self) -> Optional[Any]:
        """الحصول على آخر نتيجة"""
        async with self._lock:
            return self._last_result
    
    def execute_sync(self, query: str) -> Any:
        """
        تنفيذ SQL بشكل متزامن (مع Validation)
        """
        # ✅ Validation
        is_valid, error_msg = self.validator.validate(query)
        if not is_valid:
            logger.error(f"SQL Validation failed (sync): {error_msg}")
            return f"🚫 Query rejected: {error_msg}"
        
        try:
            result = self.sql_tool.invoke(query)
            return result
        except Exception as e:
            return f"SQL Error: {str(e)}"
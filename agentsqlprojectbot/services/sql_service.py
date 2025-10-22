# services/sql_service.py
import asyncio
from typing import Any, Optional
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool


class SQLService:
    """خدمة SQL محسّنة - async بالكامل"""
    
    def __init__(self, db=None):
        
        self.db = db
        self.sql_tool = QuerySQLDatabaseTool(db=db)
        self._last_result: Optional[Any] = None
        self._lock = asyncio.Lock()
    
    async def execute_async(self, query: str) -> Any:
        """تنفيذ SQL query بشكل async"""
        async with self._lock:
            try:
                # تنفيذ في executor لأن sql_tool.invoke هي blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.sql_tool.invoke(query)
                )
                self._last_result = result
                return result
            except Exception as e:
                error_msg = f"SQL Error: {str(e)}"
                self._last_result = error_msg
                return error_msg
    
    async def get_last_result(self) -> Optional[Any]:
        """الحصول على آخر نتيجة"""
        async with self._lock:
            return self._last_result
    
    def execute_sync(self, query: str) -> Any:
        """تنفيذ SQL بشكل متزامن (للتوافق مع الكود القديم)"""
        try:
            result = self.sql_tool.invoke(query)
            return result
        except Exception as e:
            return f"SQL Error: {str(e)}"

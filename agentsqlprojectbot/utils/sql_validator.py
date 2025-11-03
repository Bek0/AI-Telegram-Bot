# utils/sql_validator.py
"""
SQL Query Validator - منع SQL Injection
"""
import re
from typing import Tuple
import sqlparse
from sqlparse.sql import Statement, Token
from sqlparse.tokens import Keyword, DML

class SQLValidator:
    """
    Validator لفحص SQL queries قبل التنفيذ
    يسمح فقط بـ: SELECT, INSERT, UPDATE
    """
    
    ALLOWED_STATEMENTS = {'SELECT', 'INSERT', 'UPDATE'}
    FORBIDDEN_KEYWORDS = {
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 
        'GRANT', 'REVOKE', 'EXECUTE', 'EXEC', 'XP_',
        'SP_', 'SHUTDOWN', 'BACKUP', 'RESTORE'
    }
    
    # Dangerous patterns
    DANGEROUS_PATTERNS = [
        r';\s*(DROP|DELETE|TRUNCATE|ALTER|CREATE)',  # Multiple statements
        r'--',  # SQL comments
        r'/\*.*?\*/',  # Block comments
        r'xp_cmdshell',  # Command execution
        r'OPENROWSET',  # External data access
        r'OPENDATASOURCE',
    ]
    
    @classmethod
    def validate(cls, query: str) -> Tuple[bool, str]:
        """
        فحص SQL query
        
        Returns:
            (is_valid, error_message)
        """
        if not query or not query.strip():
            return False, "Empty query"
        
        query = query.strip()
        
        # 1. فحص الأنماط الخطرة
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return False, f"Dangerous pattern detected: {pattern}"
        
        # 2. Parse باستخدام sqlparse
        try:
            parsed = sqlparse.parse(query)
        except Exception as e:
            return False, f"SQL parsing error: {str(e)}"
        
        if not parsed:
            return False, "Could not parse query"
        
        # 3. فحص عدد الاستعلامات (يجب أن يكون 1 فقط)
        if len(parsed) > 1:
            return False, "Multiple statements not allowed"
        
        statement: Statement = parsed[0]
        
        # 4. فحص نوع الاستعلام
        first_token = statement.token_first(skip_ws=True, skip_cm=True)
        if not first_token:
            return False, "Invalid statement"
        
        statement_type = first_token.ttype
        statement_value = first_token.value.upper()
        
        # فحص إذا كان من الأنواع المسموحة
        if statement_value not in cls.ALLOWED_STATEMENTS:
            return False, f"Statement type '{statement_value}' not allowed"
        
        # 5. فحص الكلمات المحظورة في باقي الاستعلام
        tokens_str = str(statement).upper()
        for forbidden in cls.FORBIDDEN_KEYWORDS:
            if forbidden in tokens_str:
                return False, f"Forbidden keyword detected: {forbidden}"
        
        # 6. فحص خاص لـ SELECT: منع INTO, OUTFILE
        if statement_value == 'SELECT':
            if re.search(r'\bINTO\s+(OUTFILE|DUMPFILE)', tokens_str, re.IGNORECASE):
                return False, "SELECT INTO OUTFILE not allowed"
        
        return True, ""
    
    @classmethod
    def sanitize_table_name(cls, table_name: str) -> Tuple[bool, str]:
        """
        فحص اسم الجدول
        """
        # يجب أن يحتوي فقط على: حروف, أرقام, underscore
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            return False, "Invalid table name format"
        
        if len(table_name) > 128:
            return False, "Table name too long"
        
        return True, ""


# ✅ Unit Tests
if __name__ == "__main__":
    # Test cases
    tests = [
        ("SELECT * FROM Users", True),
        ("SELECT id, name FROM Products WHERE price > 100", True),
        ("INSERT INTO Orders (user_id, total) VALUES (1, 99.99)", True),
        ("UPDATE Users SET status = 'active' WHERE id = 5", True),
        
        # Forbidden
        ("DROP TABLE Users", False),
        ("DELETE FROM Users", False),
        ("SELECT * FROM Users; DROP TABLE Products", False),
        ("SELECT * FROM Users -- comment", False),
        ("EXEC xp_cmdshell 'dir'", False),
        ("SELECT * INTO OUTFILE '/tmp/data.txt' FROM Users", False),
    ]
    
    print("🧪 Running SQL Validator Tests...\n")
    passed = 0
    for query, expected_valid in tests:
        is_valid, error = SQLValidator.validate(query)
        status = "✅" if (is_valid == expected_valid) else "❌"
        passed += (is_valid == expected_valid)
        print(f"{status} {query[:50]}")
        if not is_valid:
            print(f"   Error: {error}")
    
    print(f"\n📊 Passed: {passed}/{len(tests)}")
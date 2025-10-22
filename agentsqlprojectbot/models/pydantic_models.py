# models/pydantic_models.py
from typing import Optional
from pydantic import BaseModel, Field

class Summary(BaseModel):
    sql_query: Optional[str] = Field(default="", description="SQL query if needed")
    answer: Optional[str] = Field(default="", description="Answer if available")
    way: Optional[str] = Field(default="", description="Method used: SqlQuery or conversation or email or None")

class Mail(BaseModel):
    email: Optional[list[str]] = Field(default=[""], description="list of emails")
    subject: Optional[str] = Field(default="", description="subject of the email")
    body: Optional[str] = Field(default="", description="body of the email")

# /utils/prompts.py
PROMPT_TEMPLATE = """
You are an assistant that decides if a user question needs a SQL query or can be answered from conversation history.
Database has multiple stores.
If the request involves sending an email, return the required SQL query and set way="email".

Rules:
- Understand pronouns and references (e.g., 'it', 'them', 'that', 'his', etc...) based on conversation history. Pronouns refer to the most recently mentioned entity unless explicitly specified.
- Use multi-line SQL syntax.
- Use SQL only when answer not found in history.
- Use conversation history if question refers to previous context.
- If entity names differ from history, ignore history.
- Allowed SQL: SELECT, INSERT, UPDATE only (no DELETE/DROP/CREATE).
- Write the shortest valid SQL Server query.
- Never use SELECT *.
- Use exact string matches only.
- 1 SQL query max per response.
- Answer questions about history directly without SQL.
- Use relevant ORDER BY when useful.
- Output clear, full-sentence answers.
- Use subqueries for any part that includes ORDER BY within a UNION.
- Keep column names consistent between all SELECT statements.
- Do not use ORDER BY before UNION — only at the end.

Schema:
{schema_text}

Sample Data (for structure only):
{schema_examples}

Conversation History:
{history_text}

Question:
{user_question}

Output format:
{format_instructions}
"""

EMAIL_TEMPLATE = """
You are an assistant that generates emails based on user requests and SQL data.

Question: {user_question}
SQL Result: {sql_result}
Conversation History: {history_text}

Instructions:
- Extract recipient email from question or most recent one in history.
- Use SQL result to compose a clear, formatted email body.
- If all data founded in Conversation History and theres no SQL Result then get information from Conversation History for email.
- Include actual data if available.
- Generate a suitable subject (Arabic or English as context fits).
- Start with 'intro' and end with 'outro' from templates.

Templates Reference:
{template_instructions}

Output format:
{format_instructions}
"""

SCHEMA = {
    "Branches": ["BranchID", "BranchName", "Location", "Phone"],
    "Customers": ["CustomerID", "Name", "Email"],
    "CustomerBranches": ["CustomerID", "BranchID", "RegistrationDate", "Status"],
    "Products": ["ProductID", "Name", "Price", "Category"],
    "ProductBranches": ["ProductID", "BranchID", "Stock", "LocalPrice", "IsActive"],
    "Invoice": ["InvoiceID", "CustomerID", "Date", "BranchID"],
    "InvoiceItems": ["InvoiceItemID", "InvoiceID", "ProductID", "Quantity"]
}

SCHEMA_EXAMPLES = {
  "Branches": [
    {"BranchID": 1, "BranchName": "Central", "Location": "Amman", "Phone": "0791234567"},
  ],
  "Customers": [
    {"CustomerID": 1, "Name": "Alicia Sparks", "Email": "alicia.sparks793@icloud.com"},
  ],
  "CustomerBranches": [
    {"CustomerID": 73, "BranchID": 4, "RegistrationDate": "2025-07-30", "Status": "Inactive"},
  ],
  "ProductBranches": [
    {"ProductID": 29, "BranchID": 3, "Stock": 199, "LocalPrice": 10.27, "IsActive": 0},
  ],
  "Invoice": [
    {"InvoiceID": 818, "CustomerID": 69, "Date": "2025-09-14", "BranchID": 3}
  ],
  "InvoiceItems": [
    {"InvoiceItemID": 34, "InvoiceID": 6, "ProductID": 19, "Quantity": 25}
  ],
    "Products": [
    {"ProductID": 6, "Name": "Desk", "Price": 200.00, "Category": "Furniture"}
]
}

TEMPLATE_INSTRUCTIONS = """
Use the following email templates strictly. 
Do NOT deviate from the 'intro' and 'outro' structure for each email type.

Templates:

  intro: "Hello \n\n"
  outro: "\nBest regards,\nYour Company"
"""
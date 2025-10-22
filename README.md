# Professional README: Telegram Bot Intelligence System

## 1. Project Overview

### What Is This System?

This is an enterprise-grade Telegram bot integrated with an AI-powered conversational interface and multi-tenant dashboard. The system enables users to query databases using natural language, automate email generation, manage organizational memberships, and track AI usage costs across multiple database connections.

### Who It's For

- **Individual Users**: People who want to ask questions about databases without writing SQL
- **Organizations**: Companies needing collaborative data access with role-based permissions
- **Enterprise Teams**: Multi-user environments requiring usage tracking, cost allocation, and audit trails

### The Business Problem It Solves

1. **SQL Accessibility**: Makes database querying accessible to non-technical users through conversational AI
2. **Team Collaboration**: Enables secure data sharing within organizations with granular permission controls
3. **Cost Transparency**: Tracks AI token usage and associated costs at both individual and organizational levels
4. **Email Automation**: Generates and sends formatted emails based on database queries automatically
5. **Audit & Compliance**: Maintains complete logs of all interactions, queries, and data access for compliance purposes

---

## 2. Project Structure

```
project-root/
├── main_telegram.py              # Bot initialization, validation, and lifecycle management
├── db_connection.py              # SQL Server database connection configuration
├── connection.py                 # Alternative database connection handler
│
├── services/
│   ├── telegram_service.py       # Main Telegram bot implementation with command handlers
│   ├── telegram_llm_service.py   # AI/LLM integration for question processing
│   ├── telegram_auth.py          # User authentication and profile management
│   ├── telegram_logging.py       # Activity logging and conversation history
│   ├── database_manager.py       # Multi-database connection management
│   ├── organization_manager.py   # Organization/team management with invitations
│   ├── send_email.py             # Email service integration
│   ├── sql_service.py            # SQL execution wrapper
│   ├── token_cost_calculator.py  # Token counting and cost tracking
│
├── models/
│   ├── pydantic_models.py        # Data validation schemas (Summary, Mail)
│
├── memory/
│   ├── telegram_conversation.py  # Conversation history with sliding window cache
│
├── utils/
│   ├── prompts.py                # LLM prompt templates and schema definitions
│
├── logs/
│   ├── bot.log                   # Main application logs
│   ├── conversations/            # Individual chat conversation files
│   ├── telegram_activity.log     # Global activity log
│
└── requirements.txt              # Python dependencies
```

### Key Files Explained

| File | Purpose |
|------|---------|
| `main_telegram.py` | Entry point; validates environment, initializes services, sets up signal handlers |
| `telegram_service.py` | Handles all Telegram commands (/start, /help, /createorg, /adddb, etc.) and callback queries |
| `telegram_llm_service.py` | Processes questions through LLM, executes SQL, generates emails, tracks token costs |
| `database_manager.py` | Manages personal and organizational database connections with access control |
| `organization_manager.py` | Handles organization creation, member management, invitation system, role-based access |
| `telegram_auth.py` | User registration, profile management, role assignment (admin, org_owner, org_member) |
| `telegram_logging.py` | Logs all user actions, maintains conversation history, provides statistics |
| `telegram_conversation.py` | In-memory conversation cache with sliding window (last 5 conversations per user) |
| `token_cost_calculator.py` | Counts tokens, calculates costs, stores usage statistics per user/org/stage/model |
| `send_email.py` | Async SMTP email service with Gmail integration |
| `sql_service.py` | Executes SQL queries with error handling and result caching |

---

## 3. User Flows

### Flow 1: Individual User Setup

```
User starts bot (/start)
    ↓
Bot registers user in system
    ↓
User adds personal database (/adddb <name> <connection_string>)
    ↓
Bot validates connection
    ↓
User selects database as active (/selectdb)
    ↓
User ready to ask questions
```

### Flow 2: Organization Creation & Member Invitation

```
User creates organization (/createorg <name>)
    ↓
Bot creates organization, assigns user as owner
    ↓
Bot generates dashboard credentials for owner
    ↓
Owner adds organization database (/adddb <name> <connection_string>)
    ↓
Owner creates invitation code (/invite [uses] [hours])
    ↓
Owner shares invitation link with team members
    ↓
Team member joins via /join <code>
    ↓
Member gets dashboard credentials
    ↓
All members can query organization databases (/selectdb, ask questions)
```

### Flow 3: Question Processing & SQL Execution

```
User asks question in chat
    ↓
Rate limiter checks usage (1 req/sec, burst of 3)
    ↓
LLM Stage 1: Analyze question → Generate SQL query (gemini-2.5-flash)
    ↓
LLM evaluates if SQL needed or conversation-based answer
    ↓
If SQL: Execute query on selected database
    ↓
LLM Stage 2: Generate response from SQL results (gemini-2.0-flash)
    ↓
If email needed: LLM Stage 3 generates email (gemini-2.5-flash)
    ↓
Bot returns answer + optional email generation buttons
    ↓
Token usage, cost, and conversation saved to database
    ↓
User can preview and send email, or continue conversation
```

### Flow 4: Email Generation & Sending

```
LLM detects email request in question
    ↓
LLM Stage 3: Generates email subject, body, and recipient list
    ↓
Bot displays "Preview Email" and "Send Email" buttons
    ↓
User clicks preview or send
    ↓
If preview: Shows formatted email
    ↓
If send: Email sent via SMTP (Gmail) to recipients
    ↓
Action logged in activity log
```

### Flow 5: Cost Tracking & Analytics

```
Each LLM call counts tokens and calculates cost
    ↓
Cost breakdown stored per:
    - Stage (Summary Generation, SQL Response, Email Generation)
    - Model used (gemini-2.5-flash, gemini-2.0-flash)
    - User/Organization
    ↓
Data persisted in costs database (SessionLocal_2)
    ↓
Users can view personal stats (/stats, /myinfo)
    ↓
Organization owners can view org stats (/orginfo)
```

---

## 4. Detailed Functional Report

### 4.1 Core Commands

#### Admin/Owner Commands

| Command | Usage | Function |
|---------|-------|----------|
| `/createorg` | `/createorg <name>` | Creates new organization, assigns user as owner, generates dashboard credentials |
| `/adddb` | `/adddb <name> <connection_string>` | Adds database (personal if user is standalone, organization if user owns org) |
| `/invite` | `/invite [max_uses] [hours_valid]` | Creates time-limited invitation code for team members |
| `/org` | `/org` | Shows organization management menu |
| `/orginfo` | `/orginfo` | Displays org statistics, members, databases |

#### Member Commands

| Command | Usage | Function |
|---------|-------|----------|
| `/join` | `/join <invitation_code>` | Joins organization, receives dashboard credentials |
| `/selectdb` | `/selectdb` | Interactive menu to select active database |
| `/myinfo` | `/myinfo` | Shows user profile, role, organization membership, current database |

#### General Commands

| Command | Usage | Function |
|---------|-------|----------|
| `/start` | `/start` | Initializes user, explains bot purpose |
| `/help` | `/help` | Shows comprehensive command guide with examples |
| `/clear` | `/clear` | Clears conversation history for current chat |
| `/history` | `/history` | Shows last 10 questions asked |
| `/stats` | `/stats` | Displays personal usage statistics |

### 4.2 Question Processing Pipeline

#### Stage 1: Summary Generation (Gemini-2.5-Flash)

**Input**: User question + conversation history + database schema  
**Output**: `Summary` object containing:
- `sql_query`: Generated SQL if database query needed
- `answer`: Direct answer if available from history
- `way`: Method used (SqlQuery, email, conversation, or None)

**Logic**:
```
IF question refers to previous context:
    USE conversation history
ELSE IF question requires data:
    GENERATE SQL query
ELSE IF request involves email:
    SET way = "email"
ELSE:
    Provide conversational answer
```

#### Stage 2: SQL Execution & Response (Gemini-2.0-Flash)

**Input**: SQL query + execution results  
**Output**: Natural language response formatted for Telegram

**Process**:
- Executes SQL query on user's selected database
- Passes results to LLM for natural language conversion
- Validates that results only include data from the query (no fabrication)
- Returns formatted answer suitable for chat

#### Stage 3: Email Generation (Gemini-2.5-Flash)

**Input**: User question + SQL results + email templates  
**Output**: `Mail` object containing:
- `email`: List of recipient addresses
- `subject`: Email subject line
- `body`: Formatted email body

**Process**:
- Extracts recipient emails from user request or conversation history
- Generates professional email using template
- Provides preview before sending

### 4.3 Database Connection Management

**Architecture**: Multi-database support with per-user access control

```
Personal Databases:
  - Owner: Individual user (user_id)
  - Access: Only that user
  - Management: /adddb, /selectdb

Organization Databases:
  - Owner: Organization (org_id)
  - Access: All organization members
  - Management: Owner adds via /adddb
  - Members select via /selectdb
```

**Connection Verification**:
- Before executing queries, bot verifies user has access
- Prevents unauthorized cross-user or cross-org database access
- Automatically disconnects invalid connections

### 4.4 User Management & Authentication

**User Roles**:
```
ADMIN (System)
  └─ Can manage system-wide settings

ORG_OWNER (Organization Manager)
  ├─ Create/manage organization
  ├─ Add databases
  ├─ Create invitations
  ├─ Remove members
  └─ View org statistics

ORG_MEMBER (Team Member)
  ├─ Access org databases
  ├─ Ask questions
  ├─ View org info
  └─ Cannot modify org

USER (Standalone)
  ├─ Add personal databases
  ├─ Ask questions
  └─ Cannot create org (unless no existing membership)
```

**Dashboard Credentials**:
- Generated automatically when org is created or user joins
- Stored hashed in database
- Format: `username` + auto-generated `password`
- Used for separate dashboard web interface (not included in this code)

### 4.5 Conversation Memory System

**Architecture**: Sliding window cache with smart loading

```
Sliding Window:
  - Stores last 5 conversations (10 messages) in memory
  - Older conversations kept in file for audit/analytics
  - Reduces token usage by only considering recent context

Cache Strategy:
  - In-memory: Last 5 exchanges (active conversation)
  - File: All conversations (up to 1000 per chat)
  - Cache timeout: 5 minutes (auto-refresh on new message)
```

**Benefits**:
- Prevents token bloat (unlimited history increases costs)
- Maintains context for coherent conversations
- Preserves full audit trail in files
- Auto-cleaning prevents memory leaks

### 4.6 Rate Limiting & Concurrency Control

**Rate Limiter** (Token Bucket Algorithm):
```
Per-user settings:
  - 1 request per second
  - Burst capacity: 3 requests
  
Example:
  - User sends 3 questions rapidly: ✓ All accepted (uses burst)
  - User sends 4th question immediately: ✗ Wait ~0.5 seconds
  - After 1 second: Bucket refilled, user can send again
```

**Concurrency Control**:
```
Per-user limit: 1 active request
  - User sends question A
  - Before answer arrives, user sends question B
  - Question B gets: "Waiting for previous answer..."
  
Prevents:
  - Queue explosion on slow databases
  - Accidental double-processing
  - Token cost explosion
```

### 4.7 Cost Tracking & Token Accounting

**What's Tracked**:

Per Conversation:
- Total tokens consumed (input + output)
- Cost breakdown by stage
- Model used for each stage
- SQL query executed (if any)
- Timestamp and duration

Per User/Organization:
- Aggregate token usage
- Cost per model
- Cost per stage type
- Most expensive operations
- Usage trends

**Database Storage**:
```
costs database (SessionLocal_2):
  - ModelPricing: Price per 1M tokens for each model
  - Conversations: Individual conversation records
  - ConversationStages: Breakdown of each stage
  - ConversationSummary: Aggregated conversation metrics
  - ModelUsage: Per-user/org model usage stats
  - StagesUsage: Per-user/org stage usage stats
  - OrgModelUsage: Per-organization model tracking
  - OrgStagesUsage: Per-organization stage tracking
```

**Cost Calculation**:
```
For each stage:
  input_cost = (input_tokens / 1,000,000) * input_price_per_1m
  output_cost = (output_tokens / 1,000,000) * output_price_per_1m
  stage_cost = input_cost + output_cost

Total conversation cost = sum of all stage costs
```

### 4.8 Email Service

**Configuration**:
```
SMTP Server: Gmail (smtp.gmail.com:465, SSL)
Sender: BOT_EMAIL (from .env)
Auth: BOT_EMAIL_PASS (app-specific password)
```

**Email Generation Process**:
1. LLM analyzes question for email need
2. Extracts recipient email(s) from question or history
3. Generates subject and body using templates
4. Shows preview to user
5. User approves or edits
6. Sends asynchronously via thread executor
7. Logged in conversation history

**Email Templates**:
```
Structure:
  - intro: "Hello\n\n"
  - body: [LLM-generated content with SQL data]
  - outro: "\nBest regards,\nYour Company"
```

### 4.9 Logging & Audit Trail

**Log Files**:
```
logs/
  ├── bot.log                    # Application startup/errors
  ├── telegram_activity.log      # All user actions
  ├── chat_<ID>_activity.log     # Per-chat activity
  └── conversations/
      └── chat_<ID>_conversation.json  # Full conversation history
```

**Logged Events**:
- User registration/first seen
- Commands executed
- Questions asked
- SQL queries run
- Emails sent
- Database selected/changed
- Organization actions (create, join, member add/remove)
- Errors and exceptions

**Data Retention**:
- Activity logs: Ongoing (no auto-delete)
- Conversation files: Last 1000 conversations per chat
- In-memory cache: Last 5 conversations
- Database records: Indefinite (for cost tracking & compliance)

---

## 5. Business Perspective

### Value Proposition for Individuals

**Problem Solved**: Non-technical users cannot query databases without IT support

**Solution Delivered**:
- Ask questions in natural language instead of writing SQL
- Get instant answers without waiting for IT requests
- Complete independence in data exploration
- No learning curve for database syntax

**Measurable Benefits**:
- Faster decision-making (seconds vs. days)
- Reduced IT support burden
- Personal data autonomy
- Cost visibility (transparent token/API usage)

### Value Proposition for Organizations

**Problem Solved**: Teams need secure, collaborative access to databases with cost control and audit trails

**Solution Delivered**:

1. **Team Collaboration**
   - One-click team member invitations
   - Shared database access with role-based permissions
   - No duplicate database connections needed
   
2. **Security & Access Control**
   - Only members of organization can access org databases
   - Owner controls who joins (via invitation codes)
   - Owners can remove members instantly
   - Personal databases cannot be accessed by non-owners

3. **Cost Transparency & Control**
   - Detailed per-user and per-organization cost tracking
   - Breakdown by AI model and processing stage
   - Enables accurate cost allocation to teams/departments
   - Identifies inefficient query patterns

4. **Compliance & Audit**
   - Complete audit trail of all questions asked
   - Records which user queried which database when
   - Email generation tracking
   - Timestamp-accurate activity logs
   - Historical conversation records (up to 1000 per chat)

5. **Operational Efficiency**
   - No SQL training required for team members
   - Reduces IT workload for ad-hoc queries
   - Self-service analytics without data warehouse overhead
   - Email automation eliminates manual reporting

### Financial Impact

**Cost Optimization**:
- Reduced IT labor (no SQL query support needed)
- Prevents wasted AI API calls (rate limiting + caching)
- Identifies cost drivers (token usage by user/org/stage)
- Sliding window memory prevents unnecessary token consumption

**Revenue Enhancement** (if offered as service):
- Per-organization pricing model viable
- Usage-based billing possible (token tracking in place)
- Premium dashboard features (team analytics, custom reports)
- Integration services (custom database connections)

### Technical Advantages

**Scalability**:
- Async/await architecture handles concurrent users
- Multi-database support (not limited to one schema)
- Distributed conversation memory (file + in-memory)
- Rate limiting prevents server overload

**Reliability**:
- Connection pooling with health checks
- Graceful fallback if LLM unavailable
- Transaction safety (SQL commit/rollback)
- Signal handlers for clean shutdown

**Maintainability**:
- Modular service architecture (easy to extend)
- Comprehensive logging for debugging
- Configurable via environment variables
- Schema-agnostic (works with any database structure)

---

## 6. Implementation Notes

### Environment Variables Required

```
TELEGRAM_BOT_TOKEN=<your_telegram_bot_token>
BOT_EMAIL=<gmail_for_sending_emails>
BOT_EMAIL_PASS=<gmail_app_password>
ADMIN_TELEGRAM_IDS=<comma_separated_admin_ids>
DATABASE_URI=<optional_default_db_connection>
GOOGLE_APPLICATION_CREDENTIALS=<path_to_google_cloud_json>  # For Vertex AI
```

### Dependencies

- `python-telegram-bot`: Telegram API wrapper
- `langchain-community` + `langchain-google-genai`: LLM/SQL integration
- `sqlalchemy` + `pyodbc`: Database connection
- `aiofiles`: Async file I/O
- `python-dotenv`: Environment config

### Known Limitations

1. **One Organization Per User**: Users cannot be members of multiple organizations simultaneously (by design for billing simplicity)
2. **LLM Dependency**: System requires active internet connection to Google GenAI API
3. **Database Support**: Primarily tested with SQL Server; other databases require pyodbc driver compatibility
4. **Email Throttling**: No built-in throttling on email sending; depends on Gmail rate limits
5. **Conversation Context**: Only last 5 conversations retained in memory (older ones in file)

---

## Conclusion

This system bridges the gap between business users and databases by combining conversational AI, security, cost tracking, and collaboration features. It serves both individual power users seeking database autonomy and organizations requiring secure team data access with full audit trails and cost transparency.

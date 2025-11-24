# Enterprise Telegram Bot + Dashboard System
## System workflows

⚠️ IMPORTANT NOTICE: This project code is currently NOT FOR PUBLIC RELEASE.

### small workflow

```mermaid
graph TD
    Start["User question"] --> Input["Telegram Bot - Receive"]
    Input --> Analysis["Analysis"]

    Analysis --> Decide{Response type}
    
    %% Path 1
    Decide -->|History| DirectPath["Get last 5 messages"]
    DirectPath --> SendDirect["Send answer"]
    
    %% Path 2
    Decide -->|SQL| SQLPath["Build SQL query"]
    SQLPath --> GenerateSQL["Run query + draft reply"]
    GenerateSQL --> SendSQL["Send SQL reply"]
    
    %% Path 3
    Decide -->|Email| EmailPath["Generate email"]
    EmailPath --> SendEmail["Send via SMTP"]
    
    %% Logging
    SendDirect --> SaveConv["Save to database"]
    SendSQL --> SaveConv
    SendEmail --> SaveConv
    
    SaveConv --> LogCosts["Log token usage"]
    LogCosts --> Dashboard["Update dashboard"]
    Dashboard --> End["End"]

    %% GREY THEME
    style Start fill:#4F4F4F,stroke:#333,color:#fff
    style Input fill:#4F4F4F,stroke:#333,color:#fff

    style Analysis fill:#6E6E6E,stroke:#4A4A4A,color:#fff

    style Decide fill:#BDBDBD,stroke:#9E9E9E,color:#000
    style SaveConv fill:#BDBDBD,stroke:#9E9E9E,color:#000
    style LogCosts fill:#BDBDBD,stroke:#9E9E9E,color:#000
    
    style DirectPath fill:#828282,stroke:#5E5E5E,color:#fff
    style SQLPath fill:#828282,stroke:#5E5E5E,color:#fff
    style EmailPath fill:#828282,stroke:#5E5E5E,color:#fff
    style GenerateSQL fill:#828282,stroke:#5E5E5E,color:#fff

    style SendDirect fill:#A0A0A0,stroke:#7A7A7A,color:#fff
    style SendSQL fill:#A0A0A0,stroke:#7A7A7A,color:#fff
    style SendEmail fill:#A0A0A0,stroke:#7A7A7A,color:#fff
    
    style Dashboard fill:#4F4F4F,stroke:#333,color:#fff
    style End fill:#333333,stroke:#1F1F1F,color:#fff

```

## Complete System Overview
---

## 1. What Is This System?

This is an enterprise-grade ecosystem combining two integrated components:

- **Telegram Bot**: Mobile-first conversational interface for database querying and email automation
- **Web Dashboard**: Administrative interface for team management and cost analytics

Both interfaces share the same backend services, ensuring consistency and single source of truth.

### The Problem It Solves

Organizations need a way to:
- Allow non-technical users to query databases without SQL knowledge
- Collaborate securely on shared databases with role-based access
- Track AI usage costs transparently 
- Maintain complete audit trails for compliance
- Automate report generation and email distribution

---

## 2. System Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────┐
│              End Users (Dual Interface)          │
├──────────────────────┬──────────────────────────┤
│   Telegram Bot       │   Web Dashboard          │
│  (Mobile-First)      │   (Desktop)              │
│  • Natural language  │   • Team management      │
│  • Email generation  │   • Cost analytics       │
│  • Team invitations  │   • Database admin       │
└──────────────┬───────┴──────────────┬───────────┘
               │                      │
               └──────────┬───────────┘
                          │
        ┌─────────────────┴──────────────────┐
        │  Shared Backend Services           │
        ├────────────────────────────────────┤
        │ • LLM Processing (Google Gemini)   │
        │ • Database Connection Management   │
        │ • User Authentication              │
        │ • Organization Management          │
        │ • Email Service (Gmail SMTP)       │
        │ • Cost Tracking & Analytics        │
        │ • Activity Logging                 │
        └────────────────┬────────────────────┘
               ┌─────────┼─────────┐
         ┌─────▼──┐  ┌────▼──┐  ┌──▼─────┐
         │Manager │  │ Costs │  │Customer│
         │  DB    │  │  DB   │  │  DBs   │
         └────────┘  └───────┘  └────────┘
```

### Key Design Principles

1. **Shared Backend**: Both interfaces use identical business logic
2. **Multi-Tenant**: Complete organizational isolation
3. **Cost Transparent**: Every API call tracked and priced
4. **Audit First**: All actions logged with timestamps
5. **Stateless**: Horizontally scalable architecture

---

## 3. User Roles & Permissions

### Role Hierarchy

```
ADMIN (System)
  └─ System-wide settings

ORG_OWNER (Organization Manager)
  ├─ Create/manage organization
  ├─ Add/remove databases
  ├─ Create member invitations
  ├─ Manage team members
  └─ View org statistics

ORG_MEMBER (Team Member)
  ├─ Query org databases
  ├─ Ask questions
  ├─ View org info (read-only)
  └─ Send emails

USER (Standalone)
  ├─ Add personal databases
  ├─ Query own databases
  ├─ Create organization (becomes owner)
  └─ Join organization
```

### Access Control Matrix

| Action | Standalone | Org Owner | Org Member |
|--------|-----------|-----------|-----------|
| Create Org | ✓ | ✗ | ✗ |
| Add Org DB | ✗ | ✓ | ✗ |
| Add Personal DB | ✓ | ✗ | ✗ |
| Query Database | ✓ | ✓ | ✓ |
| Create Invitations | ✗ | ✓ | ✗ |
| Join Organization | ✓ | ✗ | ✗ |
| Remove Members | ✗ | ✓ | ✗ |
| View Costs | ✗ | ✓ | ✗ |

---

## 4. How It Works: User Flows

### Individual User Flow

```
User: /start
  ↓ (Bot registers user)
User: /adddb "Sales DB" "connection_string"
  ↓ (Bot validates connection)
User: /selectdb
  ↓ (User chooses database)
User: "What were Q4 sales?"
  ↓
Bot: 3-stage LLM processing
  1. Analyze intent → Generate SQL
  2. Execute SQL → Format results
  3. Generate email (if requested)
  ↓
Bot returns answer + cost breakdown
```

### Organization Setup Flow

```
Owner: /createorg "Acme Corp"
  ↓ (Bot creates org, owner gets dashboard credentials)
Owner: Logs into dashboard
  ↓ (Dashboard loads)
Owner: Dashboard → Databases → Add new
  ↓ (Owner adds organization database)
Owner: Dashboard → Invitations → Create
  ↓ (Generate invitation code)
Owner: Shares code with team
  ↓
Member: /join <code>
  ↓ (Member joins organization, gets dashboard credentials)
Member: /selectdb
  ↓ (Can now access shared organization databases)
Owner: Dashboard → Costs
  ↓ (Monitor member usage and costs)
```

---

## 5. Core Features

### Telegram Bot Features

**Commands**:
- `/start` - Initialize user
- `/help` - Show all commands
- `/createorg <name>` - Create organization
- `/adddb <name> <conn_str>` - Add database
- `/selectdb` - Choose active database
- `/invite [uses] [hours]` - Create member invitation
- `/join <code>` - Join organization
- `/orginfo` - View organization stats
- `/myinfo` - Show user profile
- `/stats` - Personal usage statistics
- `/history` - Last 10 questions
- `/clear` - Clear conversation history

**Capabilities**:
- Natural language database queries
- Automatic SQL generation from questions
- Multi-stage LLM processing
- Email generation and sending
- Conversation history with sliding window cache
- Rate limiting and concurrency control
- Cost tracking per query

### Web Dashboard Features

**Owner-Only Features**:
- Member management (add/remove/view)
- Database administration (add/remove/view)
- Invitation creation and management
- Cost analytics (5 different views):
  - Total cost overview
  - Cost by AI model
  - Cost by processing stage
  - Input vs output breakdown
  - Per-user cost ranking

**Member Features** (Read-Only):
- View organization members
- See available databases
- Check personal usage stats

---

## 6. LLM Processing Pipeline

### 3-Stage Model

**Stage 1: Summary Generation** (Gemini-2.5-Flash)
- Input: Question + conversation history + database schema
- Output: SQL query (if needed), decision on processing method
- Purpose: Analyze intent and decide approach

**Stage 2: SQL Execution & Response** (Gemini-2.0-Flash)
- Input: SQL query from Stage 1
- Output: Natural language response
- Purpose: Execute and format results

**Stage 3: Email Generation** (Gemini-2.5-Flash) [Optional]
- Input: SQL results, email recipients
- Output: Email object (subject, body, recipients)
- Purpose: Generate professional email

### Example: User Question

```
User: "Send Q4 sales by region to john@example.com"

Stage 1: 
  LLM decides: "This is an email request with SQL need"
  Generates: SELECT region, SUM(amount) FROM sales WHERE year=2024 AND quarter=4

Stage 2:
  Executes query, gets results
  Formats: "Q4 Sales - East: $250K, West: $215K, South: $140K"

Stage 3:
  Generates email subject: "Q4 Sales Breakdown by Region"
  Generates email body with formatted results
  Extracts recipient: john@example.com

Result displayed with token cost: 2,735 tokens = $0.0185
```

---

## 7. Cost Tracking

### What's Tracked

**Per Query**:
- Input tokens (question + context)
- Output tokens (LLM response)
- Cost per stage (Summary Gen, SQL Response, Email Gen)
- Model used (Gemini-2.5-Flash, Gemini-2.0-Flash)
- Processing time

**Per User/Organization**:
- Total tokens consumed
- Total cost
- Breakdown by model
- Breakdown by processing stage
- Usage trends

### Cost Calculation

```
For each stage:
  input_cost = (input_tokens / 1,000,000) * input_price_per_million
  output_cost = (output_tokens / 1,000,000) * output_price_per_million
  stage_cost = input_cost + output_cost

Example:
  Input: 342 tokens @ $0.075/1M = $0.0000256
  Output: 903 tokens @ $0.3/1M = $0.0002709
  Stage total: $0.0003
```
---

## 8. Authentication

### Telegram Bot Auth

**User Identification**: Telegram user_id (unique, immutable)

**Automatic Registration**: On `/start` command
- Stores user ID, name, role
- Creates personal profile
- Assigns role: USER (standalone)

**Role Assignment**:
- Automatic on first use
- Changes when user creates org or joins org
- Can be admin if in ADMIN_TELEGRAM_IDS env var

### Dashboard Web Auth

**Login Process**:
1. User enters username + password
2. Backend validates against dashboard_users table
3. Password checked against PBKDF2 hash
4. Session token generated (32-byte secure random)
5. Token stored in localStorage (24-hour TTL)
6. All requests include: `Authorization: Bearer <token>`

**Credentials Generated**:
- Username: `{role}_{org_slug}_{user_id}` (auto-generated)
- Password: 16-byte random (sent via Telegram once)
- Both hashed before database storage
- New credentials for each new member

---

## 9. Database Architecture

### Two-Database Design

**Manager Database**:
- Stores: Users, organizations, members, databases, invitations
- Purpose: Operational data
- Access: Both bot and dashboard

**Costs Database**:
- Stores: Token counts, costs, model pricing
- Purpose: Analytics and billing
- Access: Both bot and dashboard (dashboard mostly reads)

### Personal vs Organization Databases

**Personal Databases**:
- Owned by individual user
- Access: User only
- Managed via bot (/adddb command)
- Cannot be shared

**Organization Databases**:
- Owned by organization entity
- Access: All org members
- Managed via dashboard (owner only)
- Shared across team

---

## 10. Email Service

### Email Generation

Triggered when user question mentions email keywords: "send", "report", "notify", etc.

**Process**:
1. LLM generates email subject and body
2. Bot displays preview to user
3. User clicks "Send Email"
4. Email sent via Gmail SMTP (asynchronously)
5. Logged in activity trail and cost database

### SMTP Configuration

```
Server: smtp.gmail.com:465 (SSL)
Auth: Gmail app-specific password
Sender: Configured via BOT_EMAIL env var
Template: Customizable greeting + body + signature
```

---

## 11. Logging & Audit

### What's Logged

- User registration and first-time setup
- Commands executed
- Questions asked and answers provided
- SQL queries executed
- Emails sent
- Database selections
- Organization actions
- Errors and exceptions
- Rate limit events

### Log Files

```
logs/
  ├── bot.log                 # App startup/errors
  ├── telegram_activity.log   # User action audit trail
  ├── chat_<id>_activity.log  # Per-chat activity
  └── conversations/
      └── chat_<id>.json      # Full conversation history
```

### Data Retention

- Activity logs: Indefinite
- Conversation files: Last 1,000 per chat
- In-memory cache: Last 5 conversations
- Cost database: Indefinite
- Sensitive data: NOT logged (passwords, API keys)

---

## 12. Rate Limiting & Concurrency

### Rate Limiter (Token Bucket)

**Per-User Settings**:
- Sustainable rate: 1 request/second
- Burst capacity: 3 requests
- Prevents: Server overload, runaway costs

**Example**:
```
T=0s: User sends 3 questions (uses burst) ✓
T=0.1s: 4th question rejected (rate limited) ✗
T=1s: Bucket refilled, user can send again ✓
```

### Concurrency Control

**Limit**: 1 active LLM request per user

**Behavior**:
```
User sends Q1 (processing)
  ↓
User sends Q2 immediately
  ↓
Bot: "Waiting for your previous answer..."
  ↓
Q1 completes
  ↓
Q2 begins processing
```

---

## 13. Conversation Memory

### Sliding Window Architecture

**Active Memory** (In-RAM):
- Last 5 conversations (10 messages)
- 5-minute TTL with auto-refresh

**Historical Record** (File):
- Up to 1,000 conversations per chat
- Preserved for audit and analytics
- JSON format

### Benefits

- Prevents token bloat
- Maintains conversation coherence
- Preserves audit trail
- Auto-cleanup prevents memory leaks

---

## 15. Technology Stack

**Backend**:
- Python 3.9+
- FastAPI (dashboard)
- python-telegram-bot (bot)
- SQLAlchemy (ORM)
- Google Gemini API (LLM)

**Databases**:
- SQL Server (primary)
- SQLAlchemy supports: PostgreSQL, MySQL, SQLite

**Services**:
- Gmail SMTP (email)
- Google Cloud (LLM)

---

## Summary

This system democratizes database access through conversational AI while maintaining enterprise-grade security, cost transparency, and audit trails. It serves both individual power users and organizations with multi-tenant collaboration capabilities.

**Key Takeaways**:
- Dual interface (mobile bot + desktop dashboard)
- Complete cost visibility (token-level tracking)
- Enterprise security (RBAC, audit, organization isolation)
- No SQL knowledge required
- Horizontal scalability
- Production-ready architecture

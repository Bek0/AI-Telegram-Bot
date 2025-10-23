# Enterprise Telegram Bot + Dashboard System
## Professional README & Complete System Documentation

---

## 1. Executive Overview

### What Is This System?

This is an enterprise-grade ecosystem combining a Telegram bot and web dashboard that democratize database access through conversational AI. The system enables organizations to provide secure, auditable, cost-transparent access to databases without requiring SQL knowledge from end users. It's designed for team collaboration, individual autonomy, and operational efficiency at scale.

### Core Components

1. **Telegram Bot** - Mobile-first conversational interface for database querying, email automation, and team management
2. **Web Dashboard** - Administrative and analytics interface for organization management, cost tracking, and team oversight
3. **Shared Backend Services** - LLM processing, database connections, authentication, cost tracking, and audit logging

### The Business Problems It Solves

1. **SQL Knowledge Barrier** - Makes database querying accessible to non-technical users through natural language conversation
2. **Team Data Access** - Enables secure organizational sharing of database connections with granular permission controls
3. **Cost Opacity** - Tracks AI token usage and associated costs at individual, team, and organizational levels
4. **Report Automation** - Generates and distributes formatted emails based on database queries automatically
5. **Compliance Requirements** - Maintains complete, timestamped logs of all interactions and data access for regulatory audit

### Who It's For

- **Individual Power Users** - Knowledge workers seeking self-service database access without IT intermediaries
- **Organizations** - Teams requiring secure collaborative data exploration with role-based access control
- **Enterprise Teams** - Multi-user environments needing usage tracking, cost allocation, and comprehensive audit trails
- **Finance & Operations** - Departments managing API costs and requiring cost attribution by user/department

---

## 2. Complete Project Architecture

### System Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    End Users (Dual Interface)                │
├──────────────────────────┬──────────────────────────────────┤
│    Telegram Bot          │    Web Dashboard                  │
│  (Mobile-First)          │    (Desktop/Analytics)            │
│  • Natural language      │    • Team management              │
│    questions             │    • Database administration      │
│  • Email generation      │    • Cost analytics               │
│  • Team invitations      │    • Member provisioning          │
│  • Query history         │    • Organization oversight       │
└──────────────┬───────────┴──────────────┬────────────────────┘
               │                          │
               └──────────────┬───────────┘
                              │
        ┌─────────────────────┴──────────────────────┐
        │    Shared Backend Services Layer            │
        ├──────────────────────────────────────────────┤
        │ • LLM Processing (Google Gemini API)        │
        │ • Multi-Database Connection Management      │
        │ • User Authentication & Authorization       │
        │ • Organization & Team Management            │
        │ • Email Service (Gmail SMTP)                │
        │ • Token Cost Tracking & Analytics           │
        │ • Activity Logging & Conversation History   │
        │ • Rate Limiting & Concurrency Control       │
        └──────────────────────────────────────────────┘
               │                    │                │
        ┌──────▼──────┐      ┌──────▼──────┐  ┌────▼─────────┐
        │  Manager DB  │      │   Costs DB   │  │  Customer DBs │
        │ (User/Org)   │      │ (Analytics)  │  │  (Queried by  │
        │              │      │              │  │   users)      │
        └──────────────┘      └──────────────┘  └───────────────┘
```

### Key Architectural Principles

- **Shared Backend**: Both interfaces use identical business logic, ensuring data consistency and single source of truth
- **Multi-Tenant Design**: Complete organizational isolation with member-based access control; no data leakage between orgs
- **Cost Transparency**: Every LLM call tracked, priced, and attributable to users/organizations
- **Audit First**: All actions logged with timestamps and user attribution for compliance and forensics
- **Stateless Services**: Horizontally scalable; no session binding to specific servers

---

## 3. Complete Project Structure

```
project-root/
│
├── main_telegram.py              # Bot initialization & lifecycle
├── main.py                       # Dashboard FastAPI initialization
├── db_connection.py              # SQL Server connection pooling
├── connection.py                 # Alternative database handler
│
├── services/                     # Shared business logic (bot + dashboard)
│   ├── telegram_service.py       # Telegram command handlers & callbacks
│   ├── telegram_llm_service.py   # LLM pipeline orchestration
│   ├── telegram_auth.py          # User authentication (Telegram)
│   ├── telegram_logging.py       # Activity & conversation logging
│   ├── database_manager.py       # Multi-database connection management
│   ├── organization_manager.py   # Organization & team management
│   ├── send_email.py             # Email service (Gmail SMTP)
│   ├── sql_service.py            # SQL execution & validation
│   └── token_cost_calculator.py  # Token counting & cost tracking
│
├── dashboard/
│   ├── main.py                   # FastAPI app setup & middleware
│   ├── routes.py                 # API endpoints for all operations
│   ├── auth.py                   # Session token management
│   ├── utils.py                  # Auth decorators & helper functions
│   │
│   ├── templates/
│   │   ├── login.html            # Authentication UI
│   │   ├── dashboard.html        # Main management & analytics
│   │   └── costs.html            # Detailed cost reporting
│   │
│   └── static/
│       ├── css/style.css         # Dashboard styling (responsive)
│       └── js/
│           ├── login.js          # Login form handling
│           └── dashboard.js      # Interactive UI logic & API calls
│
├── models/
│   └── pydantic_models.py        # Data validation (Summary, Mail, Organization)
│
├── memory/
│   └── telegram_conversation.py  # Conversation history & caching logic
│
├── utils/
│   └── prompts.py                # LLM prompt templates & schemas
│
├── logs/
│   ├── bot.log                   # Application startup/errors
│   ├── conversations/            # Chat history (JSON per chat ID)
│   └── telegram_activity.log     # User action audit trail
│
├── .env.example                  # Environment variables template
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

### Key Files & Their Responsibilities

| File | Purpose | Key Functions |
|------|---------|---|
| `main_telegram.py` | Bot lifecycle | Initialize bot, validate env, setup signal handlers, graceful shutdown |
| `telegram_service.py` | Command processing | Handle /start, /help, /createorg, /adddb, /selectdb, /invite, /join, /stats, etc. |
| `telegram_llm_service.py` | LLM orchestration | 3-stage processing (Summary Gen → SQL → Email Gen), token counting, cost calc |
| `database_manager.py` | Connection mgmt | Add/remove/verify database access, connection pooling, health checks |
| `organization_manager.py` | Team management | Create orgs, manage members, generate invitations, track memberships |
| `telegram_auth.py` | Auth (Bot) | User registration, role assignment, profile management |
| `telegram_logging.py` | Audit logging | Log user actions, maintain conversation history, provide statistics |
| `telegram_conversation.py` | Memory & caching | Sliding window cache, conversation file storage, TTL management |
| `token_cost_calculator.py` | Cost tracking | Count tokens, calculate costs, persist to analytics database |
| `send_email.py` | Email service | Generate & send emails via Gmail SMTP, async execution |
| `sql_service.py` | SQL execution | Execute queries, validate results, handle errors, result caching |
| `dashboard/routes.py` | API endpoints | Login, org mgmt, database mgmt, cost analytics endpoints |
| `dashboard/auth.py` | Session mgmt | Create/validate/delete session tokens, timeout handling |

---

## 4. Detailed User Flows

### Flow 1: Individual User Setup (Telegram Only)

```
Step 1: User Starts Bot
────────────────────────
User: /start
    ↓
Bot: Registers user in database (if new)
     Stores: user_id, username, first_name, created_at
     Assigns role: USER (standalone)
     ↓
     Displays welcome message & command guide

Step 2: User Adds Personal Database
───────────────────────────────────
User: /adddb "Sales DB" "sql+pyodbc://server/database"
    ↓
Bot: Validates connection string format
     Tests connection (attempt to connect & run SELECT 1)
     Stores in database_connections table:
       - connection_id (unique)
       - name: "Sales DB"
       - connection_string (encrypted in production)
       - owner_type: "user"
       - owner_id: user_id
       - created_at: timestamp
     ↓
     Confirms: "Database added! Use /selectdb to activate"

Step 3: User Selects Active Database
────────────────────────────────────
User: /selectdb
    ↓
Bot: Fetches all user's databases
     Shows inline buttons with database names
     User clicks on "Sales DB"
     ↓
     Sets user's current_database_id in UserInfo table
     Confirms: "Active database: Sales DB"

Step 4: User Ready to Query
───────────────────────────
User: "What were sales last month?"
    ↓
Bot: Checks rate limiter (1 req/sec, burst 3)
     Checks concurrency (max 1 active per user)
     Begins 3-stage LLM processing
     Returns answer with cost breakdown
     Saves to conversation history
```

### Flow 2: Organization Creation & Member Onboarding

```
Step 1: Owner Creates Organization (Bot)
─────────────────────────────────────────
User (standalone): /createorg "Acme Corp"
    ↓
Bot creates:
  1. organizations record
     - org_id (unique): "ORG_20250115_abc123"
     - name: "Acme Corp"
     - owner_id: user_id
     - created_at: timestamp
     - status: "active"
  
  2. organization_members record (owner entry)
     - org_id
     - user_id (owner)
     - role: "owner"
     - joined_at: timestamp
  
  3. dashboard_users record
     - org_id
     - user_id (owner)
     - username: "owner_acme_abc123" (auto-generated)
     - password_hash: PBKDF2(random_16_bytes)
     - role: "owner"
    ↓
Bot sends private message:
  "Dashboard credentials:
   Username: owner_acme_abc123
   Password: [generated_password]
   Link: https://dashboard.example.com"

Step 2: Owner Logs Into Dashboard
─────────────────────────────────
Owner navigates to dashboard root (/)
    ↓ Redirected to /dashboard/login (no valid session)
    ↓ Enters username + password
    ↓
POST /dashboard/login:
  Backend validates credentials against dashboard_users
  Password checked against stored hash
  If valid:
    - Generate session token (32-byte URL-safe)
    - Store in _sessions dict with 24-hour TTL
    - Return token + org metadata
  If invalid:
    - Return 401 Unauthorized
    ↓
Browser stores token in localStorage
Token included in all subsequent requests (Authorization: Bearer header)
    ↓
Dashboard loads with owner's org data

Step 3: Owner Adds Organization Database
───────────────────────────────────────────
Owner: Dashboard → "Databases" → "Create New"
    ↓ Fills form: Database Name + Connection String
    ↓
POST /dashboard/databases/create:
  Backend validates:
    - Caller is authenticated (session exists)
    - Caller is org owner (role == "owner")
    - Connection string format valid
    - Connection test succeeds
  
  Creates:
    1. database_connections record
       - connection_id
       - name
       - connection_string (encrypted in prod)
       - owner_type: "organization"
       - owner_id: org_id
       - is_active: 1
    
    2. organization_databases record (link table)
       - org_id
       - connection_id
       - added_by: owner_id
       - added_at: timestamp
    ↓
All org members can now query this database via /selectdb in bot

Step 4: Owner Invites Team Members
──────────────────────────────────
Owner: Dashboard → "Invitations" → "Create New"
    ↓ Sets: max_uses = 5, validity = 7 days
    ↓
POST /dashboard/invitations/create:
  Backend:
    - Validates caller is owner
    - Generates invite_code (URL-safe, 12 chars): "AbCd1234XyZ9"
    - Creates invitations record:
        - invite_code
        - org_id
        - created_by: owner_id
        - created_at: timestamp
        - expires_at: now + 7 days
        - max_uses: 5
        - current_uses: 0
        - is_active: 1
    ↓
Dashboard displays: "Share this link: https://app.example.com/join/AbCd1234XyZ9"

Step 5: Team Member Joins (Bot)
───────────────────────────────
Team Member (standalone): /join AbCd1234XyZ9
    ↓
Bot validates invitation:
  - Code exists
  - Not expired (now < expires_at)
  - Uses not exhausted (current_uses < max_uses)
  - User not already in organization
  - Caller is standalone user
    ↓
If valid, bot creates:
  1. organization_members record
     - org_id
     - user_id (member)
     - role: "member"
     - joined_at: timestamp
  
  2. dashboard_users record
     - org_id
     - user_id
     - username: "member_acme_user456" (auto-generated)
     - password_hash: PBKDF2(random_16_bytes)
     - role: "member"
  
  3. invitation_usage_logs record (audit)
     - invite_code
     - user_id (who joined)
     - joined_at: timestamp
    ↓
Bot increments invitations.current_uses
If current_uses >= max_uses: invitations.is_active = 0
    ↓
Bot sends private message:
  "Welcome to Acme Corp!
   Dashboard credentials:
   Username: member_acme_user456
   Password: [generated_password]"

Step 6: Member Uses System
──────────────────────────
Member: /selectdb → Selects shared organization database
    ↓
Member: "What's our Q4 revenue?"
    ↓
Bot verifies member has access to selected database
    ↓
Processes query (same 3-stage LLM pipeline)
    ↓
Owner can monitor in dashboard:
  Dashboard → "Costs" → "Per User"
    Sees which members used most tokens
    Can identify optimization opportunities
```

### Flow 3: Question Processing Pipeline (3-Stage LLM Processing)

```
User: "Send email with Q4 sales breakdown by region to john@example.com"
    ↓
┌──────────────────────────────────────────────────────────────┐
│ Stage 1: Summary Generation (Gemini-2.5-Flash)               │
│ ─────────────────────────────────────────────                │
│ Input:                                                       │
│   • User question                                            │
│   • Last 5 conversations (from memory cache)                 │
│   • Database schema (table names, columns)                   │
│                                                              │
│ LLM Task:                                                    │
│   Analyze intent: SQL query needed? Email? Conversation?    │
│   Generate SQL if needed                                    │
│   Set "way" (SqlQuery / Email / Conversation / None)       │
│                                                              │
│ Output: Summary object                                      │
│   {                                                          │
│     sql_query: "SELECT region, SUM(amount) FROM sales...",│
│     way: "email",                                           │
│     answer: null                                            │
│   }                                                          │
│                                                              │
│ Token count: 1,245 (342 input, 903 output)                 │
│ Cost: $0.00847 (input: $0.00156, output: $0.00691)         │
└──────────────┬───────────────────────────────────────────────┘
               ↓
Rate limiting check: ✓ Pass
Concurrency check: ✓ No active requests
               ↓
┌──────────────────────────────────────────────────────────────┐
│ Stage 2: SQL Execution & Response (Gemini-2.0-Flash)        │
│ ─────────────────────────────────────────────────────────    │
│ Action:                                                      │
│   1. Execute SQL query on selected database                 │
│   2. Retrieve results (e.g., [[East, 250000], [West, ...]]│
│   3. Validate no hallucination (results match query scope)  │
│   4. Pass results to LLM for natural language conversion   │
│                                                              │
│ Input to LLM:                                               │
│   • Original question                                       │
│   • SQL query executed                                      │
│   • Query results (formatted)                               │
│                                                              │
│ LLM Output:                                                 │
│   "Based on Q4 data:                                        │
│    - East region: $250,000 (42%)                           │
│    - West region: $215,000 (36%)                           │
│    - South region: $140,000 (22%)"                         │
│                                                              │
│ Token count: 856 (234 input, 622 output)                    │
│ Cost: $0.00578                                              │
└──────────────┬───────────────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────────────┐
│ Stage 3: Email Generation (Gemini-2.5-Flash) [Optional]    │
│ ─────────────────────────────────────────────────────────    │
│ Since way = "email", generate Mail object:                  │
│                                                              │
│ Input to LLM:                                               │
│   • Original question (has email recipient)                 │
│   • SQL results                                             │
│   • Email template prompt                                   │
│                                                              │
│ LLM Output: Mail object                                     │
│   {                                                          │
│     email: ["john@example.com"],                           │
│     subject: "Q4 Sales Breakdown by Region",               │
│     body: "John,\n\nPlease find attached Q4 sales data..." │
│   }                                                          │
│                                                              │
│ Token count: 634 (189 input, 445 output)                    │
│ Cost: $0.00421                                              │
└──────────────┬───────────────────────────────────────────────┘
               ↓
Bot displays response with email preview:

[LLM Response Text]

📊 Token usage: 2,735 total (765 input, 1,970 output)
💰 Cost: $0.01846
  • Stage 1 (Summary): $0.00847
  • Stage 2 (SQL Response): $0.00578
  • Stage 3 (Email Gen): $0.00421

[Preview Email] [Send Email]

User clicks [Send Email]:
  ↓
Email sent via Gmail SMTP to john@example.com
Action logged to:
  • conversation history
  • telegram_activity.log
  • Conversations table (costs db)
  ↓
User can continue asking questions (conversation context maintained)
```

### Flow 4: Cost Tracking & Analytics

```
Every LLM Call Pipeline:
───────────────────────

Stage completes:
  ├─ Token count (input & output)
  ├─ Retrieve model pricing from ModelPricing table
  │  Example: Gemini-2.5-Flash: $0.075/1M input, $0.3/1M output
  ├─ Calculate stage cost
  │  input_cost = (input_tokens / 1,000,000) * $0.075
  │  output_cost = (output_tokens / 1,000,000) * $0.3
  │  stage_cost = input_cost + output_cost
  │
  └─ Save to ConversationStages table:
     {
       stage_number: 1,
       stage_name: "Summary Generation",
       model_name: "Gemini-2.5-Flash",
       input_tokens: 342,
       output_tokens: 903,
       total_tokens: 1,245,
       input_cost: 0.00256,
       output_cost: 0.00271,
       total_cost: 0.00527,
       timestamp: now()
     }

Conversation Completes:
──────────────────────
1. Save Conversations record
   {
     conversation_id: "CONV_abc123",
     chat_id: 123456,
     user_id: 987654,
     org_id: "ORG_acme" (if org member),
     user_question: original question,
     timestamp: now(),
     total_tokens: 2735,
     total_cost: 0.01846
   }

2. Update aggregate tables (per user/org)
   → ModelUsage (tracks Gemini-2.5-Flash vs 2.0-Flash)
   → StagesUsage (tracks Summary Gen vs SQL Response vs Email Gen)
   → OrgModelUsage (if org member)
   → OrgStagesUsage (if org member)

Dashboard Views Available:
─────────────────────────

Owner: /dashboard/costs/overview
  ├─ Total Cost (all time): $847.92
  ├─ Total Input Tokens: 1,234,567
  ├─ Total Output Tokens: 4,567,890
  └─ Total Conversations: 3,421

Owner: /dashboard/costs/by-model
  ├─ Gemini-2.5-Flash: $512.34 (60%)
  ├─ Gemini-2.0-Flash: $335.58 (40%)
  └─ [Table with token counts per model]

Owner: /dashboard/costs/by-stage
  ├─ Summary Generation: $339.17 (40%)
  ├─ SQL Response: $381.57 (45%)
  └─ Email Generation: $126.18 (15%)

Owner: /dashboard/costs/input-output
  ├─ Input Cost: $169.58 (20%)
  └─ Output Cost: $678.34 (80%) [Pie chart]

Owner: /dashboard/costs/per-user
  ├─ user_456 (Sarah): $245.67 [Highest]
  ├─ user_789 (Mike): $198.34
  ├─ user_123 (Jane): $142.67
  └─ [Sortable, downloadable]
```

---

## 5. Core Features & Commands

### 5.1 Telegram Bot Commands

#### Organization Management (Owners Only)

| Command | Usage | Function | Available To |
|---------|-------|----------|---|
| `/createorg` | `/createorg Acme Corp` | Create organization, become owner | Standalone users |
| `/org` | `/org` | Show org management menu | Org owners |
| `/orginfo` | `/orginfo` | View org statistics & members | All org members |
| `/invite` | `/invite 5 7` | Generate 5-use, 7-day invite code | Org owners |
| `/join` | `/join AbCd1234XyZ9` | Join org via invite | Standalone users |

#### Database Management

| Command | Usage | Function | Available To |
|---------|-------|----------|---|
| `/adddb` | `/adddb Sales DB sql+pyodbc://...` | Add personal or org database | Standalone & org owners |
| `/selectdb` | `/selectdb` | Choose active database (interactive) | All users |
| `/myinfo` | `/myinfo` | Show profile, role, current DB | All users |

#### Utility Commands

| Command | Usage | Function | Available To |
|---------|-------|----------|---|
| `/start` | `/start` | Initialize user, show welcome | All |
| `/help` | `/help` | Show comprehensive command guide | All |
| `/clear` | `/clear` | Clear conversation history | All |
| `/history` | `/history` | Show last 10 questions asked | All |
| `/stats` | `/stats` | Display personal usage statistics | All |

### 5.2 Web Dashboard Features

#### Authentication & Session Management

- **Login Page**: Username + password authentication
- **Session Token**: 24-hour validity with secure storage
- **Auto-Logout**: Redirect to login on session expiration
- **Remember Me**: Optional persistent login (future)

#### Owner-Only Dashboard Features

**Members Management Tab**:
- View all organization members (name, role, join date)
- Add member by Telegram user ID
- Remove member (revokes access immediately)
- Export member list (CSV)

**Databases Tab**:
- List all organization databases
- Add new database (form: name + connection string)
- Remove database (with confirmation)
- Test connection before adding
- Database status indicator (active/inactive)

**Invitations Tab**:
- Create new invitation (set max uses, validity period)
- View active invitations (code, uses, expiration)
- View expired invitations (historical)
- Copy invitation link to clipboard
- Track invitation usage log

**Cost Analytics** (Five Detailed Views):

1. **Overview Cards**
   - Total cost (all time or configurable period)
   - Total input tokens (counted)
   - Total output tokens (counted)
   - Total conversations processed

2. **Input/Output Split**
   - Pie chart visualization
   - Percentage breakdown
   - Often 20% input / 80% output

3. **By AI Model**
   - Table: Model name, usage count, token counts, cost
   - Identify most expensive models
   - Cost comparison Gemini-2.5-Flash vs 2.0-Flash

4. **By Processing Stage**
   - Table: Stage type, count, token usage, cost
   - Summary Generation typically 40%
   - SQL Response typically 45%
   - Email Generation typically 15%

5. **Per User Cost Breakdown**
   - Ranked list of members by cost
   - Conversation count per member
   - Token usage per member
   - Sortable, filterable, downloadable (CSV/PDF)

#### Member-Only Dashboard Features

**View-Only Access**:
- See organization members & roles
- View list of available databases
- Check personal usage statistics
- View personal cost breakdown

---

## 6. Technical Implementation Details

### 6.1 Authentication & Authorization

#### Telegram Bot Authentication

**User Identification Method**:
- Primary identifier: Telegram `user_id` (unique per bot, immutable)
- Display name: Telegram `first_name` + optional `last_name` or `username`
- Registration: Automatic on `/start` command

**User Roles & Permissions**:

```
Role Hierarchy:

ADMIN (System-wide)
  └─ Can manage system settings (not fully implemented)

ORG_OWNER (Organization Level)
  ├─ Create & manage organization
  ├─ Add/remove databases
  ├─ Create member invitations
  ├─ Add/remove members
  ├─ View org statistics
  └─ Access all org databases

ORG_MEMBER (Team Member)
  ├─ Query org databases
  ├─ Ask questions
  ├─ View org info (read-only)
  ├─ Send emails (if question triggers it)
  └─ View personal stats only

USER (Standalone)
  ├─ Add personal databases
  ├─ Query own databases
  ├─ View personal stats
  ├─ Create organization (becomes owner)
  └─ Join organization (loses standalone status)
```

**Authorization Enforcement**:

```
Before executing ANY action:
1. Verify user exists in database
2. Determine user's role (admin/org_owner/org_member/user)
3. Check if action is allowed for that role
4. If database access: Verify user has permission

Example: /adddb command
  ├─ If standalone user → Create personal database ✓
  ├─ If org owner → Create org database ✓
  └─ If org member → Deny (403 Forbidden) ✗
```

#### Dashboard Web Authentication

**Login Process**:

```
1. User navigates to /dashboard/login
2. Enters dashboard username (e.g., "owner_acme_abc123")
3. Enters dashboard password (auto-generated during org creation)
4. Browser: POST /dashboard/login
   Payload: {username: "...", password: "..."}

5. Backend validates:
   - Lookup user in dashboard_users table
   - Verify password matches hash (PBKDF2)
   - If valid:
     * Generate session token (secrets.token_urlsafe(32))
     * Store in _sessions dict: {token → user_metadata}
     * Set TTL: 24 hours (auto-cleanup after 24h inactivity)
     * Return: {token: "...", org_name: "...", role: "owner", ...}
   - If invalid: Return 401 Unauthorized

6. Browser: Stores token in localStorage
   localStorage.setItem('session_token', token)

7. All subsequent requests include token:
   Authorization: Bearer <token>

8. Backend: Validates token before processing request
   - Check token exists in _sessions
   - Check not expired
   - Extract user_id, org_id, role
   - Proceed with authorization checks
```

**Session Token Structure**:

```python
_sessions = {
    'token_abc123xyz789': {
        'org_id': 'ORG_20250115_abc',
        'user_id': 123456789,
        'role': 'owner',  # or 'member'
        'org_name': 'Acme Corp',
        'username': 'owner_acme_abc123',
        'created_at': datetime(2025, 1, 15, 10, 30),
        'last_activity': datetime(2025, 1, 15, 11, 45)
    }
}
```

**Dashboard Credentials**:

Automatically generated when organization created or member joins:

```
Format:
  Username: {role}_{org_slug}_{user_id}
    Example: "owner_acme_123456789" or "member_acme_987654321"
  
  Password: 16-byte cryptographically secure random
    Example: "xK9mP2qL8nR5vBtY"

Storage:
  Hashed with PBKDF2 (iterations=100,000, algorithm=SHA256)
  Stored in dashboard_users table
  Original password sent to user once via Telegram (not stored)
```

#### Role-Based Access Control (RBAC) Matrix

**Dashboard Endpoint Protection**:

| Endpoint | GET | POST | DELETE | Owner Only | Member OK | Public |
|----------|-----|------|--------|------------|-----------|--------|
| `/dashboard/login` | ✓ | ✓ | — | — | — | ✓ |
| `/dashboard/overview` | ✓ | — | — | — | ✓ | — |
| `/dashboard/members` | ✓ | — | — | — | ✓ | — |
| `/dashboard/members/add` | — | ✓ | — | ✓ | ✗ | — |
| `/dashboard/members/remove` | — | — | ✓ | ✓ | ✗ | — |
| `/dashboard/databases` | ✓ | — | — | — | ✓ | — |
| `/dashboard/databases/create` | — | ✓ | — | ✓ | ✗ | — |
| `/dashboard/databases/remove` | — | — | ✓ | ✓ | ✗ | — |
| `/dashboard/invitations` | ✓ | — | — | ✓ | ✗ | — |
| `/dashboard/invitations/create` | — | ✓ | — | ✓ | ✗ | — |
| `/dashboard/costs/overview` | ✓ | — | — | ✓ | ✗ | — |
| `/dashboard/costs/by-model` | ✓ | — | — | ✓ | ✗ | — |
| `/dashboard/costs/by-stage` | ✓ | — | — | ✓ | ✗ | — |
| `/dashboard/costs/per-user` | ✓ | — | — | ✓ | ✗ | — |

### 6.2 Database Connection Management

#### Multi-Database Architecture

**Personal Databases** (For Standalone Users):
```
Ownership: Individual user (user_id)
Access: Only that user can query
Management: User controls via /adddb & /selectdb
Storage: database_connections table
  owner_type: "user"
  owner_id: user_id (Telegram)
```

**Organization Databases** (For Teams):
```
Ownership: Organization entity (org_id)
Access: All members of that organization
Management: Organization owner controls via dashboard
Storage: database_connections + organization_databases (link table)
  owner_type: "organization"
  owner_id: org_id
```

#### Connection Verification Flow

Before executing ANY query:

```
1. Retrieve user's current_database_id from UserInfo
2. Fetch database record from database_connections
3. Check if connection is_active == 1
4. Verify access permissions:
   ├─ If owner_type == "user":
   │  └─ Verify: current_user.user_id == database.owner_id
   ├─ If owner_type == "organization":
   │  ├─ Fetch organization_members record
   │  └─ Verify: current_user is member of database.owner_id org
   └─ Otherwise: DENY (403 Forbidden)
5. Attempt to establish database connection
6. If success: Proceed with query execution
7. If failure: Return error to user
```

#### Connection Pooling & Health Checks

- Connections cached in `_db_instances` dict (keyed by connection_id)
- Timeout-based invalidation: 30 minutes
- Health check: SELECT 1 before reuse
- Auto-cleanup: Connections invalidated when member removed
- Max concurrent connections: 10 per user

### 6.3 LLM Processing Pipeline (3-Stage Model)

#### Stage 1: Summary Generation (Gemini-2.5-Flash)

**Purpose**: Analyze user intent and decide processing approach

**Input**:
- User question (current message)
- Last 5 conversations from memory cache
- Database schema (table names, column names, data types)
- Organization context (if org member)

**Processing Logic**:

```python
IF question_matches_conversation_history:
    way = "conversation"
    answer = extract_from_history()
ELSE IF question_mentions_email:
    way = "email"
    sql_query = generate_sql()
ELSE IF requires_data_lookup:
    way = "SqlQuery"
    sql_query = generate_sql()
ELSE:
    way = "None"
    answer = answer_from_knowledge()
```

**Output**: Summary Pydantic object
```python
{
    sql_query: str (or None),
    answer: str (or None),
    way: Literal["SqlQuery", "email", "conversation", "None"]
}
```

**Token Tracking**:
- Input tokens: 200-500 typical (question + history + schema)
- Output tokens: 400-800 typical
- Cost: $0.004-$0.008 per call

#### Stage 2: SQL Execution & Response (Gemini-2.0-Flash)

**Purpose**: Execute SQL and format results for users

**Input**:
- Generated SQL query from Stage 1
- User's original question (for context)
- Empty if way != "SqlQuery" (skipped if not needed)

**Processing**:

```
1. Connect to user's selected database
2. Execute SQL query with timeout (30 seconds)
3. Fetch results (max 1000 rows to prevent bloat)
4. Validate results:
   - Are rows returned?
   - Do results match query scope (no hallucination)?
   - Are columns what was requested?
5. Format results as markdown table or text
6. Pass to LLM for natural language conversion
7. LLM generates human-readable response
```

**Output**: Natural language response
```
Based on Q4 2024 data:
- East region: $250,000 (42% of total)
- West region: $215,000 (36% of total)
- South region: $140,000 (22% of total)

Total Q4 revenue: $605,000
```

**Token Tracking**:
- Input tokens: 300-600 typical
- Output tokens: 200-500 typical
- Cost: $0.003-$0.006 per call

**Error Handling**:
- SQL syntax error → Show error + suggestion
- Connection timeout → Show "Database unavailable"
- No results → Show "No data matches your criteria"
- Too many results → Show first 100 + "... (showing 1 of 5,000 results)"

#### Stage 3: Email Generation (Gemini-2.5-Flash) [Optional]

**Purpose**: Generate professional email with query results

**Triggered Only When**: way == "email" from Stage 1

**Input**:
- SQL results from Stage 2
- Email recipient(s) (extracted from question)
- Email template prompt
- Optional: User's signature

**Processing**:

```
1. Extract recipient email(s) from question
   "Send to john@example.com and sarah@company.com"
   → recipients = [john@example.com, sarah@company.com]

2. LLM generates:
   - Subject line (professional, descriptive)
   - Body (formatted, with data embedded)
   - Uses template structure (greeting + content + closing)

3. Create Mail object:
   {
       email: [john@example.com, sarah@company.com],
       subject: "Q4 Sales Breakdown by Region",
       body: "John and Sarah,\n\nPlease find the Q4 sales breakdown..."
   }

4. Display preview to user with [Send] button
```

**Output**: Mail object (if email requested)
```python
{
    email: List[str],
    subject: str,
    body: str
}
```

**Token Tracking**:
- Input tokens: 150-400 typical
- Output tokens: 200-500 typical
- Cost: $0.003-$0.005 per call

### 6.4 Email Service Implementation

#### Email Generation & Sending

**Trigger Detection**:
- LLM detects email-related keywords in question
- Examples: "send email", "report", "notify", "forward", "distribute"

**SMTP Configuration**:
```
Server: smtp.gmail.com
Port: 465 (SSL/TLS)
Authentication: Gmail app-specific password
Sender: BOT_EMAIL (from .env)
Rate Limit: Gmail's standard 300 per minute per account
```

**Email Sending Process**:

```
1. LLM generates Mail object (Stage 3)
2. Bot displays email preview to user
3. User clicks [Send Email] button
4. Backend constructs MIME message:
   - From: BOT_EMAIL
   - To: recipients (from Mail.email list)
   - Subject: Mail.subject
   - Body: Mail.body (HTML formatted)
5. Connect to Gmail SMTP (with auth)
6. Send message asynchronously (doesn't block user)
7. Log email sent:
   - Activity log entry
   - Conversation record
   - Costs table record
8. Return confirmation to user

Example flow in code:
try:
    asyncio.create_task(send_async(subject, body, recipients))
    return "Email queued for sending"
except SMTPException as e:
    return f"Email send failed: {str(e)}"
```

**Email Template**:
```
Hello {{recipient_first_name}},

{{body_content}}

Best regards,
{{signature}}
```

### 6.5 Conversation Memory & Caching System

#### Sliding Window Architecture

**Purpose**: Maintain conversation context while minimizing token usage (and cost)

**Memory Levels**:

```
Level 1: Active Memory (In-RAM)
  ├─ Stores: Last 5 conversations (10 messages)
  ├─ TTL: 5 minutes (auto-refresh on new message)
  ├─ Purpose: Fast context for LLM
  └─ Benefit: Reduces token cost by 70% vs unlimited history

Level 2: Historical Record (File)
  ├─ Stores: Up to 1,000 conversations per chat
  ├─ Format: JSON (one file per chat_id)
  ├─ Purpose: Audit trail & analytics
  └─ Benefit: Complete history preserved for compliance

Level 3: Database Records (Cost Analytics)
  ├─ Stores: Conversation summaries + costs
  ├─ Retention: Indefinite
  └─ Purpose: Cost reporting & usage analytics
```

**Memory Loading Logic**:

```
When user sends message:
1. Check if memory exists in-RAM (5-min TTL)
2. If cache valid:
   - Use cached conversations
   - Use last 5 conversations only
3. If cache expired or miss:
   - Load from file: logs/conversations/chat_<chat_id>.json
   - Extract last 5 conversations
   - Cache result (5-min TTL)
4. Pass to LLM for context (not unlimited history)
5. After LLM processes:
   - Save new conversation to file
   - Update in-memory cache
   - If file > 1,000 conversations: Delete oldest
```

**Example Memory File**:
```json
[
  {
    "timestamp": ,
    "user_id": ,
    "username": ,
    "question": ,
    "answer": ,
    "sql_query": ,
    "sql_result": 
  },
  ...
]
```

**Cache Benefits**:
- Token reduction: ~70% fewer tokens vs unlimited history
- Cost reduction: Direct consequence of token reduction
- Context maintained: Enough history for coherent conversation
- Audit preserved: Full history in files for compliance
- Memory safe: Auto-cleanup prevents memory leaks

### 6.6 Rate Limiting & Concurrency Control

#### Token Bucket Rate Limiter

**Algorithm**: Token Bucket (industry standard)

**Configuration Per User**:
```
Sustainable rate: 1 request per second
Burst capacity: 3 requests
Bucket size: 3 tokens
Refill rate: 1 token per second
```

**Example Scenarios**:

```
Scenario 1: Normal usage
  T=0s: User sends Q1 (tokens: 3 → 2)
  T=0.5s: User sends Q2 (tokens: 2 → 1)
  T=1s: User sends Q3 (tokens: 1 → 0, bucket refilled to 1)
  T=1.5s: User sends Q4 (tokens: 1 → 0)
  Result: ✓ All requests accepted

Scenario 2: Burst (user sends 3 rapid questions)
  T=0s: Q1, Q2, Q3 sent
  Bucket check: 3 tokens available
  Result: ✓ All 3 accepted (uses full burst capacity)
  Bucket now: 0 tokens
  
  T=0.1s: Q4 sent
  Bucket check: 0 tokens available
  Result: ✗ Rate limit hit, user must wait 0.9s

Scenario 3: After rate limit hit
  T=0.1s: Q4 rejected (rate limited)
  T=1.0s: Bucket refilled (1 token)
  T=1.0s: User retries Q4
  Result: ✓ Accepted
```

#### Concurrency Control

**Per-User Limit**: Maximum 1 active LLM request

**Implementation**:
```python
user_active_requests = {}

def can_process_request(user_id):
    if user_id in user_active_requests:
        return False  # Already processing
    return True

# When starting to process
user_active_requests[user_id] = True

# When processing completes
del user_active_requests[user_id]
```

**User Experience**:
```
User sends Q1 (starts processing)
  ↓ (LLM processing for 5 seconds)
User sends Q2 immediately
  ↓ Bot responds: "Waiting for your previous answer..."
  ↓ User must wait for Q1 to complete
Q1 completes
  ↓ Now Q2 is allowed to process
```

**Benefits**:
- Prevents queue explosion on slow databases
- Avoids accidental double-processing
- Prevents token cost explosion
- Database connection pooling remains efficient

### 6.7 Activity Logging & Audit Trail

#### Log Files & Locations

**Log Files**:
```
logs/
  ├── bot.log
  │   └─ Application startup, initialization, errors
  │      Example: "Bot initialized with token: xxxx..."
  │               "Database connection failed: timeout"
  │
  ├── telegram_activity.log
  │   └─ Global user action audit trail
  │      Example: "[2025-01-15 14:32:10] user_123 | /start | ..."
  │               "[2025-01-15 14:32:15] user_123 | QUESTION | ..."
  │
  ├── chat_<chat_id>_activity.log
  │   └─ Per-chat activity (separate file for each conversation)
  │
  └── conversations/
      └── chat_<chat_id>_conversation.json
          └─ Full conversation history (JSON format, up to 1000 entries)
```

#### What Gets Logged

**Events**:
- User registration/first seen
- Commands executed (/start, /help, /adddb, etc.)
- Questions asked (question text, not always results)
- SQL queries executed (SQL text only)
- Query results (optional, if not sensitive)
- Emails generated & sent
- Database selected/changed
- Organization actions (create, join, member add/remove)
- Errors and exceptions (with stack traces)
- Rate limit events
- Session timeouts

**Log Entry Format**:
```
[2025-01-15 14:32:10] user_123 (chat_456) | EVENT_TYPE | Details
  Example: [2025-01-15 14:32:10] user_123 (chat_456) | QUESTION_ASKED | Q: "What are sales?"
  Example: [2025-01-15 14:32:20] user_123 (chat_456) | QUESTION_ANSWERED | Cost: $0.0084, Tokens: 1245
  Example: [2025-01-15 14:32:25] user_123 (chat_456) | EMAIL_SENT | To: john@example.com
```

#### Data Retention Policy

```
Activity logs:        Indefinite (compliance requirement)
Conversation files:   Last 1,000 per chat (auto-cleanup)
In-memory cache:      Last 5 conversations (30-min TTL)
Cost database:        Indefinite (for billing & analytics)
Sensitive data:       NOT logged (passwords, API keys, CCN)
```

### 6.8 Cost Tracking & Token Accounting

#### What's Tracked Per Conversation

```
Conversation Record:
  ├─ conversation_id (unique)
  ├─ chat_id (Telegram chat ID)
  ├─ user_id (Telegram user ID)
  ├─ org_id (if org member, else null)
  ├─ user_question (original question text)
  ├─ timestamp (when conversation started)
  ├─ total_tokens (input + output sum)
  ├─ total_cost (sum of all stages)
  └─ duration_ms (processing time)

Per-Stage Record:
  ├─ stage_number (1, 2, 3...)
  ├─ stage_name ("Summary Generation", "SQL Response", "Email Gen")
  ├─ model_name ("Gemini-2.5-Flash", "Gemini-2.0-Flash")
  ├─ input_tokens (counted by LLM)
  ├─ output_tokens (counted by LLM)
  ├─ total_tokens (input + output)
  ├─ input_cost (calculated)
  ├─ output_cost (calculated)
  ├─ total_cost (input_cost + output_cost)
  └─ timestamp (stage completion time)
```

#### Cost Calculation Formula

```
For each LLM call:

1. Token Counting:
   input_tokens = count_tokens(prompt)
   output_tokens = count_tokens(response)
   total_tokens = input_tokens + output_tokens

2. Cost Lookup (from ModelPricing table):
   model = "Gemini-2.5-Flash"
   input_price_per_million = $0.075
   output_price_per_million = $0.3

3. Cost Calculation:
   input_cost = (input_tokens / 1,000,000) * $0.075
   output_cost = (output_tokens / 1,000,000) * $0.3
   stage_cost = input_cost + output_cost

4. Example:
   input_tokens: 342
   output_tokens: 903
   
   input_cost = (342 / 1,000,000) * $0.075 = $0.00002565
   output_cost = (903 / 1,000,000) * $0.3 = $0.0002709
   stage_cost = $0.00029655 ≈ $0.0003

5. Conversation Total:
   conversation_cost = stage_1_cost + stage_2_cost + stage_3_cost
   Example: $0.0084 + $0.0058 + $0.0042 = $0.0184
```

#### Database Tables (Costs Schema)

```
ModelPricing:
  - model_id (PK)
  - model_name ("Gemini-2.5-Flash", etc.)
  - input_price_per_million
  - output_price_per_million
  - effective_date

Conversations:
  - conversation_id (PK)
  - chat_id, user_id, org_id
  - user_question, timestamp
  - total_tokens, total_cost

ConversationStages:
  - stage_id (PK)
  - conversation_id (FK)
  - stage_number, stage_name, model_name
  - input/output tokens, costs
  - timestamp

ModelUsage (Aggregate):
  - user_id, model_name
  - total_tokens, total_cost
  - conversation_count, last_used

StagesUsage (Aggregate):
  - user_id, stage_name
  - total_tokens, total_cost
  - usage_count

OrgModelUsage, OrgStagesUsage (Organization-level):
  - org_id instead of user_id
  - Same structure as per-user tables
```

---

## 7. Deployment & Operations

### Environment Variables Required

```bash
# Telegram Configuration (Required)
TELEGRAM_BOT_TOKEN=<bot_token_from_botfather>
  # Get from BotFather: https://t.me/botfather

# Email Service (Required for email features)
BOT_EMAIL=<gmail_address>
  # Example: company-bot@gmail.com
BOT_EMAIL_PASS=<gmail_app_password>
  # Use Gmail app password (not regular password)
  # Generate at: https://myaccount.google.com/apppasswords

# Administration
ADMIN_TELEGRAM_IDS=<comma_separated_admin_user_ids>
  # Example: 123456789,987654321,111111111
  # Users with system admin role

# Database Connections
DATABASE_URI=<optional_default_database_connection_string>
  # Example: sql+pyodbc://server/database?driver=ODBC+Driver+17

# LLM / Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=<path_to_google_cloud_json>
  # Path to service account JSON file
  # Download from Google Cloud Console

# Dashboard (Optional)
DASHBOARD_PORT=8000
  # Port for FastAPI server (default: 8000)

DASHBOARD_SECRET_KEY=<secret_key_for_session_signing>
  # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
```

### Python Dependencies

```
# Core dependencies (from requirements.txt)
python-telegram-bot>=20.0           # Telegram bot API wrapper
langchain-community>=0.0.1          # LLM orchestration framework
langchain-google-genai>=0.0.1       # Google Gemini integration
sqlalchemy>=2.0                     # Database ORM
pyodbc>=5.0                         # SQL Server driver
fastapi>=0.104                      # Dashboard web framework
uvicorn>=0.24                       # ASGI server
aiofiles>=23.0                      # Async file operations
python-dotenv>=1.0                  # Environment configuration
pydantic>=2.0                       # Data validation
email-validator>=2.0                # Email validation
python-multipart>=0.0.6             # Form data parsing
```

### Deployment Architecture (Recommended)

**Development**:
- Host: Local machine or development VM
- Bot: `python main_telegram.py` (console logs)
- Dashboard: `uvicorn dashboard.main:app --reload` (auto-restart on changes)
- Database: Local SQL Server or Docker container

**Production**:

```
┌─────────────────────────────────────────┐
│         Load Balancer / DNS              │
├─────────────────────────────────────────┤
│         Telegram Webhooks                │
│      (optional, for scalability)         │
├──────────────┬──────────────────────────┤
│  Cloud Run   │  App Engine / Cloud Run   │
│  (Bot)       │  (Dashboard)              │
│  Async/      │  FastAPI instance(s)     │
│  Long-lived  │                          │
└──────────────┴──────────────────────────┘
       ↓              ↓              ↓
   ┌───────────────────────────────────┐
   │   Cloud SQL / RDS (Databases)    │
   │  ├─ Manager DB (user/org data)   │
   │  └─ Costs DB (analytics)         │
   └───────────────────────────────────┘
       ↓              ↓
   ┌───────────────────────────────────┐
   │   Cloud Storage / S3              │
   │   (Conversation logs, backups)    │
   └───────────────────────────────────┘
```

**Recommended Cloud Platforms**:
- **Google Cloud**: Cloud Run (bot) + App Engine (dashboard) + Cloud SQL
- **AWS**: Lambda + API Gateway (bot) + Fargate (dashboard) + RDS
- **Azure**: Azure Functions (bot) + App Service (dashboard) + SQL Database
- **Heroku**: Dyno (bot + dashboard) + Heroku Postgres

### Scaling Considerations

**Horizontal Scaling** (add more instances):
- Both bot and dashboard are stateless
- Session tokens stored in Redis (not in-memory)
- Database connections handled by pooling
- Rate limiting keyed by user_id (works across instances)

**Vertical Scaling** (more powerful machines):
- Async/await architecture handles high concurrency
- Connection pooling prevents resource exhaustion
- Memory usage stays low (sliding window cache)

**Database Scaling**:
- Use database read replicas for analytics queries
- Separate databases for operational (manager) and analytical (costs) data
- Connection pooling (max 20 connections per instance)
- Query optimization with indexes on user_id, org_id, created_at

---

## 8. Known Limitations & Future Enhancements

### Current Limitations

1. **One Organization Per User** (By Design)
   - Users cannot be members of multiple organizations simultaneously
   - Simplifies billing and permission model
   - Can be enhanced in future versions with separate org contexts

2. **LLM Dependency**
   - Requires active internet connection to Google Gemini API
   - No offline fallback or caching of LLM responses
   - Service disruptions affect availability

3. **Database Support**
   - Primarily tested with SQL Server
   - Other databases require compatible pyodbc drivers
   - Schema introspection optimized for SQL Server

4. **Email Throttling**
   - No built-in rate limiting on email sending
   - Depends on Gmail provider rate limits (300/minute)
   - No queue for failed email retries

5. **Conversation Context**
   - Only last 5 conversations in active memory
   - Older conversations in file-based storage only
   - May lose some nuance across very long conversations

6. **Timezone Handling**
   - All timestamps stored in UTC
   - Dashboard shows UTC times (needs localization)

### Planned Enhancements

- Multi-organization membership for power users (with per-org context switching)
- Custom LLM model selection per organization
- Advanced dashboard charts (trend analysis, forecasting, anomaly detection)
- Slack integration alongside Telegram
- Database connection encryption at rest (TDE)
- SSO/OAuth integration (Google, Microsoft AD)
- API key authentication for programmatic access
- Webhook notifications for query results
- Custom email templates and branding
- Data export (CSV, Excel, JSON formats)
- Mobile app (iOS/Android) alternative to Telegram

---

## 9. Troubleshooting & Support

### Common Issues

**Bot Won't Start**:
- Verify TELEGRAM_BOT_TOKEN is valid (copy from BotFather)
- Check database connection (DATABASE_URI)
- Review logs in bot.log

**Gmail Email Not Sending**:
- Verify BOT_EMAIL is correct
- Ensure BOT_EMAIL_PASS is Gmail app password (not regular password)
- Check Gmail account hasn't locked emails (check security alerts)

**Database Connection Fails**:
- Test connection string manually with SQL Server Management Studio
- Verify pyodbc driver is installed (`pip show pyodbc`)
- Check firewall rules allow connection
- Verify credentials in connection string

**Rate Limiting Too Strict**:
- Current settings: 1 req/sec, burst 3
- Can be adjusted in code (search for RateLimiter)
- Consider user's actual needs before adjusting

**Dashboard Login Not Working**:
- Verify credentials were sent in Telegram message (check DMs)
- Username format: `owner_org_userid` or `member_org_userid`
- Check browser localStorage has session token
- Try logging out and logging back in

---

## 10. Conclusion & Value Summary

### Enterprise Value Proposition

**For Individual Users**:
- Eliminate SQL knowledge barrier → Instant self-service access
- Reduce IT dependency → No more "can you run this query?" requests
- Faster decision-making → 30 seconds vs. days
- Transparent costs → See exactly what API calls cost

**For Organizations**:
- Team productivity → Members work autonomously
- Security & compliance → Complete audit trail of all data access
- Cost optimization → Detailed tracking identifies inefficiencies
- Operational efficiency → Email automation eliminates manual reporting
- Scalability → Multi-tenant design supports unlimited organizations

### Key Differentiators

1. **Dual Interface** - Mobile bot for ad-hoc queries + desktop dashboard for administration
2. **Complete Cost Visibility** - Token-level tracking with per-model, per-stage breakdown
3. **Enterprise Security** - Role-based access, audit trails, organization isolation
4. **No SQL Required** - True natural language interface, not SQL translation
5. **Horizontal Scalability** - Stateless architecture supports unlimited users
6. **Audit Compliance** - Comprehensive logging for regulatory requirements

### Getting Started

1. **Clone repository**: `git clone <repo_url>`
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Configure environment**: Copy `.env.example` to `.env` and fill in values
4. **Initialize databases**: Run migration scripts
5. **Start bot**: `python main_telegram.py`
6. **Start dashboard**: `uvicorn dashboard.main:app`
7. **Test**: Message bot `/start` or visit dashboard `/dashboard/login`

### Support & Contribution

- Report issues on GitHub Issues
- Submit feature requests via GitHub Discussions
- Contribute improvements via Pull Requests
- Community Telegram group: [Link]
- Documentation: [Wiki Link]

---

**Last Updated**: January 2025  
**Version**: 1.0.0  
**Status**: Production Ready

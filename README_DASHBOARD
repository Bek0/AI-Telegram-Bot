# Professional README: Complete System Analysis - Dashboard

#### `dashboard/routes.py`
**Purpose**: FastAPI endpoints for all dashboard operations

**Endpoints Overview**:

**Authentication**:
- `POST /dashboard/login` - Dashboard user login
- `POST /dashboard/logout` - Session cleanup
- `GET /dashboard/verify` - Session validation

**Overview & Organization**:
- `GET /dashboard/overview` - Dashboard statistics
- `GET /dashboard/members` - List organization members
- `POST /dashboard/members/add` - Add member (Owner only)
- `POST /dashboard/members/remove` - Remove member (Owner only)

**Database Management**:
- `GET /dashboard/databases` - List org databases
- `POST /dashboard/databases/create` - Add database (Owner only)
- `POST /dashboard/databases/remove` - Delete database (Owner only)

**Invitations**:
- `GET /dashboard/invitations` - List invitations (Owner only)
- `POST /dashboard/invitations/create` - Generate invitation (Owner only)

**Cost Analytics** (Owner only):
- `GET /dashboard/costs/overview` - Total costs summary
- `GET /dashboard/costs/by-model` - Costs per AI model used
- `GET /dashboard/costs/by-stage` - Costs per processing stage
- `GET /dashboard/costs/input-output` - Input vs output cost split
- `GET /dashboard/costs/per-user` - Per-member cost breakdown

#### `dashboard/auth.py`
**Purpose**: Session token management

**Key Functions**:
- `create_session()` - Generate secure token for logged-in user
- `get_session()` - Retrieve session data with timeout validation
- `delete_session()` - Logout & cleanup
- `is_session_valid()` - Quick validation check

**Session Data Structure**:
```python
{
    'org_id': 'ORG_20250101120000_abc123',
    'user_id': 123456789,
    'role': 'owner',  # or 'member'
    'org_name': 'Company Name',
    'username': 'dashboard_username',
    'created_at': datetime.now()
}
```

**Timeout**: 24 hours

#### `dashboard/utils.py`
**Purpose**: Helper functions for authentication & decorators

**Key Functions**:
- `get_session_from_headers()` - Extract Bearer token from HTTP headers
- `require_auth` - Decorator to verify session validity
- `require_owner` - Decorator to restrict to owners only

### Updated: Frontend Components

#### `dashboard/templates/login.html`
**Purpose**: Authentication interface

**Features**:
- Simple two-field form (username + password)
- Error message display
- Loading spinner during submission
- Form validation on client-side

**Flow**:
1. User enters dashboard username & password
2. Form submitted to `/dashboard/login`
3. Backend validates against `dashboard_users` table
4. Returns token + user metadata
5. Token stored in `localStorage` for subsequent requests
6. Redirect to `/dashboard/`

#### `dashboard/templates/dashboard.html`
**Purpose**: Main organization management interface

**Tabs/Sections**:

**1. Overview (Auto-loaded)**
- Members count
- Databases count
- Active invitations
- Organization creation date

**2. Members Tab (All users see)**
- List all organization members
- Show role (owner/member)
- Join date
- **Owner-only**: Add member by user_id, remove member button

**3. Databases Tab (All users see)**
- List all org databases
- Show connection ID & creation date
- **Owner-only**: Create new database form, delete button

**4. Invitations Tab (Owner only)**
- Create new invitation form
- List active invitations
- Show code, usage count, expiration date

**5. Costs Tab (Owner only)**
- Multiple sub-sections:
  - **Overview Cards**: Total cost, input tokens, output tokens, conversation count
  - **Input/Output Split**: Pie chart showing cost distribution
  - **By Model**: Table of costs per AI model (Gemini-2.5, etc.)
  - **By Stage**: Table of costs per processing stage (Summary Gen, SQL Response, Email Gen)
  - **Per User**: Table showing each member's contribution to total cost

#### `dashboard/static/js/dashboard.js`
**Purpose**: Frontend logic for dashboard interactions

**Key Functions**:

```javascript
// Authentication & Setup
loadDashboard()              // Load org data on page load
logout()                     // Clear tokens and redirect to login

// Members Management
loadMembers()               // Fetch and display member list
addMember()                 // Add new member by user ID
removeMember(userId)        // Remove member (Owner only)

// Database Management
loadDatabases()             // Fetch and display database list
createDatabase()            // Add new database connection
removeDatabase(connId)      // Remove database from org

// Invitations Management
loadInvitations()           // Display active invitations
createInvitation()          // Generate new invitation code

// Cost Tracking
loadCostsOverview()         // Load total cost metrics
loadCostsByModel()          // Load model-specific costs
loadCostsByStage()          // Load stage-specific costs
loadInputOutputCosts()      // Generate pie chart
loadCostsPerUser()          // Load per-user cost breakdown
```

**Data Flow**:
1. On page load, verify session token
2. Fetch org metadata from `/dashboard/overview`
3. Load each tab's data on demand (lazy loading)
4. All requests include `Authorization: Bearer <token>` header
5. Display errors if session expires (401 response)

#### `dashboard/static/js/login.js`
**Purpose**: Login form handling

**Process**:
1. Form submission intercepted
2. Username + password validated (required)
3. POST to `/dashboard/login`
4. If successful: store token + redirect
5. If failed: show error message

### Updated: Backend Integration Points

#### How Dashboard Connects to Telegram Services

**Shared Services**:
```
database_manager.py
  ├─ add_connection()          [Used by: Dashboard to add org databases]
  ├─ get_organization_connections()  [Used by: Dashboard to list databases]
  └─ verify_user_can_access_database()  [Used by: Bot to verify access]

organization_manager.py
  ├─ authenticate_dashboard_user()     [Used by: Dashboard login]
  ├─ get_organization()                [Used by: Dashboard overview]
  ├─ get_organization_statistics()     [Used by: Dashboard stats]
  ├─ get_organization_members_with_roles()  [Used by: Dashboard members list]
  ├─ add_member_directly()             [Used by: Dashboard add member]
  ├─ remove_member()                   [Used by: Dashboard remove member]
  └─ create_invitation()               [Used by: Dashboard create invite]

token_cost_calculator.py
  ├─ save_conversation()               [Used by: Bot to log usage]
  ├─ update_model_usage()              [Used by: Bot to track costs]
  └─ [Queries used by: Dashboard cost endpoints]
```

**Database Connections**:
```
manager database (db_connection.py)
  ├─ organizations
  ├─ organization_members
  ├─ organization_databases
  ├─ database_connections
  ├─ dashboard_users
  ├─ invitations
  └─ invitation_usage_logs

costs database (SessionLocal_2)
  ├─ ModelPricing
  ├─ Conversations
  ├─ ConversationStages
  ├─ ConversationSummary
  ├─ ModelUsage
  ├─ StagesUsage
  ├─ OrgModelUsage
  └─ OrgStagesUsage
```

---

## 5. Detailed Functional Report - Complete System

### 5.1 Authentication & Authorization

#### Telegram Bot Authentication

**User Identification**:
- Primary key: `user_id` from Telegram API
- Display name: `first_name` + optional `last_name` or `username`
- Roles determined at join time:
  - `admin` - System administrator (from ADMIN_TELEGRAM_IDS env var)
  - `org_owner` - Owns an organization
  - `org_member` - Member of an organization
  - `user` - Standalone (no organization)

**Authorization Model**:
```
Can /adddb:
  ✓ Standalone users → creates personal database
  ✓ Organization owners → creates org database
  ✗ Organization members → denied (use owner's databases)

Can /selectdb:
  ✓ All users → can select from their available databases

Can /org commands:
  ✓ Standalone users → create organization
  ✓ Org owners → manage organization
  ✓ Org members → view organization (read-only)

Can /invite & /join:
  ✓ Org owners → create invitations
  ✓ Any standalone user → join organization
  ✗ Org members → cannot join another org
```

#### Dashboard Authentication

**Login Process**:
1. User navigates to dashboard root (`/`)
2. Redirected to login page
3. Enters `username` + `password`
4. Backend validates against `dashboard_users` table:
   - Stored as: `username` (plaintext for simplicity) + `password_hash` (PBKDF2)
   - Contains: `org_id`, `user_id`, `role` (owner/member)
5. Success: Generate session token + store metadata
6. Token stored in browser `localStorage`
7. All subsequent requests include `Authorization: Bearer <token>` header

**Session Token Structure**:
```python
token = secrets.token_urlsafe(32)  # 32-byte secure random
_sessions[token] = {
    'org_id': '...',
    'user_id': 123,
    'role': 'owner',
    'org_name': '...',
    'username': '...',
    'created_at': datetime.now()
}
```

**Session Timeout**: 24 hours (configurable)

**Credentials Generation**:
- When org created: Owner gets auto-generated credentials
- When member joins: Member gets auto-generated credentials
- Format: `username = member_<org_id>_<user_id>`, `password = random 16-byte`
- Both hashed with PBKDF2 before storage

#### Role-Based Access Control (RBAC)

**Dashboard Access Matrix**:

| Operation | Owner | Member | Non-Member |
|-----------|-------|--------|-----------|
| View members | ✓ | ✓ | ✗ |
| Add member | ✓ | ✗ | ✗ |
| Remove member | ✓ | ✗ | ✗ |
| View databases | ✓ | ✓ | ✗ |
| Add database | ✓ | ✗ | ✗ |
| Remove database | ✓ | ✗ | ✗ |
| Create invitation | ✓ | ✗ | ✗ |
| View invitations | ✓ | ✗ | ✗ |
| View costs | ✓ | ✗ | ✗ |

**Telegram Bot Access Matrix**:

| Command | Standalone | Owner | Member |
|---------|-----------|-------|--------|
| /createorg | ✓ | ✗ (already org owner) | ✗ (in org) |
| /adddb | ✓ (personal) | ✓ (org) | ✗ |
| /selectdb | ✓ | ✓ | ✓ |
| /org | ✓ (info only) | ✓ (full) | ✓ (view) |
| /invite | ✗ | ✓ | ✗ |
| /join | ✓ | ✗ | ✗ |

### 5.2 Organization & Team Management

#### Organization Lifecycle

**Creation**:
```
User executes /createorg "Company Name"
    ↓
Bot creates:
  1. organizations record
     - org_id (unique)
     - name
     - owner_id (user who created)
     - created_at
     - description (optional)
  2. organization_members record (owner)
     - org_id
     - user_id (owner)
     - role = 'owner'
     - joined_at
  3. dashboard_users record
     - org_id
     - user_id (owner)
     - username (auto-generated)
     - password_hash (auto-generated)
     - role = 'owner'
    ↓
Bot sends credentials to owner in private message
```

**Member Invitation System**:

```
Owner invokes /invite [max_uses] [hours_valid]
    ↓
Bot generates:
  1. invitations record
     - invite_code (unique, URL-safe)
     - org_id
     - created_by (owner_id)
     - created_at
     - expires_at (now + hours_valid)
     - max_uses
     - current_uses = 0
     - is_active = 1
    ↓
Bot displays code to owner
    ↓
Owner shares code with team member
    ↓
Team member invokes /join <code>
    ↓
Bot validates:
  - Code exists
  - Not expired
  - Uses not exhausted
  - User not already in org
    ↓
If valid, creates:
  1. organization_members record
  2. dashboard_users record with random credentials
  3. invitation_usage_logs record (audit trail)
    ↓
Increments current_uses
If current_uses >= max_uses: is_active = 0
    ↓
Bot sends member dashboard credentials
```

#### Member Management

**Adding Members (Dashboard - Owner Only)**:
```
Owner clicks "Add Member" in dashboard
    ↓
Enters Telegram user_id
    ↓
POST /dashboard/members/add
    ↓
Backend validates:
  - Caller is owner
  - User_id exists
  - User not already in another org
    ↓
Creates:
  - organization_members record
  - dashboard_users record
    ↓
Member can now join via bot
```

**Removing Members (Dashboard - Owner Only)**:
```
Owner clicks remove button next to member
    ↓
POST /dashboard/members/remove
    ↓
Backend:
  - Deletes organization_members record
  - Deletes dashboard_users record
  - Disconnects any active databases
  - Member loses all access immediately
    ↓
If member was using database in bot:
  - Next question attempt shows "database disconnected"
```

#### Statistics & Insights

**Organization Statistics** (Owner Dashboard):
- Members count
- Active databases count
- Active invitations count
- Expired invitations count
- Organization creation date
- Total cost (sum of all conversations)
- Average cost per member
- Most expensive member

### 5.3 Database Connection Management

#### Connection Lifecycle

**Personal Database (Standalone Users)**:
```
User: /adddb <name> <connection_string>
    ↓
Bot creates database_connections record:
  - connection_id
  - name
  - connection_string
  - created_by (user_id)
  - owner_type = 'user'
  - owner_id = str(user_id)
  - is_active = 1
    ↓
Bot validates connection works
    ↓
User can /selectdb to use it
```

**Organization Database (Owner via Dashboard)**:
```
Owner: Create Database form in dashboard
    ↓
POST /dashboard/databases/create
    ↓
Backend creates:
  1. database_connections record
     - owner_type = 'organization'
     - owner_id = org_id
  2. organization_databases record
     - Links connection to org
    ↓
All members can /selectdb and query it
```

#### Connection Verification

**Before Every Query**:
```
User asks question in bot
    ↓
System retrieves user's current_database from UserInfo
    ↓
Calls verify_user_can_access_database(user_id, db_id)
    ↓
Checks:
  1. Connection exists and is_active
  2. If owner_type = 'user': Owns this connection
  3. If owner_type = 'organization': Is member of that org
    ↓
GRANT access → Execute query
DENY access → Show error
```

**Pool Management**:
- Connections cached in `_db_instances` dict
- Timeout-based invalidation
- Auto-cleanup on member removal
- Connection validation before reuse

### 5.4 Cost Tracking & Analytics

#### Cost Calculation Pipeline

**Per Query**:
```
1. LLM Call begins
   └─ Token counting starts

2. Input Processing
   ├─ Count input tokens
   ├─ Get model pricing from ModelPricing table
   └─ Calculate: input_tokens / 1,000,000 * input_price_per_1m

3. Output Generation
   ├─ Count output tokens
   └─ Calculate: output_tokens / 1,000,000 * output_price_per_1m

4. Stage Total
   └─ Cost = input_cost + output_cost

5. Conversation Total
   └─ Sum all stages
```

**Data Persistence**:
```
After conversation completes:

1. Save to Conversations table
   ├─ conversation_id
   ├─ chat_id
   ├─ user_id
   ├─ org_id (if member)
   ├─ user_question
   └─ timestamp

2. Save each stage to ConversationStages
   ├─ stage_number (1, 2, 3...)
   ├─ stage_name
   ├─ model_name
   ├─ input_tokens
   ├─ output_tokens
   ├─ total_tokens
   ├─ input_cost
   ├─ output_cost
   └─ total_cost

3. Update aggregate tables
   ├─ ConversationSummary (per conversation)
   ├─ ModelUsage (per user/org)
   ├─ StagesUsage (per user/org)
   ├─ OrgModelUsage (if org)
   └─ OrgStagesUsage (if org)
```

#### Dashboard Cost Views

**Overview** (`/dashboard/costs/overview`):
- Total cost (sum of all ConversationStages)
- Total input tokens
- Total output tokens
- Total conversations

**By Model** (`/dashboard/costs/by-model`):
```
SELECT model_name,
  COUNT(*) as usage_count,
  SUM(input_tokens) as total_input,
  SUM(output_tokens) as total_output,
  SUM(total_tokens) as total_tokens,
  SUM(input_cost) as total_input_cost,
  SUM(output_cost) as total_output_cost,
  SUM(total_cost) as total_cost
FROM ConversationStages
GROUP BY model_name
ORDER BY total_cost DESC
```

**By Stage** (`/dashboard/costs/by-stage`):
```
Similar structure, grouping by stage_name
Shows which processing stages are most expensive
(typically Summary Gen > SQL Response > Email Gen)
```

**Input vs Output** (`/dashboard/costs/input-output`):
- Total input cost + percentage
- Total output cost + percentage
- Pie chart visualization
- Usually 70-30 or 80-20 split (input:output)

**Per User** (`/dashboard/costs/per-user`):
```
SELECT user_id, username,
  COUNT(DISTINCT conversation_id) as conversations_count,
  SUM(input_tokens), SUM(output_tokens), SUM(total_tokens),
  SUM(input_cost), SUM(output_cost), SUM(total_cost)
FROM Conversations c
LEFT JOIN ConversationStages cs ON c.conversation_id = cs.conversation_id
WHERE c.org_id = ?
GROUP BY c.user_id, c.username
ORDER BY total_cost DESC
```

Shows:
- Most expensive members
- Average cost per member
- Member contribution breakdown

### 5.5 Email Automation

#### Email Request Detection

**LLM Stage 3 - Email Generation** (only if needed):
```
LLM analyzes user question:
  "Send email to..." → way = "email"
  
If email requested:
  1. Extract recipient emails from question or history
  2. Generate email subject & body
  3. Return Mail object with: email[], subject, body
```

#### Email Sending Flow

**In Telegram**:
```
Bot displays two buttons:
  [Preview Email] [Send Email]

User clicks Preview:
  Shows formatted email before sending

User clicks Send:
  Email sent via Gmail SMTP
  Logged in conversation_history
  Recorded in activity_log
```

**Email Service** (`send_email.py`):
```
async def send_async(subject, body, recipients):
  ├─ Validates credentials (BOT_EMAIL, BOT_EMAIL_PASS)
  ├─ Creates MIME message
  ├─ Connects to smtp.gmail.com:465 (SSL)
  ├─ Authenticates
  ├─ Sends message
  └─ Returns success/error message
```

**Requirements**:
- Gmail account with app-specific password
- Environment variables: BOT_EMAIL, BOT_EMAIL_PASS
- Recipients extracted from request

#### Email Templates

**Default Structure**:
```
Hello

[LLM-generated content]

Best regards,
Your Company
```

Can be customized via TEMPLATE_INSTRUCTIONS in prompts.py

### 5.6 Conversation Memory & Caching

#### Memory Architecture

**Sliding Window Approach**:
```
Active memory (in-RAM):
  └─ Last 5 conversations (10 messages)
     └─ Reduces token usage & costs

Historical record (file):
  └─ Up to 1000 conversations per chat
     └─ Preserved for audit & analytics

Cache strategy:
  ├─ 5-minute TTL for history text
  ├─ Auto-refresh on new message
  └─ Reduces database queries
```

**Memory Loading**:
```
User sends message:
  1. Check in-memory cache (5 min TTL)
  2. If expired or miss: Load from file
  3. Process last 5 conversations only
  4. Cache result for 5 minutes
  5. Use for LLM context
```

#### Conversation Persistence

**Per Message Saved**:
```
{
  "timestamp": "2025-01-15 14:32:10",
  "user_id": 123456789,
  "username": "John Doe",
  "question": "What are our top products?",
  "answer": "Based on sales data...",
  "sql_query": "SELECT TOP 5 ...",
  "sql_result": "[[...], [...], ...]"
}
```

**File Storage**: `logs/conversations/chat_<id>_conversation.json`

**Cleanup**:
- File keeps last 1000 conversations
- Memory keeps last 5 conversations
- Old conversations deleted when file exceeds limit

### 5.7 Activity Logging & Audit Trail

#### What's Logged

**User Actions** (`telegram_activity.log`):
```
[2025-01-15 14:32:10] @john_doe (Chat:123456) | START_COMMAND | User started bot
[2025-01-15 14:32:15] @john_doe (Chat:123456) | QUESTION_ASKED | Question: What are...
[2025-01-15 14:32:25] @john_doe (Chat:123456) | QUESTION_ANSWERED | SQL: SELECT TOP 5...
[2025-01-15 14:32:30] @john_doe (Chat:123456) | EMAIL_SENT | Email sent to: john@example.com
[2025-01-15 14:33:00] @john_doe (Chat:123456) | DATABASE_SELECTED | Database: Company_DB
[2025-01-15 14:33:10] @john_doe (Chat:123456) | ORG_CREATED | Created org: Acme Corp
[2025-01-15 14:33:20] @john_doe (Chat:123456) | JOINED_ORG | Joined via invite: AbCd1234
[2025-01-15 14:33:25] @john_doe (Chat:123456) | MEMORY_CLEARED | User confirmed memory clear
```

**Per-Chat Activity** (`chat_<id>_activity.log`):
- Same format but for individual chat
- Useful for debugging specific user issues

#### Data Privacy

**What's NOT logged**:
- Actual SQL query results (too sensitive)
- Passwords or API keys
- Personal email addresses (except when sent via email feature)

**Data Retention**:
- Activity logs: Indefinite (compliance requirement)
- Conversation files: Last 1000 per chat
- In-memory: Last 5 conversations
- Database cost records: Indefinite

---

## 6. Business Perspective - Complete Value Proposition

### For Individual Users

**Problem**: Database complexity & SQL knowledge requirement barrier

**Solution Delivered**:
1. **Natural Language Interface** - Ask questions like "What were last month's sales?" instead of `SELECT SUM(amount)...`
2. **Instant Responses** - Get answers in seconds vs. IT ticket wait times
3. **Transparency** - See exactly what SQL was executed (for learning)
4. **Email Integration** - Automatic report generation and distribution
5. **Cost Visibility** - See how much API usage costs (educational value)

**Measurable ROI**:
- Time saved: 5-10 minutes per query average
- IT dependency: Reduced from "must request" to "self-service"
- Learning curve: Minimal (natural language)
- Cost per query: $0.001 - $0.01 (visible & controllable)

### For

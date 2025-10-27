# Telegram Bot: AI-Powered Database Query Interface

## Bot Work Flows

### small workflow
```mermaid
graph TD
    A["👤 Telegram User"] --> B{نوع الرسالة}
    
    B -->|/start| C["✅ تسجيل المستخدم"]
    B -->|/createorg| D["✨ إنشاء مؤسسة"]
    B -->|/adddb| E["➕ إضافة قاعدة بيانات"]
    B -->|/selectdb| F["🗄️ اختيار قاعدة نشطة"]
    B -->|/join| G["👥 الانضمام لمؤسسة"]
    B -->|/help, /stats| H["📖 عرض المعلومات"]
    B -->|رسالة نصية| I["🤖 معالجة السؤال"]
    
    C --> C1["إنشاء UserInfo<br/>إرسال ترحيب"]
    D --> D1["توليد org_id<br/>بيانات لوحة التحكم"]
    E --> E1["التحقق من الاتصال<br/>حفظ في قاعدة البيانات"]
    F --> F1["عرض القواعد المتاحة<br/>تعيين النشطة"]
    G --> G1["التحقق من الدعوة<br/>إضافة كعضو"]
    H --> H1["عرض الأوامر أو الإحصائيات"]
    
    I --> I1{"فحوصات"}
    I1 -->|لا قاعدة| I1A["⚠️ اختر قاعدة أولاً"]
    I1 -->|Rate Limit| I1B["⏳ انتظر"]
    I1 -->|نشط جداً| I1C["📢 طلبات معلقة"]
    I1 -->|يمر| J["🔍 المرحلة 1: التحليل<br/>Gemini 2.5-Flash"]
    
    J --> J1["تحليل السؤال<br/>توليد SQL"]
    J1 --> K{نوع الإجابة؟}
    
    K -->|SQL Query| L["⚙️ المرحلة 2: تنفيذ SQL<br/>Gemini 2.0-Flash"]
    K -->|Direct| M["إجابة مباشرة"]
    K -->|Email| N["📧 المرحلة 3: توليد إيميل<br/>Gemini 2.5-Flash"]
    
    L --> L1["تنفيذ الاستعلام<br/>تنسيق النتائج"]
    N --> N1["استخراج المستلمين<br/>إنشاء بريد احترافي"]
    
    L1 --> O["💾 حفظ في قاعدة البيانات"]
    N1 --> O
    M --> O
    
    O --> P["📊 حساب التكاليف"]
    P --> Q["🎫 عرض الإجابة"]
    Q --> R{إيميل متاح؟}
    
    R -->|نعم| R1["عرض زر الإرسال"]
    R1 --> R2{المستخدم يختار}
    R2 -->|إرسال| S["📤 إرسال عبر SMTP"]
    R2 -->|معاينة| T["👁️ عرض المعاينة"]
    R2 -->|إلغاء| U["❌ إلغاء"]
    R -->|لا| V["رسالة عادية"]
    
    S --> Z["✅ انتهى"]
    T --> U
    U --> Z
    V --> Z
    C1 --> Z
    D1 --> Z
    E1 --> Z
    F1 --> Z
    G1 --> Z
    H1 --> Z
    I1A --> Z
    I1B --> Z
    I1C --> Z
    
    style A fill:#0088cc,stroke:#005fa3,color:#fff
    style J fill:#e74c3c,stroke:#c0392b,color:#fff
    style L fill:#9b59b6,stroke:#7d3c98,color:#fff
    style N fill:#27ae60,stroke:#1e8449,color:#fff
    style O fill:#f39c12,stroke:#d68910,color:#fff
```

### To-show workflow
```mermaid
graph TD
    A["👤 Telegram User"] --> B{نوع الرسالة}
    
    %% ===== أوامر عامة =====
    B -->|/start| C["✅ تسجيل مستخدم جديد"]
    C --> C1["إنشاء UserInfo"]
    C1 --> C2["عرض رسالة ترحيب"]
    
    B -->|/help| D["📖 عرض الأوامر المتاحة"]
    D --> D1{الدور}
    D1 -->|عضو عادي| D2["أوامر محدودة"]
    D1 -->|مالك مؤسسة| D3["جميع الأوامر"]
    
    B -->|/myinfo| E["👤 معلومات المستخدم"]
    E --> E1["عرض: الدور، المؤسسة، قاعدة البيانات النشطة"]
    
    B -->|/clear| F["🗑️ حذف السجل"]
    F --> F1["تأكيد من المستخدم"]
    F1 --> F2["حذف من الذاكرة والملفات"]
    
    B -->|/history| G["📋 آخر 10 محادثات"]
    G --> G1["عرض الأسئلة السابقة"]
    
    B -->|/stats| H["📊 إحصائيات المحادثة"]
    H --> H1["عدد الأسئلة، SQL queries، التكاليف"]
    
    %% ===== أوامر المؤسسات =====
    B -->|/org| I["🏢 قائمة المؤسسة"]
    I --> I1{الدور}
    I1 -->|ليس عضواً| I2["اقتراح: /createorg أو /join"]
    I1 -->|عضو| I3["عرض معلومات المؤسسة<br/>خيارات محدودة"]
    I1 -->|مالك| I4["عرض جميع الخيارات:<br/>✓ إضافة قاعدة<br/>✓ إنشاء دعوة<br/>✓ إدارة أعضاء"]
    
    B -->|/createorg| J["✨ إنشاء مؤسسة جديدة"]
    J --> J1{تحقق: ليس في مؤسسة?}
    J1 -->|نعم| J2["توليد org_id، بيانات دخول لوحة التحكم"]
    J2 --> J3["تخزين في قاعدة البيانات"]
    J3 --> J4["إرسال بيانات الدخول للمستخدم"]
    J1 -->|لا| J5["❌ أنت بالفعل في مؤسسة"]
    
    B -->|/orginfo| K["📊 معلومات المؤسسة"]
    K --> K1["عرض: الأعضاء، قواعد البيانات، التاريخ"]
    
    B -->|/adddb| L["➕ إضافة قاعدة بيانات"]
    L --> L1{الدور}
    L1 -->|مالك مؤسسة| L2["إضافة لجميع الأعضاء"]
    L1 -->|عضو عادي| L3["إضافة شخصية فقط"]
    L1 -->|بدون مؤسسة| L4["إضافة شخصية"]
    L2 --> L5["التحقق من الاتصال"]
    L3 --> L5
    L4 --> L5
    L5 --> L6["تخزين في قاعدة البيانات"]
    
    B -->|/selectdb| M["🗄️ اختيار قاعدة البيانات"]
    M --> M1["عرض قائمة القواعس المتاحة"]
    M1 --> M2["تعيين كقاعدة نشطة"]
    
    B -->|/invite| N["🎫 إنشاء رابط دعوة"]
    N --> N1{تحقق: مالك مؤسسة?}
    N1 -->|نعم| N2["توليد رمز + وقت انتهاء"]
    N2 --> N3["تحديد عدد الاستخدامات"]
    N3 --> N4["إرسال الرابط"]
    N1 -->|لا| N5["❌ صلاحية محصورة على المالك"]
    
    B -->|/join| O["👥 الانضمام لمؤسسة"]
    O --> O1{تحقق: الرابط صحيح?}
    O1 -->|نعم| O2["توليد بيانات دخول لوحة التحكم"]
    O2 --> O3["إضافة كعضو في المؤسسة"]
    O3 --> O4["إشعار المالك"]
    O1 -->|لا| O5["❌ رابط غير صحيح أو منتهي الصلاحية"]
    
    %% ===== الأسئلة والمعالجة =====
    B -->|رسالة نصية| P{"تحقق من القيود"}
    P -->|لا قاعدة| P1["⚠️ اختر قاعدة بيانات أولاً"]
    P -->|Rate limit| P2["⏳ انتظر قبل السؤال التالي"]
    P -->|نشط جداً| P3["📢 طلبات كثيرة معلقة"]
    
    P -->|يمر| Q["🤖 معالجة السؤال"]
    Q --> Q1["المرحلة 1: تحليل السؤال<br/>Gemini 2.5-Flash"]
    Q1 --> Q2{النوع}
    
    Q2 -->|استعلام SQL| R["المرحلة 2: تنفيذ SQL<br/>Gemini 2.0-Flash"]
    Q2 -->|إجابة مباشرة| S["إرسال الإجابة"]
    Q2 -->|إيميل| T["المرحلة 3: توليد إيميل<br/>Gemini 2.5-Flash"]
    
    R --> R1["حساب التوكنات"]
    R1 --> R2["حساب التكاليف"]
    R2 --> S
    
    T --> T1["حساب التوكنات"]
    T1 --> T2["حساب التكاليف"]
    T2 --> U["عرض زر معاينة الإيميل"]
    U --> U1{اختيار المستخدم}
    U1 -->|معاينة| U2["عرض الإيميل"]
    U1 -->|إرسال| U3["إرسال عبر SMTP"]
    U1 -->|إلغاء| U4["إلغاء العملية"]
    
    S --> V["💾 حفظ في قاعدة البيانات"]
    V --> V1["جدول Conversations"]
    V2["جدول ConversationStages"]
    V3["تحديث ModelUsage"]
    V1 --> V2 --> V3
    V3 --> W["📱 إرسال الرد للمستخدم"]
    
    style C fill:#0088cc,stroke:#005fa3,color:#fff
    style J fill:#27ae60,stroke:#1e8449,color:#fff
    style N fill:#f39c12,stroke:#d68910,color:#fff
    style O fill:#9b59b6,stroke:#7d3c98,color:#fff
    style Q fill:#e74c3c,stroke:#c0392b,color:#fff
```

### For dev workflow 
```mermaid
graph TD
    A["User Sends Message"] --> B["Bot Receives Update"]
    B --> C{Message Type?}
    
    C -->|/start| D["Register/Update User"]
    C -->|Command| E["Route to Command Handler"]
    C -->|Text Message| F["Question Handler"]
    
    D --> D1["Create UserInfo<br/>Store in JSON"]
    D1 --> D2["Send Welcome Message"]
    D2 --> END1["End"]
    
    E --> E1{Which Command?}
    E1 -->|/createorg| E2["Validate User<br/>Not in Org"]
    E1 -->|/adddb| E3["Check Permissions<br/>Add Connection"]
    E1 -->|/selectdb| E4["List Available DBs<br/>Set Active"]
    E1 -->|/invite| E5["Generate Invite<br/>Code + Creds"]
    E1 -->|/join| E6["Validate Invite<br/>Add Member"]
    E1 -->|/clear| E7["Confirm Dialog"]
    E1 -->|/org, /myinfo| E8["Display Info/Menu"]
    
    E2 --> E2A["Create Org ID"]
    E2A --> E2B["Generate Dashboard Creds"]
    E2B --> E2C["Create org_owner Role"]
    E2C --> E2D["Send Credentials"]
    E2D --> END2["End"]
    
    E3 --> E3A["Check org_owner"]
    E3A --> E3B["Validate Connection"]
    E3B --> E3C["Store Connection"]
    E3C --> E3D["Notify Members"]
    E3D --> END3["End"]
    
    E7 --> E7A{User Confirms?}
    E7A -->|Yes| E7B["Delete Memory"]
    E7A -->|No| E7C["Cancel"]
    E7B --> E7D["Clear JSON Files"]
    E7D --> END4["End"]
    
    F --> F1["Check Rate Limit<br/>1 req/sec, burst 3"]
    F1 --> F2{Rate Limited?}
    F2 -->|Yes| F2A["Send Wait Message"]
    F2A --> END5["End"]
    F2 -->|No| F3["Check Active<br/>Requests ≤ 1"]
    F3 --> F3A{Max Reached?}
    F3A -->|Yes| F3B["Send Queue Message"]
    F3B --> END6["End"]
    F3A -->|No| F4["Get Database"]
    
    F4 --> F5{DB Selected?}
    F5 -->|No| F5A["Request DB Selection"]
    F5A --> END7["End"]
    F5 -->|Yes| F6["Stage 1: Analysis"]
    
    F6 --> F6A["Load Conversation<br/>History Last 5"]
    F6A --> F6B["Call Gemini 2.5-Flash<br/>Analyze Question"]
    F6B --> F6C["Generate Summary<br/>SQL Query Check"]
    F6C --> F6D["Count Tokens<br/>Calculate Cost"]
    F6D --> F7{What Method?}
    
    F7 -->|SQL Query| F8["Stage 2: Execute SQL"]
    F7 -->|Direct Answer| F9["Use Summary Answer"]
    F7 -->|Email| F10["Stage 3: Generate Email"]
    
    F8 --> F8A["Execute Query<br/>Against DB"]
    F8A --> F8B["Call Gemini 2.0-Flash<br/>Process Results"]
    F8B --> F8C["Generate Natural<br/>Language Response"]
    F8C --> F8D["Count Tokens<br/>Calculate Cost"]
    F8D --> F11["Save to Database"]
    
    F10 --> F10A["Extract Recipients<br/>from Context"]
    F10A --> F10B["Call Gemini 2.5-Flash<br/>Generate Email"]
    F10B --> F10C["Create Mail Object"]
    F10C --> F10D["Count Tokens"]
    F10D --> F11
    
    F9 --> F11["Save Conversation<br/>Update Memory"]
    F11 --> F11A["Save to JSON<br/>Background Queue"]
    F11A --> F11B["Store in SQL<br/>Conversation ID"]
    F11B --> F11C["Save Stage Data<br/>Tokens + Costs"]
    F11C --> F11D["Update Model Usage<br/>Aggregates"]
    F11D --> F12["Send Response<br/>with Buttons"]
    F12 --> F13{Has Email?}
    F13 -->|Yes| F13A["Add Email Preview<br/>Send Button"]
    F13 -->|No| F13B["Regular Response"]
    F13A --> F14["User Receives<br/>Message"]
    F13B --> F14
    F14 --> END8["End"]
    
    F14 --> F15{User Clicks<br/>Email Button?}
    F15 -->|Preview| F16["Show Email<br/>Confirmation"]
    F16 --> F17{Confirm Send?}
    F17 -->|Yes| F18["Call EmailService<br/>Send SMTP"]
    F17 -->|No| F19["Cancel"]
    F18 --> F20["Log Action"]
    F20 --> END9["End"]
    F19 --> END10["End"]
    F15 -->|No| END11["End"]
    
    style A fill:#e1f5ff
    style F6 fill:#fff3e0
    style F8 fill:#f3e5f5
    style F10 fill:#e8f5e9
    style F11 fill:#fce4ec
    style F18 fill:#e0f2f1
```

### Full workflow
```mermaid
graph TD
    Start["🚀 بدء البوت"] --> Init["تهيئة النظام<br/>تحميل LLM Services"]
    Init --> Ready["✅ البوت جاهز"]
    
    Ready --> UserMsg{نوع الرسالة؟}
    
    %% ===== الأوامر الأساسية =====
    UserMsg -->|/start| StartCmd["📝 تسجيل المستخدم"]
    StartCmd --> CreateUser["إنشاء UserInfo"]
    CreateUser --> SaveUser["💾 حفظ في telegram_users"]
    SaveUser --> Welcome["📨 إرسال رسالة ترحيب"]
    Welcome --> Ready
    
    UserMsg -->|/help| HelpCmd["📖 عرض المساعدة"]
    HelpCmd --> CheckRole{الدور؟}
    CheckRole -->|عضو عادي| LimitedHelp["أوامر محدودة"]
    CheckRole -->|مالك مؤسسة| FullHelp["جميع الأوامر"]
    LimitedHelp --> Ready
    FullHelp --> Ready
    
    UserMsg -->|/myinfo| InfoCmd["👤 معلومات المستخدم"]
    InfoCmd --> ShowInfo["عرض: الدور، المؤسسة، القاعدة النشطة"]
    ShowInfo --> Ready
    
    UserMsg -->|/clear| ClearCmd["🗑️ حذف السجل"]
    ClearCmd --> ConfirmClear{تأكيد؟}
    ConfirmClear -->|نعم| DeleteMem["حذف من الذاكرة"]
    DeleteMem --> DeleteFiles["حذف ملفات JSON"]
    DeleteFiles --> ClearDone["✅ تم الحذف"]
    ConfirmClear -->|لا| CancelClear["❌ إلغاء"]
    ClearDone --> Ready
    CancelClear --> Ready
    
    UserMsg -->|/history| HistCmd["📋 السجل"]
    HistCmd --> ShowHist["عرض آخر 10 محادثات"]
    ShowHist --> Ready
    
    UserMsg -->|/stats| StatsCmd["📊 الإحصائيات"]
    StatsCmd --> ShowStats["عدد الأسئلة، SQL، التكاليف"]
    ShowStats --> Ready
    
    %% ===== أوامر المؤسسات =====
    UserMsg -->|/createorg| CreateOrgCmd["✨ إنشاء مؤسسة"]
    CreateOrgCmd --> CheckNotInOrg{ليس في مؤسسة؟}
    CheckNotInOrg -->|لا| AlreadyInOrg["❌ أنت بالفعل في مؤسسة"]
    CheckNotInOrg -->|نعم| GenOrgID["توليد org_id"]
    GenOrgID --> GenDashCreds["🔐 توليد بيانات دخول الداشبورد"]
    GenDashCreds --> SaveOrg["💾 حفظ في organizations"]
    SaveOrg --> SaveDashUser["💾 حفظ في dashboard_users"]
    SaveDashUser --> SendCreds["📨 إرسال بيانات الدخول"]
    SendCreds --> Ready
    AlreadyInOrg --> Ready
    
    UserMsg -->|/org| OrgCmd["🏢 قائمة المؤسسة"]
    OrgCmd --> CheckOrgRole{الدور؟}
    CheckOrgRole -->|ليس عضواً| SuggestOrg["اقترح /createorg أو /join"]
    CheckOrgRole -->|عضو| ShowOrgMember["عرض معلومات محدودة"]
    CheckOrgRole -->|مالك| ShowOrgOwner["عرض جميع الخيارات"]
    SuggestOrg --> Ready
    ShowOrgMember --> Ready
    ShowOrgOwner --> Ready
    
    UserMsg -->|/orginfo| OrgInfoCmd["📊 معلومات المؤسسة"]
    OrgInfoCmd --> DisplayOrgInfo["عرض: الأعضاء، القواعد، التاريخ"]
    DisplayOrgInfo --> Ready
    
    %% ===== قواعد البيانات =====
    UserMsg -->|/adddb| AddDBCmd["➕ إضافة قاعدة بيانات"]
    AddDBCmd --> CheckDBRole{الدور؟}
    CheckDBRole -->|مالك مؤسسة| OrgDB["إضافة لجميع الأعضاء"]
    CheckDBRole -->|عضو عادي| PersonalDB["إضافة شخصية فقط"]
    CheckDBRole -->|بدون مؤسسة| IndividualDB["إضافة شخصية"]
    OrgDB --> ValidateConn["✅ التحقق من الاتصال"]
    PersonalDB --> ValidateConn
    IndividualDB --> ValidateConn
    ValidateConn --> ConnValid{صحيح؟}
    ConnValid -->|لا| ConnError["❌ اتصال غير صحيح"]
    ConnValid -->|نعم| SaveDB["💾 حفظ في database_connections"]
    SaveDB --> LinkOrgDB["💾 ربط في organization_databases"]
    LinkOrgDB --> NotifyMembers["📢 إشعار الأعضاء"]
    NotifyMembers --> Ready
    ConnError --> Ready
    
    UserMsg -->|/selectdb| SelectDBCmd["🗄️ اختيار قاعدة"]
    SelectDBCmd --> ListDBs["عرض القواعد المتاحة"]
    ListDBs --> SelectActive["تعيين القاعدة النشطة"]
    SelectActive --> UpdateCache["تحديث الكاش"]
    UpdateCache --> Ready
    
    %% ===== الدعوات =====
    UserMsg -->|/invite| InviteCmd["🎫 إنشاء دعوة"]
    InviteCmd --> CheckOwner{مالك مؤسسة؟}
    CheckOwner -->|لا| NoPermInvite["❌ صلاحية محصورة"]
    CheckOwner -->|نعم| GenInvCode["توليد رمز فريد"]
    GenInvCode --> SetExpiry["تحديد وقت الانتهاء"]
    SetExpiry --> SetMaxUses["تحديد عدد الاستخدامات"]
    SetMaxUses --> SaveInvite["💾 حفظ في invitations"]
    SaveInvite --> SendInvLink["📨 إرسال رابط الدعوة"]
    SendInvLink --> Ready
    NoPermInvite --> Ready
    
    UserMsg -->|/join| JoinCmd["👥 الانضمام لمؤسسة"]
    JoinCmd --> ValidateInv{رابط صحيح؟}
    ValidateInv -->|لا| InvError["❌ رابط غير صحيح أو منتهي"]
    ValidateInv -->|نعم| GenMemberCreds["🔐 توليد بيانات دخول"]
    GenMemberCreds --> AddMember["إضافة إلى organization_members"]
    AddMember --> UpdateInvUses["تحديث عدد الاستخدامات"]
    UpdateInvUses --> NotifyOwner["📢 إشعار المالك"]
    NotifyOwner --> SendMemberCreds["📨 إرسال بيانات الدخول"]
    SendMemberCreds --> Ready
    InvError --> Ready
    
    %% ===== معالجة الأسئلة =====
    UserMsg -->|رسالة نصية| QuestionFlow["🤖 معالجة السؤال"]
    QuestionFlow --> CheckDB{قاعدة محددة؟}
    CheckDB -->|لا| NoDBError["⚠️ اختر قاعدة أولاً"]
    NoDBError --> Ready
    
    CheckDB -->|نعم| RateLimit["⏱️ فحص Rate Limit<br/>1 طلب/ثانية"]
    RateLimit --> RateLimited{محدود؟}
    RateLimited -->|نعم| WaitMsg["⏳ انتظر قليلاً"]
    WaitMsg --> Ready
    
    RateLimited -->|لا| CheckActive["فحص الطلبات النشطة<br/>≤ 1"]
    CheckActive --> MaxReached{وصل الحد؟}
    MaxReached -->|نعم| QueueMsg["📢 طلبات كثيرة معلقة"]
    QueueMsg --> Ready
    
    %% ===== المرحلة الأولى: التحليل =====
    MaxReached -->|لا| Stage1["🔍 المرحلة 1: التحليل<br/>Gemini 2.5-Flash"]
    Stage1 --> LoadHistory["تحميل آخر 5 محادثات"]
    LoadHistory --> LoadSchema["تحميل Schema القاعدة"]
    LoadSchema --> AnalyzeQ["تحليل السؤال"]
    AnalyzeQ --> CountTokens1["حساب التوكنات"]
    CountTokens1 --> CalcCost1["حساب التكلفة"]
    CalcCost1 --> SaveStage1["💾 حفظ Stage 1<br/>في ConversationStages"]
    SaveStage1 --> DecideMethod{نوع الإجابة؟}
    
    %% ===== المرحلة الثانية: SQL =====
    DecideMethod -->|استعلام SQL| Stage2["⚙️ المرحلة 2: تنفيذ SQL"]
    Stage2 --> ExecuteSQL["تنفيذ الاستعلام"]
    ExecuteSQL --> SQLSuccess{نجح؟}
    SQLSuccess -->|لا| SQLError["❌ خطأ في SQL"]
    SQLSuccess -->|نعم| FormatResults["Gemini 2.0-Flash<br/>تنسيق النتائج"]
    FormatResults --> GenNLResponse["توليد إجابة طبيعية"]
    GenNLResponse --> CountTokens2["حساب التوكنات"]
    CountTokens2 --> CalcCost2["حساب التكلفة"]
    CalcCost2 --> SaveStage2["💾 حفظ Stage 2"]
    SaveStage2 --> SaveConv
    SQLError --> SaveConv
    
    %% ===== المرحلة الثالثة: الإيميل =====
    DecideMethod -->|توليد إيميل| Stage3["📧 المرحلة 3: الإيميل<br/>Gemini 2.5-Flash"]
    Stage3 --> ExtractRecipients["استخراج المستلمين"]
    ExtractRecipients --> GenEmail["توليد محتوى الإيميل"]
    GenEmail --> CreateMailObj["إنشاء كائن البريد"]
    CreateMailObj --> CountTokens3["حساب التوكنات"]
    CountTokens3 --> CalcCost3["حساب التكلفة"]
    CalcCost3 --> SaveStage3["💾 حفظ Stage 3"]
    SaveStage3 --> SaveConv
    
    %% ===== إجابة مباشرة =====
    DecideMethod -->|إجابة مباشرة| DirectAnswer["استخدام الملخص"]
    DirectAnswer --> SaveConv
    
    %% ===== الحفظ والإرسال =====
    SaveConv["💾 حفظ المحادثة"] --> SaveJSON["حفظ في JSON"]
    SaveJSON --> SaveSQL["💾 حفظ في Conversations"]
    SaveSQL --> UpdateUsage["تحديث ModelUsage<br/>StagesUsage<br/>OrgModelUsage"]
    UpdateUsage --> CalcTotalCost["حساب التكلفة الإجمالية"]
    CalcTotalCost --> SendResponse["📨 إرسال الرد"]
    SendResponse --> HasEmail{يحتوي على إيميل؟}
    
    HasEmail -->|نعم| ShowEmailBtns["عرض أزرار الإيميل<br/>📧 معاينة | إرسال"]
    HasEmail -->|لا| NormalMsg["رسالة عادية"]
    ShowEmailBtns --> WaitAction["انتظار فعل المستخدم"]
    NormalMsg --> Ready
    
    WaitAction --> UserAction{الفعل؟}
    UserAction -->|معاينة| PreviewEmail["عرض محتوى الإيميل"]
    PreviewEmail --> ConfirmSend{تأكيد الإرسال؟}
    ConfirmSend -->|نعم| SendSMTP["📤 إرسال عبر SMTP"]
    ConfirmSend -->|لا| CancelEmail["❌ إلغاء"]
    SendSMTP --> LogEmail["تسجيل العملية"]
    LogEmail --> Ready
    CancelEmail --> Ready
    UserAction -->|تجاهل| Ready
    
    style Start fill:#0088cc,stroke:#005fa3,color:#fff
    style Stage1 fill:#e74c3c,stroke:#c0392b,color:#fff
    style Stage2 fill:#9b59b6,stroke:#7d3c98,color:#fff
    style Stage3 fill:#27ae60,stroke:#1e8449,color:#fff
    style SaveConv fill:#f39c12,stroke:#d68910,color:#fff
    style SendResponse fill:#3498db,stroke:#2980b9,color:#fff
```

## Complete Bot Implementation Guide
---

## 1. Bot Overview

This Telegram bot enables users to query databases using natural language instead of SQL. It's built with Python, integrates with Google Gemini API for LLM capabilities, and supports both individual and organizational use cases.

### What Users Can Do

- Ask database questions in natural language
- Get instant answers with SQL queries shown transparently
- Generate and send formatted emails with query results
- Manage personal databases
- Join and use organizational databases
- Track personal usage and costs

### Key Features

- **Natural Language Queries**: Ask "What were Q4 sales?" instead of writing SQL
- **Multi-Database Support**: Add multiple databases, switch between them
- **Email Automation**: Generate professional emails from query results
- **Conversation Memory**: Maintain context across multiple messages
- **Cost Tracking**: See exactly how much each query costs
- **Team Collaboration**: Join organizations and share databases
- **Rate Limiting**: Protected from excessive/accidental requests
- **Audit Logging**: Complete activity trail for compliance

---

## 2. User Commands Reference

### Startup Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Initialize bot, show welcome message | `/start` |
| `/help` | Show all available commands with descriptions | `/help` |

### Database Management

| Command | Description | Example |
|---------|-------------|---------|
| `/adddb` | Add a new database connection | `/adddb Sales DB sql+pyodbc://server/database` |
| `/selectdb` | Choose which database to query (interactive menu) | `/selectdb` |
| `/myinfo` | Show current user profile and active database | `/myinfo` |

### Organization Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/createorg` | Create new organization (user becomes owner) | `/createorg Acme Corp` |
| `/org` | Show organization management menu | `/org` |
| `/orginfo` | View organization stats, members, databases | `/orginfo` |
| `/invite` | Create team member invitation code | `/invite 5 7` (5 uses, 7 days valid) |
| `/join` | Join organization via invitation code | `/join AbCd1234XyZ9` |

### Utility Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/stats` | Show personal usage statistics | `/stats` |
| `/history` | Show last 10 questions asked | `/history` |
| `/clear` | Clear all conversation history for current chat | `/clear` |

---

## 3. User Workflows

### Workflow 1: Personal User Setup

```
Step 1: User starts bot
  /start
    ↓
  Bot: Registers user, shows welcome + help

Step 2: Add database
  /adddb "Sales DB" "sql+pyodbc://server/database"
    ↓
  Bot: Validates connection, stores database info
    ↓
  Bot: "Database added! Use /selectdb to activate"

Step 3: Select database
  /selectdb
    ↓
  Bot: Shows list of user's databases (inline buttons)
  User: Clicks on "Sales DB"
    ↓
  Bot: "Active database: Sales DB"

Step 4: Ask question
  "What were Q4 sales?"
    ↓
  Bot: Processes through 3-stage LLM pipeline
    ↓
  Bot: Shows answer, SQL query, token cost

Step 5: Ask follow-up
  "What about Q3?"
    ↓
  Bot: Uses conversation history for context
    ↓
  Bot: Shows Q3 answer referencing Q4 for comparison
```

### Workflow 2: Organization Owner Setup

```
Step 1: Create organization
  /createorg "Acme Corp"
    ↓
  Bot: Creates organization, assigns user as owner
  Bot: Sends private message with dashboard credentials

Step 2: Add organization database (via Dashboard)
  (Owner logs into web dashboard and adds database)
    ↓
  Bot: Recognizes shared org database

Step 3: Create invitation
  /invite 5 7
    ↓
  Bot: Generates invitation code (valid for 5 uses, 7 days)
  Bot: Shows: "Share: https://app.example.com/join/AbCd1234XyZ9"

Step 4: Team member joins
  Member receives invitation link
  Member: /join AbCd1234XyZ9
    ↓
  Bot: Validates code, adds member to organization
  Bot: Sends member dashboard credentials
```

### Workflow 3: Team Member Usage

```
Step 1: Join organization
  /join <invitation_code>
    ↓
  Bot: Confirms membership, sends credentials

Step 2: View organization info
  /orginfo
    ↓
  Bot: Shows organization members, databases

Step 3: Select shared database
  /selectdb
    ↓
  Bot: Shows available databases (both personal + org)
  User: Clicks on shared "Sales DB"
    ↓
  Bot: "Active database: Sales DB (shared by Acme Corp)"

Step 4: Query organization data
  "Which products have highest profit margin?"
    ↓
  Bot: Executes query on organization's database
  Bot: Shows results with cost breakdown
```

### Workflow 4: Email Generation

```
User asks question mentioning email:
  "Send Q4 sales summary to john@example.com"
    ↓
  Stage 1: LLM analyzes → Detects email request
  Stage 2: Executes SQL query → Gets results
  Stage 3: Generates email with results
    ↓
  Bot displays email preview:
    Subject: "Q4 Sales Summary"
    To: john@example.com
    Body: [formatted results]
    ↓
  Bot shows buttons: [Preview] [Send]
    ↓
  User clicks [Send]
    ↓
  Email sent via Gmail SMTP
  Bot: "Email sent successfully!"
```

---

## 4. LLM Processing Pipeline (3 Stages)

### Stage 1: Intent Analysis & SQL Generation

**Model**: Gemini-2.5-Flash

**Input**:
- User's question
- Last 5 conversations (from memory cache)
- Database schema (table names, columns)

**Processing**:
```
LLM analyzes:
  - Is this a database query? (needs SQL)
  - Is this an email request?
  - Can I answer from history?
  - Is this general conversation?

Output:
  way: "SqlQuery" | "email" | "conversation" | "None"
  sql_query: Generated SQL (if needed)
  answer: Direct answer (if no SQL needed)
```

**Example**:
```
User: "What were last month's sales?"

LLM decides:
  way = "SqlQuery"
  sql_query = "SELECT SUM(amount) FROM sales WHERE MONTH(date)=12"
```

**Token Usage**: 200-500 tokens typical
**Cost**: $0.004-$0.008 per query

### Stage 2: SQL Execution & Response Formatting

**Model**: Gemini-2.0-Flash

**Input**:
- SQL query from Stage 1
- Original user question

**Processing**:
```
1. Connect to user's selected database
2. Execute SQL query (timeout: 30 seconds)
3. Fetch results (max 1000 rows)
4. Validate results match query intent
5. Format results as table/text
6. Pass to LLM for natural language conversion
```

**Example**:
```
SQL executed: SELECT SUM(amount) FROM sales WHERE MONTH(date)=12
Results: [(1200000,)]

LLM formats:
  "December 2024 sales total: $1,200,000
   (This is 15% higher than November)"
```

**Token Usage**: 300-600 tokens typical
**Cost**: $0.003-$0.006 per query

### Stage 3: Email Generation (Optional)

**Model**: Gemini-2.5-Flash

**Triggered**: Only if Stage 1 decides way = "email"

**Processing**:
```
1. Extract email recipients from question
2. Generate professional subject line
3. Format query results into email body
4. Create email object with all data
```

**Example**:
```
Question: "Send Q4 sales to john@company.com"

Generated:
  Subject: "Q4 2024 Sales Report"
  To: john@company.com
  Body: "John,
         Please find the Q4 sales summary below:
         [formatted results]"
```

**Token Usage**: 150-400 tokens typical
**Cost**: $0.003-$0.005 per query

---

## 5. Cost Tracking in Bot

### How Costs Are Calculated

```
Per Query:
  1. Count input tokens (question + context)
  2. Count output tokens (LLM response)
  3. Look up model pricing from database
  4. Calculate: (tokens / 1,000,000) * price_per_million

Example:
  Stage 1: 342 input + 903 output tokens
    Input: (342 / 1,000,000) * $0.075 = $0.0000256
    Output: (903 / 1,000,000) * $0.3 = $0.0002709
    Total: $0.0003
```
### Personal Statistics

User can check stats anytime:
```
/stats
  ↓
  Bot displays:
    • Total questions: 5 
    • Total queries: 3
    • First message: 20-10-2025 19:30:56
    • Last message: 25-10-2025 10:00:51
```

---

## 6. Conversation Memory System

### How Memory Works

**Goal**: Keep context while minimizing token usage (and cost)

**Memory Levels**:

```
Level 1: Active Memory (RAM)
  ├─ Stores: Last 5 conversations
  ├─ TTL: 5 minutes
  ├─ Used for: LLM context
  └─ Benefit: 70% token reduction vs unlimited history

Level 2: File Storage
  ├─ Stores: Last 1,000 conversations per chat
  ├─ Format: JSON
  ├─ Used for: /history command, audit trail
  └─ Benefit: Full history preserved

Level 3: Database
  ├─ Stores: Conversation summaries + costs
  ├─ Used for: Analytics, /stats command
  └─ Benefit: Cost reporting
```

### Example Memory File

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
  }
]
```

### Memory Benefits

- **Cost Reduction**: 70% fewer tokens = 70% cost reduction
- **Context Maintained**: Bot understands "What about Q3?" (references Q4 context)
- **Audit Trail**: Full history for compliance
- **Smart Cleanup**: Auto-deletes oldest when > 1,000 conversations

---

## 7. Rate Limiting & Concurrency Control

### Rate Limiter (Token Bucket Algorithm)

**Purpose**: Prevent server overload and runaway costs

**Configuration**:
```
Sustainable rate: 1 request per second
Burst capacity: 3 requests
```

**How It Works**:

```
Scenario 1: Normal usage
  T=0s: User sends Q1 ✓ (tokens: 3 → 2)
  T=0.5s: User sends Q2 ✓ (tokens: 2 → 1)
  T=1s: User sends Q3 ✓ (tokens: 1 → 0, refill to 1)
  T=1.5s: User sends Q4 ✓ (tokens: 1 → 0)
  Result: All questions answered

Scenario 2: Rapid burst
  T=0s: Q1, Q2, Q3 sent ✓ (uses all 3 burst tokens)
  T=0.1s: Q4 sent ✗ (rate limited, must wait)
  T=1.0s: Q4 retried ✓ (bucket refilled)
  Result: User protected from accidental burst
```

**User Experience**:
```
User sends 4 questions too fast
  Bot: "Please wait 0.9 seconds before next question"
  After 1 second: Question accepted
```

### Concurrency Control

**Limit**: 1 active LLM request per user

**Behavior**:
```
User sends Q1 (LLM processing for 5 seconds)
  ↓
User sends Q2 immediately
  ↓
Bot: "Waiting for your previous answer to complete..."
  ↓
Q1 completes (2 seconds later)
  ↓
Q2 begins processing
```

**Benefits**:
- Prevents database queue explosion
- Avoids accidental double-processing
- Prevents token cost explosion
- Keeps database connection pooling efficient

---

## 8. Email Service

### When Emails Are Generated

Bot detects email-related keywords in user question:
- "send email"
- "send report"
- "notify"
- "forward"
- "distribute"
- "mail to"

### Email Generation Process

```
User: "Send Q4 sales report to john@company.com and sarah@ops.com"
  ↓
Stage 3 LLM processes:
  1. Extracts recipients: [john@company.com, sarah@ops.com]
  2. Generates subject: "Q4 2024 Sales Report"
  3. Formats body with query results
  ↓
Bot displays preview:
  ┌─────────────────────────────────┐
  │ To: john@company.com, sarah@... │
  │ Subject: Q4 2024 Sales Report   │
  │                                 │
  │ Body:                           │
  │ Dear Recipients,                │
  │ [formatted results]             │
  │                                 │
  │ Best regards,                   │
  │ Company Bot                     │
  └─────────────────────────────────┘

  [Preview Email] [Send Email]
  ↓
User clicks [Send Email]
  ↓
Email sent via Gmail SMTP (async)
Bot: "Email sent successfully!"
  ↓
Email logged in:
  • Activity log
  • Conversation history
  • Cost database
```

### Email Configuration

```
SMTP Server: smtp.gmail.com:465 (SSL/TLS)
Authentication: Gmail app-specific password
Sender: BOT_EMAIL (from environment variable)
Rate Limit: Gmail 300 per minute
```

### Email Template

```
Hello {{recipient_first_name}},

{{query_results_formatted}}

Best regards,
{{signature}}
```

---

## 9. Logging & Activity Trail

### What Bot Logs

**Events Logged**:
- User registration (/start)
- Commands executed (/adddb, /selectdb, /createorg, etc.)
- Questions asked (full text)
- SQL queries (text only, not results)
- Query results (if not sensitive)
- Emails sent (recipient, subject)
- Database selected/changed
- Organization actions (create, join, member added)
- Errors and exceptions (with stack trace)
- Rate limit events
- Memory cleared

**Log Format**:
```
[2025-01-15 14:32:10] user_123 (chat_456) | EVENT_TYPE | Details

Example entries:
[2025-01-15 14:32:10] user_123 (chat_456) | /start | User registered
[2025-01-15 14:32:15] user_123 (chat_456) | QUESTION_ASKED | "What are sales?"
[2025-01-15 14:32:20] user_123 (chat_456) | QUESTION_ANSWERED | Cost: $0.0084
[2025-01-15 14:32:25] user_123 (chat_456) | EMAIL_SENT | To: john@example.com
[2025-01-15 14:32:30] user_123 (chat_456) | /selectdb | Sales DB activated
```

### Log Files Location

```
logs/
  ├── bot.log
  │   └─ Application startup, initialization, errors
  │
  ├── telegram_activity.log
  │   └─ Global user action audit trail
  │
  ├── chat_<chat_id>_activity.log
  │   └─ Per-chat activity (one file per conversation)
  │
  └── conversations/
      └── chat_<chat_id>_conversation.json
          └─ Full conversation history (up to 1,000 entries)
```

### Data Retention

- Activity logs: Indefinite (for compliance)
- Conversation files: Last 1,000 per chat
- In-memory cache: Last 5 conversations (5-min TTL)
- Sensitive data: NOT logged (passwords, API keys)

---

## 10. Database Connections

### Adding Databases

**Personal Database**:
```
/adddb "Sales DB" "sql+pyodbc://server/database"
  ↓
Bot validates connection works
  ↓
Stores in database_connections table:
  - connection_id (unique)
  - name: "Sales DB"
  - connection_string
  - owner_type: "user"
  - owner_id: user_id
  - is_active: 1
```

**Connection String Format**:
```
sql+pyodbc://username:password@server/database?driver=ODBC+Driver+17

Example:
sql+pyodbc://admin:pass123@db.company.com/sales?driver=ODBC+Driver+17
```

### Switching Databases

```
/selectdb
  ↓
Bot shows list (inline buttons):
  [Sales DB] [Inventory DB] [HR DB]
  ↓
User clicks database
  ↓
Bot sets as active:
  "Active database: Sales DB"
```

### Access Verification

Before every query:
```
1. Retrieve user's current_database_id
2. Check database exists and is_active
3. Verify user owns it (personal) or is org member (org)
4. Validate connection works
5. GRANT access → Execute query
6. DENY → Show error message
```

### Connection Pooling

- Connections cached in memory
- Timeout-based invalidation: 30 minutes
- Health check: SELECT 1 before reuse
- Max concurrent: 10 per user
- Auto-cleanup on member removal

---

## 11. Organization Features

### Creating Organization

```
/createorg "Acme Corp"
  ↓
Bot creates:
  1. organizations record
  2. organization_members (owner entry)
  3. dashboard_users (owner credentials)
  ↓
Bot sends private message:
  "Organization created! You're the owner.
   
   Dashboard credentials:
   Username: owner_acme_abc123
   Password: xK9mP2qL8nR5vBtY
   
   Share invitation codes with team members
   using: /invite [uses] [days]"
```

### Creating Invitations

```
/invite 5 7
  ↓
Creates invitation record:
  - invite_code: "AbCd1234XyZ9" (12-char URL-safe)
  - org_id
  - created_by: owner_id
  - max_uses: 5
  - expires_at: now + 7 days
  - is_active: 1
  ↓
Bot displays:
  "Invitation created!
   Code: AbCd1234XyZ9
   Uses remaining: 5/5
   Expires: 2025-01-22 (7 days)
   
   Share: https://app.example.com/join/AbCd1234XyZ9"
```

### Joining Organization

```
/join AbCd1234XyZ9
  ↓
Bot validates:
  - Code exists
  - Not expired
  - Uses not exhausted
  - User not already in org
  ↓
If valid, bot creates:
  1. organization_members record
  2. dashboard_users record (member credentials)
  3. invitation_usage_logs (audit entry)
  ↓
Bot increments current_uses
If reached max_uses: is_active = 0
  ↓
Bot sends:
  "Welcome to Acme Corp!
   
   Dashboard credentials:
   Username: member_acme_user456
   Password: mN3xY9kL2qR8vBtP
   
   Use /selectdb to access shared databases"
```

### Viewing Organization Info

```
/orginfo
  ↓
Bot displays:
  ┌──────────────────────────────┐
  │ {ORG_NAME}                   │
  │ ID:'ORG_2025101920525_djw29v'│
  │ Created: 2025-01-15          │
  │ Owner: John Smith            │
  │ Your role: member            │
  │                              │
  │ Members:                     │
  │ • John Smith                 │
  │ • Sarah Davis                │
  │ • Mike Johnson               │
  │ • Emma Wilson                │
  │ • You                        │
  │                              │
  │ Databases:                   │
  │ • Sales DB                   │
  │ • Inventory DB               │
  │ • HR DB                      │
  └──────────────────────────────┘
```

---

## 12. User Profile Management

### User Profile Info

```
/myinfo
  ↓
Bot displays:
  ┌──────────────────────────────┐
  │ Profile                      │
  │ ─────────────────────────    │
  │ Name: John Smith             │
  │ Telegram ID: 123456789       │
  │ Role: org_member             │
  │ Joined: 2025-01-10           │
  │                              │
  │ Organization:                │
  │ • Name: Acme Corp            │
  │ • Joined: 2025-01-15         │
  │                              │
  │ Current Database:            │
  │ • Sales DB (org)             │
  │                              │
  │ Personal Stats:              │
  │ • Queries today: 12          │
  │ • Queries this week: 45      │
  │ • Cost today: $0.45          │
  │ • Cost this week: $1.23      │
  └──────────────────────────────┘
```

---

## 13. Query History

### Viewing History

```
/history
  ↓
Bot displays last 10 queries:
  1. "What were Q4 sales?"
  2. "What about Q3?"
  3. "Top 5 products?"
  4. "Revenue by region?" 
  5. "Send summary to john" 
  ...
```

---

## 14. Clearing History

### Memory Clear Command

```
/clear
  ↓
Bot asks for confirmation:
  "Are you sure you want to clear conversation history?
   This cannot be undone.
   
   [Yes, clear] [Cancel]"
  ↓
If user confirms:
  - Clears in-memory cache
  - Preserves conversation file (for audit)
  - Confirms: "Conversation history cleared"
  ↓
If user cancels:
  - Does nothing
```

---

## 15. Help & Documentation

### Help Command

```
/help
  ↓
Bot displays comprehensive guide:
  
  "TELEGRAM BOT COMMANDS
   ═════════════════════
   
   Getting Started:
   • /start - Initialize bot
   • /help - Show this help
   • /myinfo - Show your profile
   
   Databases:
   • /adddb <name> <connection> - Add database
   • /selectdb - Choose active database
   • /history - View last 10 queries
   • /stats - View usage statistics
   
   Organizations:
   • /createorg <name> - Create organization
   • /org - Org management menu
   • /orginfo - Org statistics
   • /invite [uses] [days] - Create invitation
   • /join <code> - Join organization
   
   Utilities:
   • /clear - Clear conversation history
   
   USAGE EXAMPLES:
   ═════════════════
   
   Query a database:
   → 'What were last month sales?'
   
   Generate email:
   → 'Send Q4 report to john@company.com'
   
   Reference history:
   → 'What about the previous quarter?'
   
   NEED HELP?
   ══════════
   Visit: /help or contact support"
```

---

## 16. Error Handling

### Common Errors & Messages

**Connection Failed**:
```
Bot: "❌ Failed to connect to database
     Please check:
     • Connection string is correct
     • Server is accessible
     • Credentials are valid
     
     Use /adddb to update or retry"
```

**Rate Limited**:
```
Bot: "⏱️ Rate limit reached
     Please wait 0.5 seconds before next query"
```

**Query Timeout**:
```
Bot: "⏱️ Query timeout (> 30 seconds)
     The database is busy or query too complex
     Try asking a simpler question or try later"
```

**No Results**:
```
Bot: "📭 No data matches your query
     Try rephrasing your question or check:
     • Correct database selected
     • Date ranges are valid
     • Data actually exists"
```

**SQL Error**:
```
Bot: "❌ SQL query failed
     Error: [specific error message]
     
     This might be a database issue
     Try a different question"
```

---

## 17. Project Structure (Bot Only)

```
bot-services/
├── main_telegram.py              # Bot entry point
│
├── services/
│   ├── telegram_service.py       # Command handlers
│   ├── telegram_llm_service.py   # LLM orchestration
│   ├── telegram_auth.py          # User auth
│   ├── telegram_logging.py       # Logging
│   ├── database_manager.py       # DB connections
│   ├── organization_manager.py   # Org management
│   ├── send_email.py             # Email service
│   ├── sql_service.py            # SQL execution
│   └── token_cost_calculator.py  # Cost tracking
│
├── models/
│   └── pydantic_models.py        # Data validation
│
├── memory/
│   └── telegram_conversation.py  # Caching
│
├── utils/
│   └── prompts.py                # LLM templates
│
├── logs/
│   ├── bot.log
│   ├── telegram_activity.log
│   └── conversations/
│
└── requirements.txt
```

---

## 18. Key Services Explained

### telegram_service.py
Handles all bot commands and user interactions:
- `/start`, `/help`, `/adddb`, `/selectdb`
- `/createorg`, `/invite`, `/join`
- `/org`, `/orginfo`, `/stats`, `/history`
- `/clear`, `/myinfo`
- Button callbacks and message handling

### telegram_llm_service.py
Orchestrates the 3-stage LLM pipeline:
- Stage 1: Summary generation (intent + SQL)
- Stage 2: SQL execution + response formatting
- Stage 3: Email generation (if needed)
- Token counting and cost calculation

### telegram_auth.py
Manages user authentication:
- User registration on `/start`
- Role assignment and management
- Profile storage
- Permission checking

### telegram_logging.py
Comprehensive audit logging:
- User actions logged
- Conversation history saved
- Statistics tracked
- File-based persistence

### database_manager.py
Manages database connections:
- Personal database management
- Organization database access
- Connection pooling
- Health checks
- Access verification

### organization_manager.py
Team and organization management:
- Create organizations
- Manage memberships
- Generate invitations
- Track member activities
- Verify permissions

### send_email.py
Email service integration:
- Generate emails from results
- SMTP configuration
- Async sending
- Error handling

### sql_service.py
SQL query execution:
- Connect to database
- Execute queries safely
- Result validation
- Error handling
- Result caching

### token_cost_calculator.py
Cost tracking system:
- Count tokens (input/output)
- Calculate costs per stage
- Store in analytics DB
- Aggregate statistics

---

## 19. Technology Stack (Bot Only)

**Language**: Python 3.9+

**Core Libraries**:
- `python-telegram-bot`: Telegram API wrapper
- `langchain-community`: LLM orchestration
- `langchain-google-genai`: Google Gemini API
- `sqlalchemy`: Database ORM
- `pyodbc`: SQL Server driver
- `aiofiles`: Async file operations

**External Services**:
- Google Gemini API (LLM)
- Gmail SMTP (email)
- SQL Server (data)
- Telegram Bot API

---

## 20. Performance Metrics

### Response Times
- Query processing: 2-5 seconds average
- Email generation: 1-2 seconds
- Database connection: <500ms

### Token Usage
- Per query: 500-3,000 tokens typical
- Input vs output: 30% input, 70% output typical

### Cost Metrics
- Per query: $0.001-$0.02 typical
- Bulk discount: Prices per 1M tokens (very cheap)
- Memory optimization: 70% cost reduction vs unlimited history

### Reliability
- Uptime target: 99.5% (production)
- Timeout protection: 30-second query limit
- Rate limiting: 1 req/sec, burst 3
- Concurrency: 1 active per user

---

## 21. Security Considerations

**Authentication**:
- Telegram user_id as primary identifier
- No additional password needed for bot
- Session tokens auto-generated for dashboard

**Authorization**:
- Role-based access control (RBAC)
- Per-user database access verification
- Organization isolation

**Data Protection**:
- HTTPS/TLS for all communications
- Connection strings stored encrypted (production)
- Sensitive data not logged
- SQL queries logged (not results by default)

**Audit Trail**:
- Complete activity logging
- Timestamped events
- User attribution
- Compliance-ready

---

## Summary

The Telegram bot is a complete AI-powered database query interface that enables users to:
- Query databases without SQL knowledge
- Collaborate in organizations
- Generate and send automated emails
- Track personal costs and usage
- Maintain full conversation context

Key strengths:
- Natural language interface
- Complete transparency (users see generated SQL)
- Cost tracking and awareness
- Team collaboration capabilities
- Enterprise audit logging32:10",
    "question": "What were Q4 sales?",
    "answer": "Q4 2024 sales were $1.2M",
    "sql_query": "SELECT SUM(amount) FROM sales WHERE year=2024 AND quarter=4",
    "tokens": 1245,
    "cost": 0.00847
  },
  {
    "timestamp": "2025-01-15 14:

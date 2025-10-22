# /dashboard/routes.py

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from services.organization_manager import get_organization_manager
from services.database_manager import get_database_manager
from dashboard.auth import create_session, get_session, delete_session
from dashboard.utils import get_session_from_headers
from db_connection import get_db_session
from sqlalchemy import text

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
org_manager = get_organization_manager()
db_manager = get_database_manager()

# إضافة هذه الـ Routes إلى routes.py الموجود

# = COSTS / BILLING =

@router.get("/costs/overview")
async def get_costs_overview(authorization: Optional[str] = Header(None)):
    """الحصول على نظرة عامة على تكاليف المؤسسة"""
    
    token = get_session_from_headers(authorization)
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    # استخدام الاتصال الثاني (costs database)
    from db_connection import SessionLocal_2
    db = SessionLocal_2()
    
    try:
        # التكاليف الكلية
        total_result = db.execute(text("""
            SELECT 
                COALESCE(SUM(total_cost), 0) as total_cost,
                COALESCE(SUM(input_tokens), 0) as total_input,
                COALESCE(SUM(output_tokens), 0) as total_output,
                COUNT(DISTINCT conversation_id) as total_conversations
            FROM ConversationStages
            WHERE conversation_id IN (
                SELECT conversation_id FROM Conversations 
                WHERE org_id = :org_id
            )
        """), {'org_id': session['org_id']})
        
        total_row = total_result.fetchone()
        total_stats = {
            'total_cost': float(total_row[0] or 0),
            'total_input_tokens': int(total_row[1] or 0),
            'total_output_tokens': int(total_row[2] or 0),
            'total_conversations': int(total_row[3] or 0)
        }
        
        return {
            "success": True,
            "total_stats": total_stats
        }
    
    except Exception as e:
        print(f"❌ خطأ في جلب بيانات التكاليف: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/costs/by-model")
async def get_costs_by_model(authorization: Optional[str] = Header(None)):
    """التكاليف حسب النموذج"""
    
    token = get_session_from_headers(authorization)
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    from db_connection import SessionLocal_2
    db = SessionLocal_2()
    
    try:
        result = db.execute(text("""
            SELECT 
                cs.model_name,
                COUNT(*) as usage_count,
                COALESCE(SUM(cs.input_tokens), 0) as total_input,
                COALESCE(SUM(cs.output_tokens), 0) as total_output,
                COALESCE(SUM(cs.total_tokens), 0) as total_tokens,
                COALESCE(SUM(cs.input_cost), 0) as total_input_cost,
                COALESCE(SUM(cs.output_cost), 0) as total_output_cost,
                COALESCE(SUM(cs.total_cost), 0) as total_cost
            FROM ConversationStages cs
            INNER JOIN Conversations c ON cs.conversation_id = c.conversation_id
            WHERE c.org_id = :org_id
            GROUP BY cs.model_name
            ORDER BY total_cost DESC
        """), {'org_id': session['org_id']})
        
        models = []
        for row in result:
            models.append({
                'model_name': row[0],
                'usage_count': int(row[1]),
                'total_input_tokens': int(row[2]),
                'total_output_tokens': int(row[3]),
                'total_tokens': int(row[4]),
                'total_input_cost': float(row[5]),
                'total_output_cost': float(row[6]),
                'total_cost': float(row[7])
            })
        
        return {
            "success": True,
            "models": models
        }
    
    except Exception as e:
        print(f"❌ خطأ في جلب تكاليف النماذج: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/costs/by-stage")
async def get_costs_by_stage(authorization: Optional[str] = Header(None)):
    """التكاليف حسب المرحلة"""
    
    token = get_session_from_headers(authorization)
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    from db_connection import SessionLocal_2
    db = SessionLocal_2()
    
    try:
        result = db.execute(text("""
            SELECT 
                cs.stage_name,
                COUNT(*) as usage_count,
                COALESCE(SUM(cs.input_tokens), 0) as total_input,
                COALESCE(SUM(cs.output_tokens), 0) as total_output,
                COALESCE(SUM(cs.total_tokens), 0) as total_tokens,
                COALESCE(SUM(cs.input_cost), 0) as total_input_cost,
                COALESCE(SUM(cs.output_cost), 0) as total_output_cost,
                COALESCE(SUM(cs.total_cost), 0) as total_cost
            FROM ConversationStages cs
            INNER JOIN Conversations c ON cs.conversation_id = c.conversation_id
            WHERE c.org_id = :org_id
            GROUP BY cs.stage_name
            ORDER BY total_cost DESC
        """), {'org_id': session['org_id']})
        
        stages = []
        for row in result:
            stages.append({
                'stage_name': row[0],
                'usage_count': int(row[1]),
                'total_input_tokens': int(row[2]),
                'total_output_tokens': int(row[3]),
                'total_tokens': int(row[4]),
                'total_input_cost': float(row[5]),
                'total_output_cost': float(row[6]),
                'total_cost': float(row[7])
            })
        
        return {
            "success": True,
            "stages": stages
        }
    
    except Exception as e:
        print(f"❌ خطأ في جلب تكاليف المراحل: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/costs/input-output")
async def get_costs_input_output(authorization: Optional[str] = Header(None)):
    """تكاليف المدخلات والمخرجات"""
    
    token = get_session_from_headers(authorization)
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    from db_connection import SessionLocal_2
    db = SessionLocal_2()
    
    try:
        result = db.execute(text("""
            SELECT 
                COALESCE(SUM(cs.input_cost), 0) as total_input_cost,
                COALESCE(SUM(cs.output_cost), 0) as total_output_cost,
                COALESCE(SUM(cs.total_cost), 0) as total_cost
            FROM ConversationStages cs
            INNER JOIN Conversations c ON cs.conversation_id = c.conversation_id
            WHERE c.org_id = :org_id
        """), {'org_id': session['org_id']})
        
        row = result.fetchone()
        
        return {
            "success": True,
            "input_cost": float(row[0] or 0),
            "output_cost": float(row[1] or 0),
            "total_cost": float(row[2] or 0),
            "input_percentage": (float(row[0] or 0) / float(row[2] or 1)) * 100,
            "output_percentage": (float(row[1] or 0) / float(row[2] or 1)) * 100
        }
    
    except Exception as e:
        print(f"❌ خطأ في جلب تكاليف المدخلات والمخرجات: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/costs/per-user")
async def get_costs_per_user(authorization: Optional[str] = Header(None)):
    """متوسط التكاليف لكل مستخدم"""
    
    token = get_session_from_headers(authorization)
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    from db_connection import SessionLocal_2
    db = SessionLocal_2()
    
    try:
        result = db.execute(text("""
            SELECT 
                c.user_id,
                c.username,
                COUNT(DISTINCT c.conversation_id) as conversations_count,
                COALESCE(SUM(cs.input_tokens), 0) as total_input,
                COALESCE(SUM(cs.output_tokens), 0) as total_output,
                COALESCE(SUM(cs.total_tokens), 0) as total_tokens,
                COALESCE(SUM(cs.input_cost), 0) as total_input_cost,
                COALESCE(SUM(cs.output_cost), 0) as total_output_cost,
                COALESCE(SUM(cs.total_cost), 0) as total_cost
            FROM Conversations c
            LEFT JOIN ConversationStages cs ON c.conversation_id = cs.conversation_id
            WHERE c.org_id = :org_id
            GROUP BY c.user_id, c.username
            ORDER BY total_cost DESC
        """), {'org_id': session['org_id']})
        
        users = []
        total_org_cost = 0
        total_users = 0
        
        for row in result:
            user_cost = float(row[8] or 0)
            total_org_cost += user_cost
            total_users += 1
            
            users.append({
                'user_id': row[0],
                'username': row[1],
                'conversations_count': int(row[2]),
                'total_input_tokens': int(row[3]),
                'total_output_tokens': int(row[4]),
                'total_tokens': int(row[5]),
                'total_input_cost': float(row[6]),
                'total_output_cost': float(row[7]),
                'total_cost': user_cost
            })
        
        average_cost = total_org_cost / total_users if total_users > 0 else 0
        
        return {
            "success": True,
            "users": users,
            "total_org_cost": total_org_cost,
            "average_cost_per_user": average_cost,
            "total_users": total_users
        }
    
    except Exception as e:
        print(f"❌ خطأ في جلب تكاليف المستخدمين: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# = MODELS =

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    success: bool
    message: str
    token: str = None
    role: str = None
    org_id: str = None
    org_name: str = None
    user_id: int = None


class AddMemberRequest(BaseModel):
    user_id: int


class RemoveMemberRequest(BaseModel):
    user_id: int

class CreateDatabaseRequest(BaseModel):
    name: str
    connection_string: str  # ✅ لإنشاء قاعدة جديدة


class RemoveDatabaseRequest(BaseModel):
    connection_id: str


class CreateInvitationRequest(BaseModel):
    max_uses: int = 1


# = AUTHENTICATION =

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """تسجيل الدخول"""
    
    if not request.username or not request.password:
        return LoginResponse(
            success=False,
            message="يجب ملء جميع الحقول"
        )
    
    # البحث عن المستخدم
    user_data = await org_manager.authenticate_dashboard_user(
        request.username,
        request.password
    )
    
    if not user_data:
        return LoginResponse(
            success=False,
            message="بيانات الدخول غير صحيحة"
        )
    
    # إنشاء جلسة
    token = create_session(
        org_id=user_data['org_id'],
        user_id=user_data['user_id'],
        role=user_data['role'],
        org_name=user_data['org_name'],
        username=user_data['username']
    )
    
    print(f"✅ تم إنشاء التوكن: {token}")
    print(f"👤 الدور: {user_data['role']}")
    
    return LoginResponse(
        success=True,
        message="تم تسجيل الدخول بنجاح",
        token=token,
        role=user_data['role'],
        org_id=user_data['org_id'],
        org_name=user_data['org_name'],
        user_id=user_data['user_id']
    )


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """تسجيل الخروج"""
    token = get_session_from_headers(authorization)
    
    if token:
        delete_session(token)
    
    return {
        "success": True,
        "message": "تم تسجيل الخروج بنجاح"
    }


@router.get("/verify")
async def verify_session(authorization: Optional[str] = Header(None)):
    """التحقق من الجلسة"""
    token = get_session_from_headers(authorization)
    
    if not token:
        raise HTTPException(status_code=401, detail="لا توجد جلسة")
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="جلسة غير صحيحة")
    
    return {
        "valid": True,
        "role": session['role'],
        "org_id": session['org_id'],
        "username": session['username']
    }


# = OVERVIEW =

@router.get("/overview")
async def get_overview(authorization: Optional[str] = Header(None)):
    """الحصول على بيانات الداش بورد"""
    
    token = get_session_from_headers(authorization)
    
    if not token:
        raise HTTPException(status_code=401, detail="لا توجد جلسة")
    
    session = get_session(token)
    
    if not session:
        raise HTTPException(status_code=401, detail="جلسة غير صحيحة")
    
    # الحصول على بيانات المؤسسة
    org = await org_manager.get_organization(session['org_id'])
    stats = await org_manager.get_organization_statistics(session['org_id'])
    
    if not org:
        raise HTTPException(status_code=404, detail="المؤسسة غير موجودة")
    
    return {
        "org": {
            "id": org.org_id,
            "name": org.name,
            "description": org.description,
            "created_at": org.created_at
        },
        "stats": stats,
        "user": {
            "role": session['role'],
            "username": session['username'],
            "user_id": session['user_id']
        },
        "permissions": {
            "is_owner": session['role'] == 'owner',
            "is_member": session['role'] == 'member'
        }
    }


# = MEMBERS =

@router.get("/members")
async def get_members(authorization: Optional[str] = Header(None)):
    """الحصول على الأعضاء - الكل يرى"""
    token = get_session_from_headers(authorization)
    
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    members = await org_manager.get_organization_members_with_roles(session['org_id'])
    
    return {
        "members": [m.to_dict() for m in members],
        "can_manage": session['role'] == 'owner',
        "is_owner": session['role'] == 'owner'
    }


@router.post("/members/add")
async def add_member(request: AddMemberRequest, authorization: Optional[str] = Header(None)):
    """إضافة عضو - Owner فقط"""
    token = get_session_from_headers(authorization)
    
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    # فحص الصلاحية - Owner فقط
    if session['role'] != 'owner':
        raise HTTPException(
            status_code=403, 
            detail="فقط مالك المؤسسة يمكنه إضافة أعضاء"
        )
    
    success = await org_manager.add_member_directly(
        org_id=session['org_id'],
        owner_id=session['user_id'],
        member_id=request.user_id,
        role='member'
    )
    
    if success:
        return {
            "success": True,
            "message": "تم إضافة العضو بنجاح"
        }
    else:
        return {
            "success": False,
            "message": "فشل إضافة العضو"
        }


@router.post("/members/remove")
async def remove_member(request: RemoveMemberRequest, authorization: Optional[str] = Header(None)):
    """حذف عضو - Owner فقط"""
    token = get_session_from_headers(authorization)
    
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    # فحص الصلاحية - Owner فقط
    if session['role'] != 'owner':
        raise HTTPException(
            status_code=403, 
            detail="فقط مالك المؤسسة يمكنه حذف أعضاء"
        )
    
    success = await org_manager.remove_member(
        org_id=session['org_id'],
        owner_id=session['user_id'],
        member_id=request.user_id
    )
    
    return {
        "success": success,
        "message": "تم الحذف بنجاح" if success else "فشل الحذف"
    }


# = DATABASES =

@router.get("/databases")
async def get_databases(authorization: Optional[str] = Header(None)):
    """الحصول على قواعد البيانات الحالية - الكل يرى"""
    token = get_session_from_headers(authorization)
    
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    # ✅ جلب قواعد البيانات من خلال organization_databases
    db = get_db_session()
    try:
        result = db.execute(text("""
            SELECT 
                dc.connection_id,
                dc.name,
                dc.created_at,
                dc.is_active,
                dc.owner_type,
                od.added_at
            FROM database_connections dc
            INNER JOIN organization_databases od 
                ON dc.connection_id = od.connection_id
            WHERE od.org_id = :org_id AND dc.is_active = 1
            ORDER BY od.added_at DESC
        """), {'org_id': session['org_id']})
        
        databases = []
        for row in result:
            databases.append({
                'connection_id': row[0],
                'name': row[1],
                'created_at': row[2].isoformat() if row[2] else None,
                'is_active': bool(row[3]),
                'owner_type': row[4],
                'added_at': row[5].isoformat() if row[5] else None
            })
        
        return {
            "databases": databases,
            "count": len(databases),
            "can_manage": session['role'] == 'owner',
            "is_owner": session['role'] == 'owner',
            "is_member": session['role'] == 'member'
        }
    except Exception as e:
        print(f"❌ خطأ في جلب قواعد البيانات: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/databases/create")
async def create_database(request: CreateDatabaseRequest, authorization: Optional[str] = Header(None)):
    """
    إنشاء قاعدة بيانات جديدة وإضافتها للمؤسسة مباشرة - Owner فقط
    """
    token = get_session_from_headers(authorization)
    
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    # فحص الصلاحية - Owner فقط
    if session['role'] != 'owner':
        raise HTTPException(
            status_code=403, 
            detail="فقط مالك المؤسسة يمكنه إنشاء قواعد بيانات"
        )
    
    print(f"🔧 محاولة إنشاء قاعدة بيانات: {request.name}")
    print(f"   Connection String: {request.connection_string[:50]}...")
    
    # ✅ إنشاء قاعدة البيانات (ستُضاف تلقائياً في organization_databases)
    connection = await db_manager.add_connection(
        name=request.name,
        connection_string=request.connection_string,
        created_by=session['user_id'],
        owner_type="organization",
        owner_id=session['org_id']
    )
    db = get_db_session()
    db.execute(text("""
        INSERT INTO organization_databases (org_id, connection_id, added_at)
        VALUES (:org_id, :connection_id, :added_at)
    """), {
        'org_id': session['org_id'],
        'connection_id': connection.connection_id,
        'added_at': datetime.now()
    })
    db.commit()
    if connection:
        print(f"✅ تم إنشاء قاعدة البيانات: {connection.connection_id}")
        return {
            "success": True,
            "message": f"تم إنشاء قاعدة البيانات '{request.name}' بنجاح",
            "connection_id": connection.connection_id,
            "name": connection.name
        }
    else:
        print(f"❌ فشل إنشاء قاعدة البيانات")
        raise HTTPException(
            status_code=500,
            detail="فشل إنشاء قاعدة البيانات. تحقق من connection_string"
        )

@router.post("/databases/remove")
async def remove_database(request: RemoveDatabaseRequest, authorization: Optional[str] = Header(None)):
    """حذف قاعدة بيانات من المؤسسة - Owner فقط"""
    token = get_session_from_headers(authorization)
    
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    # فحص الصلاحية - Owner فقط
    if session['role'] != 'owner':
        raise HTTPException(
            status_code=403, 
            detail="فقط مالك المؤسسة يمكنه حذف قواعد بيانات"
        )
    
    print(f"🗑️ محاولة حذف قاعدة البيانات: {request.connection_id}")
    
    # ✅ حذف من organization_databases فقط (وليس من database_connections)
    db = get_db_session()
    try:
        result = db.execute(text("""
            DELETE FROM organization_databases
            WHERE org_id = :org_id AND connection_id = :connection_id
        """), {
            'org_id': session['org_id'],
            'connection_id': request.connection_id
        })
        db.execute(text("""
            DELETE FROM database_connections
            WHERE connection_id = :connection_id
        """), {'connection_id': request.connection_id})
        db.commit()
        
        if result.rowcount > 0:
            print(f"✅ تم حذف قاعدة البيانات من المؤسسة")
            
            # مسح الـ cache
            db_manager.clear_instance_cache(request.connection_id)
            
            return {
                "success": True,
                "message": "تم الحذف بنجاح"
            }
        else:
            print(f"⚠️ قاعدة البيانات غير موجودة في المؤسسة")
            return {
                "success": False,
                "message": "قاعدة البيانات غير موجودة في المؤسسة"
            }
            
    except Exception as e:
        db.rollback()
        print(f"❌ خطأ في حذف قاعدة البيانات: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# = INVITATIONS =

@router.get("/invitations")
async def get_invitations(authorization: Optional[str] = Header(None)):
    """الحصول على الدعوات - Owner فقط"""
    token = get_session_from_headers(authorization)
    
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    # فحص الصلاحية - Owner فقط
    if session['role'] != 'owner':
        raise HTTPException(
            status_code=403,
            detail="فقط مالك المؤسسة يمكنه رؤية الدعوات"
        )
    
    db = get_db_session()
    try:
        result = db.execute(text("""
            SELECT invite_code, created_at, expires_at, max_uses, current_uses, is_active
            FROM invitations
            WHERE org_id = :org_id
            ORDER BY created_at DESC
        """), {'org_id': session['org_id']})
        
        invitations = []
        for row in result:
            invitations.append({
                'code': row[0],
                'created_at': row[1].isoformat() if row[1] else None,
                'expires_at': row[2].isoformat() if row[2] else None,
                'max_uses': row[3],
                'current_uses': row[4],
                'is_active': bool(row[5])
            })
        
        return {"invitations": invitations}
    finally:
        db.close()


@router.post("/invitations/create")
async def create_invitation(request: CreateInvitationRequest, authorization: Optional[str] = Header(None)):
    """إنشاء دعوة جديدة - Owner فقط"""
    token = get_session_from_headers(authorization)
    
    if not token:
        raise HTTPException(status_code=401)
    
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401)
    
    # فحص الصلاحية - Owner فقط
    if session['role'] != 'owner':
        raise HTTPException(
            status_code=403,
            detail="فقط مالك المؤسسة يمكنه إنشاء دعوات"
        )
    
    invitation = await org_manager.create_invitation(
        org_id=session['org_id'],
        creator_id=session['user_id'],
        max_uses=request.max_uses,
        expires_hours=24
    )
    
    if invitation:
        return {
            "success": True,
            "code": invitation.invite_code,
            "link": f"https://yoursite.com/join/{invitation.invite_code}"
        }
    
    return {
        "success": False,
        "message": "فشل إنشاء الدعوة"
    }
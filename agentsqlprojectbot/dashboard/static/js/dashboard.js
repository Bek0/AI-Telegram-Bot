// /dashboard/static/js/dashboard.js

const token = localStorage.getItem('auth_token');
const userRole = localStorage.getItem('user_role');
const orgId = localStorage.getItem('org_id');
const orgName = localStorage.getItem('org_name');
const userId = localStorage.getItem('user_id');

// متغير لتخزين البيانات
let isOwner = false;
let isMember = false;

if (!token) {
    window.location.href = '/';
}

// تحقق من صحة الجلسة عند التحميل
async function verifySessionOnLoad() {
    try {
        const response = await fetch('/dashboard/verify', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                console.warn('⚠️  جلسة منتهية الصلاحية');
                logout();
            }
        }
    } catch (error) {
        console.error('❌ خطأ في التحقق من الجلسة:', error);
    }
}

// = INITIALIZATION =

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('orgName').textContent = orgName;

    const roleBadge = document.getElementById('userRole');
    roleBadge.textContent = userRole === 'owner' ? 'مالك المؤسسة' : 'عضو';
    roleBadge.className = `role-badge ${userRole}`;
    
    // تحديد الصلاحيات
    isOwner = userRole === 'owner';
    isMember = userRole === 'member';

    loadDashboard();
    setupButtons();
    setupTabs();
    updateUIPermissions();
});

// = UPDATE UI PERMISSIONS =

function updateUIPermissions() {
    
    // نماذج الإضافة - Owner فقط
    document.getElementById('addMemberForm').style.display = isOwner ? 'block' : 'none';
    document.getElementById('createDatabaseForm').style.display = isOwner ? 'block' : 'none';
    document.getElementById('createInvitationForm').style.display = isOwner ? 'block' : 'none';
    
    // أعمدة الإجراءات - Owner فقط
    document.getElementById('actionsHeader').style.display = isOwner ? 'table-cell' : 'none';
    document.getElementById('dbActionsHeader').style.display = isOwner ? 'table-cell' : 'none';
    
    // تبويب الدعوات - Owner فقط
    const invitationsTab = document.querySelector('[data-tab="invitations"]');
    if (invitationsTab) {
        invitationsTab.style.display = isOwner ? 'block' : 'none';
    }
    
    // إذا كان عضو، أخفِ بعض التبويبات
    if (isMember) {
        const tabs = document.querySelectorAll('.tab-btn');
        tabs.forEach(tab => {
            if (tab.getAttribute('data-tab') === 'invitations') {
                tab.style.display = 'none';
            }
        });
    }
    const costsTab = document.querySelector('[data-tab="costs"]');
    if (costsTab) {
        costsTab.style.display = isOwner ? 'block' : 'none';
    }
}

// = LOAD DASHBOARD =

async function loadDashboard() {
    try {
        const response = await fetch('/dashboard/overview', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) {
            if (response.status === 401) {
                logout();
            }
            throw new Error('فشل تحميل البيانات');
        }

        const data = await response.json();

        document.getElementById('membersCount').textContent = data.stats.members_count;
        document.getElementById('databasesCount').textContent = data.stats.databases_count;
        document.getElementById('invitationsCount').textContent = data.stats.active_invitations;
        document.getElementById('createdDate').textContent = data.org.created_at.substring(0, 10);

        loadMembers();
        loadDatabases();
        
        if (isOwner) {
            loadInvitations();
            loadCostsOverview();
            loadCostsByModel();
            loadCostsByStage();
            loadInputOutputCosts();
            loadCostsPerUser();
        }

    } catch (error) {
        console.error('Error:', error);
    }
}

// = MEMBERS =

async function loadMembers() {
    try {
        const response = await fetch('/dashboard/members', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) throw new Error('فشل تحميل الأعضاء');

        const data = await response.json();
        const table = document.getElementById('membersTable');

        if (!data.members || data.members.length === 0) {
            table.innerHTML = '<tr><td colspan="4" class="text-center">لا يوجد أعضاء</td></tr>';
            return;
        }

        table.innerHTML = data.members.map(member => `
            <tr>
                <td>${member.user_id}</td>
                <td>
                    <span class="role-badge ${member.role}">
                        ${member.role === 'owner' ? 'مالك' : 'عضو'}
                    </span>
                </td>
                <td>${member.joined_at.substring(0, 10)}</td>
                <td>
                    ${isOwner && member.role !== 'owner' ? `
                        <button class="btn btn-danger btn-sm" onclick="removeMember(${member.user_id})">
                            حذف
                        </button>
                    ` : (isMember ? '-' : '')}
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error:', error);
    }
}

async function addMember() {
    if (!isOwner) {
        alert('ليس لديك صلاحية لإضافة أعضاء');
        return;
    }

    const userId = document.getElementById('memberUserId').value;

    if (!userId) {
        alert('أدخل معرف المستخدم');
        return;
    }

    try {
        const response = await fetch('/dashboard/members/add', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: parseInt(userId)
            })
        });

        const data = await response.json();

        if (data.success) {
            alert('تم إضافة العضو بنجاح');
            document.getElementById('memberUserId').value = '';
            loadMembers();
        } else {
            alert('خطأ: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('حدث خطأ');
    }
}

async function removeMember(userId) {
    if (!isOwner) {
        alert('ليس لديك صلاحية لحذف أعضاء');
        return;
    }

    if (!confirm('هل أنت متأكد من حذف هذا العضو؟')) return;

    try {
        const response = await fetch('/dashboard/members/remove', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId
            })
        });

        const data = await response.json();

        if (data.success) {
            alert('تم حذف العضو بنجاح');
            loadMembers();
        } else {
            alert('خطأ في الحذف');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('حدث خطأ');
    }
}

// = DATABASES =

async function loadDatabases() {
    try {
        const response = await fetch('/dashboard/databases', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) throw new Error('فشل تحميل قواعد البيانات');

        const data = await response.json();
        const table = document.getElementById('databasesTable');

        if (!data.databases || data.databases.length === 0) {
            table.innerHTML = '<tr><td colspan="4" class="text-center">لا توجد قواعد بيانات</td></tr>';
            return;
        }

        table.innerHTML = data.databases.map(db => `
            <tr>
                <td>${db.name}</td>
                <td><code style="background: #f0f0f0; padding: 4px 8px; border-radius: 4px;">${db.connection_id}</code></td>
                <td>${db.created_at.substring(0, 10)}</td>
                <td>
                    ${isOwner ? `
                        <button class="btn btn-danger btn-sm" onclick="removeDatabase('${db.connection_id}')">
                            حذف
                        </button>
                    ` : (isMember ? '-' : '')}
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error:', error);
    }
}

async function createDatabase() {
    if (!isOwner) {
        alert('ليس لديك صلاحية لإنشاء قواعد بيانات');
        return;
    }

    const name = document.getElementById('databaseName').value.trim();
    const connectionString = document.getElementById('connectionString').value.trim();

    if (!name || !connectionString) {
        alert('أدخل الاسم وسلسلة الاتصال');
        return;
    }

    try {
        const response = await fetch('/dashboard/databases/create', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                connection_string: connectionString
            })
        });

        const data = await response.json();

        if (data.success) {
            alert('✅ ' + data.message);
            document.getElementById('databaseName').value = '';
            document.getElementById('connectionString').value = '';
            loadDatabases();
        } else {
            alert('❌ خطأ: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('حدث خطأ');
    }
}

async function removeDatabase(connectionId) {
    if (!isOwner) {
        alert('ليس لديك صلاحية لحذف قواعد البيانات');
        return;
    }

    if (!confirm('هل أنت متأكد من حذف هذه قاعدة البيانات؟')) return;

    try {
        const response = await fetch('/dashboard/databases/remove', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                connection_id: connectionId
            })
        });

        const data = await response.json();

        if (data.success) {
            alert('تم حذف قاعدة البيانات بنجاح');
            loadDatabases();
        } else {
            alert('خطأ في الحذف');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('حدث خطأ');
    }
}

// = INVITATIONS =

async function createInvitation() {
    if (!isOwner) {
        alert('ليس لديك صلاحية لإنشاء دعوات');
        return;
    }

    const maxUses = document.getElementById('maxUses').value;

    if (!maxUses || maxUses < 1) {
        alert('أدخل عدد الاستخدامات الصحيح');
        return;
    }

    try {
        const response = await fetch('/dashboard/invitations/create', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                max_uses: parseInt(maxUses)
            })
        });

        const data = await response.json();

        if (data.success) {
            const result = document.getElementById('invitationResult');
            result.innerHTML = `
                <div class="success-message" style="margin-top: 20px;">
                    <strong>✅ تم إنشاء الدعوة بنجاح</strong><br>
                    الرمز: <code>${data.code}</code><br>
                    الرابط: <code>${data.link}</code><br>
                    الاستخدامات: ${maxUses} | الصلاحية: 24 ساعة
                </div>
            `;
            
            setTimeout(loadInvitations, 1000);
        } else {
            alert('خطأ: ' + data.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('حدث خطأ');
    }
}

async function loadInvitations() {
    if (!isOwner) {
        return;
    }

    try {
        const response = await fetch('/dashboard/invitations', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) throw new Error('فشل تحميل الدعوات');

        const data = await response.json();
        const table = document.getElementById('invitationsTable');

        if (!data.invitations || data.invitations.length === 0) {
            table.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center">لا توجد دعوات</td>
                </tr>
            `;
            return;
        }

        table.innerHTML = data.invitations.map(inv => {
            // تحويل النص إلى كائن تاريخ
            const date = new Date(inv.expires_at);

            // تنسيق التاريخ والوقت بالعربية
            const formattedDate = date.toLocaleString({
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            });

            return `
                <tr>
                    <td><code>${inv.code}</code></td>
                    <td>${inv.current_uses}/${inv.max_uses}</td>
                    <td>${formattedDate}</td>
                </tr>
            `;
        }).join('');


    } catch (error) {
        console.error('Error:', error);
    }
}

// = TABS =

function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.getAttribute('data-tab');
            
            tabBtns.forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            btn.classList.add('active');
            document.getElementById(`${tabName}-tab`).classList.add('active');
            
            if (tabName === 'invitations' && isOwner) {
                loadInvitations();
            }
        });
    });
}

// = BUTTONS SETUP =

function setupButtons() {
    document.getElementById('logoutBtn').addEventListener('click', logout);
}

// = LOGOUT =

async function logout() {
    try {
        await fetch('/dashboard/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
    } catch (error) {
        console.error('Error:', error);
    }

    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_role');
    localStorage.removeItem('org_id');
    localStorage.removeItem('org_name');
    localStorage.removeItem('user_id');
    localStorage.removeItem('login_timestamp');

    window.location.href = '/';
}

// = COSTS =

async function loadCostsOverview() {
    try {
        const response = await fetch('/dashboard/costs/overview', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) throw new Error('فشل تحميل بيانات التكاليف');

        const data = await response.json();
        const stats = data.total_stats;

        document.getElementById('totalCost').textContent = stats.total_cost.toFixed(6) + ' $';
        document.getElementById('totalInputTokens').textContent = stats.total_input_tokens.toLocaleString();
        document.getElementById('totalOutputTokens').textContent = stats.total_output_tokens.toLocaleString();
        document.getElementById('totalConversations').textContent = stats.total_conversations;

    } catch (error) {
        console.error('Error:', error);
    }
}

async function loadCostsByModel() {
    try {
        const response = await fetch('/dashboard/costs/by-model', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) throw new Error('فشل تحميل تكاليف النماذج');

        const data = await response.json();
        const table = document.getElementById('costsByModelTable');

        if (!data.models || data.models.length === 0) {
            table.innerHTML = '<tr><td colspan="7" class="text-center">لا توجد بيانات</td></tr>';
            return;
        }

        table.innerHTML = data.models.map(model => `
            <tr>
                <td><strong>${model.model_name}</strong></td>
                <td>${model.usage_count}</td>
                <td>${model.total_input_tokens.toLocaleString()}</td>
                <td>${model.total_output_tokens.toLocaleString()}</td>
                <td>$${model.total_input_cost.toFixed(6)}</td>
                <td>$${model.total_output_cost.toFixed(6)}</td>
                <td><strong>$${model.total_cost.toFixed(6)}</strong></td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error:', error);
    }
}

async function loadCostsByStage() {
    try {
        const response = await fetch('/dashboard/costs/by-stage', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) throw new Error('فشل تحميل تكاليف المراحل');

        const data = await response.json();
        const table = document.getElementById('costsByStageTable');

        if (!data.stages || data.stages.length === 0) {
            table.innerHTML = '<tr><td colspan="7" class="text-center">لا توجد بيانات</td></tr>';
            return;
        }

        table.innerHTML = data.stages.map(stage => `
            <tr>
                <td><strong>${stage.stage_name}</strong></td>
                <td>${stage.usage_count}</td>
                <td>${stage.total_input_tokens.toLocaleString()}</td>
                <td>${stage.total_output_tokens.toLocaleString()}</td>
                <td>$${stage.total_input_cost.toFixed(6)}</td>
                <td>$${stage.total_output_cost.toFixed(6)}</td>
                <td><strong>$${stage.total_cost.toFixed(6)}</strong></td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error:', error);
    }
}

async function loadInputOutputCosts() {
    try {
        const response = await fetch('/dashboard/costs/input-output', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) throw new Error('فشل تحميل البيانات');

        const data = await response.json();
        
        console.log('📊 Input/Output Costs Data:', data); // للتشخيص

        // التأكد من أن البيانات موجودة وليست null أو undefined
        const inputCost = parseFloat(data.input_cost) || 0;
        const outputCost = parseFloat(data.output_cost) || 0;
        const totalCost = parseFloat(data.total_cost) || 0;
        
        console.log('💰 Parsed Values:', { inputCost, outputCost, totalCost });

        // تحديث النصوص أولاً
        document.getElementById('inputCost').textContent = '$' + inputCost.toFixed(6);
        document.getElementById('outputCost').textContent = '$' + outputCost.toFixed(6);
        
        // حساب النسب المئوية
        let inputPercentage = 0;
        let outputPercentage = 0;
        
        if (totalCost > 0) {
            inputPercentage = (inputCost / totalCost) * 100;
            outputPercentage = (outputCost / totalCost) * 100;
        }
        
        document.getElementById('inputPercentage').textContent = inputPercentage.toFixed(2) + '%';
        document.getElementById('outputPercentage').textContent = outputPercentage.toFixed(2) + '%';

        // تدمير الرسم البياني القديم إن وجد
        if (window.costsPieChart instanceof Chart) {
            window.costsPieChart.destroy();
        }

        // إنشاء الرسم البياني الجديد مع البيانات الصحيحة
        const ctx = document.getElementById('costsPieChart');
        
        if (!ctx) {
            console.error('Canvas element not found');
            return;
        }

        // التأكد من أن البيانات يتم تمريرها كـ array من الأرقام
        const chartData = [inputCost, outputCost];
        
        console.log('📈 Chart Data:', chartData);

        window.costsPieChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['تكاليف المدخلات', 'تكاليف المخرجات'],
                datasets: [{
                    data: chartData,
                    backgroundColor: ['#3498db', '#e74c3c'],
                    borderColor: ['#2980b9', '#c0392b'],
                    borderWidth: 2,
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            font: { size: 13, weight: 'bold' },
                            padding: 15,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        enabled: true,
                        backgroundColor: 'rgba(0,0,0,0.7)',
                        padding: 10,
                        titleFont: { size: 12 },
                        bodyFont: { size: 11 },
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed;
                                const total = inputCost + outputCost;
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(2) : 0;
                                return 'التكلفة: $' + value.toFixed(6) + ' (' + percentage + '%)';
                            }
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('❌ Error in loadInputOutputCosts:', error);
        
        // عرض رسالة خطأ للمستخدم
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = 'color: #e74c3c; padding: 10px; text-align: center;';
        errorDiv.textContent = 'خطأ في تحميل بيانات التكاليف';
        const chartContainer = document.getElementById('costsPieChart');
        if (chartContainer && chartContainer.parentNode) {
            chartContainer.parentNode.insertBefore(errorDiv, chartContainer);
        }
    }
}

async function loadCostsPerUser() {
    try {
        const response = await fetch('/dashboard/costs/per-user', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (!response.ok) throw new Error('فشل تحميل بيانات المستخدمين');

        const data = await response.json();
        const table = document.getElementById('costsPerUserTable');

        document.getElementById('avgCostPerUser').textContent = '$' + data.average_cost_per_user.toFixed(6);
        document.getElementById('totalOrgCost').textContent = '$' + data.total_org_cost.toFixed(6);

        if (!data.users || data.users.length === 0) {
            table.innerHTML = '<tr><td colspan="8" class="text-center">لا توجد بيانات</td></tr>';
            return;
        }

        table.innerHTML = data.users.map(user => `
            <tr>
                <td>${user.user_id}</td>
                <td>${user.username || 'بدون اسم'}</td>
                <td>${user.conversations_count}</td>
                <td>${user.total_input_tokens.toLocaleString()}</td>
                <td>${user.total_output_tokens.toLocaleString()}</td>
                <td>$${user.total_input_cost.toFixed(6)}</td>
                <td>$${user.total_output_cost.toFixed(6)}</td>
                <td><strong>$${user.total_cost.toFixed(6)}</strong></td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error:', error);
    }
}
// /dashboard/static/js/login.js

const form = document.getElementById('loginForm');
const errorMessage = document.getElementById('errorMessage');
const submitBtn = document.getElementById('submitBtn');
const loading = document.getElementById('loading');

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    // إخفاء الرسالة السابقة
    errorMessage.classList.remove('show');

    // التحقق من المدخلات
    if (!username || !password) {
        showError('يجب ملء جميع الحقول');
        return;
    }

    // إظهار حالة التحميل
    submitBtn.style.display = 'none';
    loading.style.display = 'block';

    try {
        // إرسال بيانات الدخول
        const response = await fetch('/dashboard/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        });

        const data = await response.json();

        if (data.success) {
            // حفظ البيانات في localStorage
            localStorage.setItem('auth_token', data.token);
            localStorage.setItem('user_role', data.role);
            localStorage.setItem('org_id', data.org_id);
            localStorage.setItem('org_name', data.org_name);
            localStorage.setItem('user_id', data.user_id);

            // إعادة التوجيه
            window.location.href = '/dashboard/';
        } else {
            showError(data.message || 'فشل تسجيل الدخول');
            submitBtn.style.display = 'block';
            loading.style.display = 'none';
        }
    } catch (error) {
        console.error('Error:', error);
        showError('حدث خطأ في الاتصال. يرجى المحاولة لاحقاً');
        submitBtn.style.display = 'block';
        loading.style.display = 'none';
    }
});

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.add('show');
}

// مسح الخطأ عند التركيز على الحقول
document.getElementById('username').addEventListener('focus', () => {
    errorMessage.classList.remove('show');
});

document.getElementById('password').addEventListener('focus', () => {
    errorMessage.classList.remove('show');
});
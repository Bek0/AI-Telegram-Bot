// dashboard/static/js/login.js - تعديلات

const form = document.getElementById('loginForm');
const errorMessage = document.getElementById('errorMessage');
const submitBtn = document.getElementById('submitBtn');
const loading = document.getElementById('loading');

form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;

    errorMessage.classList.remove('show');

    if (!username || !password) {
        showError('يجب ملء جميع الحقول');
        return;
    }

    submitBtn.style.display = 'none';
    loading.style.display = 'block';

    try {
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
            localStorage.setItem('login_timestamp', new Date().toISOString());
            
            // تحقق من الجلسة بعد التوجيه
            window.location.href = '/dashboard/';
        } else {
            showError(data.message || 'فشل تسجيل الدخول');
            submitBtn.style.display = 'block';
            loading.style.display = 'none';
        }
    } catch (error) {
        console.error('Error:', error);
        showError('حدث خطأ في الاتصال');
        submitBtn.style.display = 'block';
        loading.style.display = 'none';
    }
});

function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.add('show');
}

document.getElementById('username').addEventListener('focus', () => {
    errorMessage.classList.remove('show');
});

document.getElementById('password').addEventListener('focus', () => {
    errorMessage.classList.remove('show');
});
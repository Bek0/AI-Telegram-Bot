# services/send_email.py

import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List
import os


class EmailService:
    """خدمة البريد الإلكتروني - async"""
    
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 465  # SSL
        self.email_address = os.getenv("BOT_EMAIL")
        self.email_password = os.getenv("BOT_EMAIL_PASS")
        
        if not self.email_address or not self.email_password:
            print("⚠️ تحذير: بيانات البريد الإلكتروني غير مكتملة")
    
    async def send_async(
        self, 
        subject: str, 
        body: str, 
        recipients: List[str]
    ) -> str:
        """إرسال إيميل بشكل async"""
        if not self.email_address or not self.email_password:
            raise ValueError("Email credentials not configured")
        
        # تنفيذ في executor لأن smtplib هو blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._send_email_sync,
            subject,
            body,
            recipients
        )
    
    def _send_email_sync(
        self,
        subject: str,
        body: str,
        recipients: List[str]
    ) -> str:
        """إرسال الإيميل بشكل متزامن"""
        try:
            print(f"Sending email to {len(recipients)} recipients: {recipients}")
            
            msg = MIMEMultipart()
            msg["From"] = self.email_address
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.email_address, self.email_password)
                server.send_message(msg)
            
            success_msg = f"تم إرسال الإيميل بنجاح إلى {len(recipients)} مستلم"
            print(f"✅ {success_msg}")
            return success_msg
            
        except smtplib.SMTPAuthenticationError:
            error_msg = "فشل في المصادقة: تحقق من البريد وكلمة المرور"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
            
        except smtplib.SMTPConnectError:
            error_msg = "فشل الاتصال بخادم SMTP"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"حدث خطأ غير متوقع: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)

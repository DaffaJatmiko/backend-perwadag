"""Email service using Gmail SMTP with standard library."""

import smtplib
import asyncio
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime

from src.core.config import settings
from src.templates.email_templates import EmailTemplates
from src.utils.password import mask_email

logger = logging.getLogger(__name__)


class EmailService:
    """Email service using Gmail SMTP with standard library."""
    
    def __init__(self):
        self.smtp_host = settings.EMAIL_SMTP_HOST
        self.smtp_port = settings.EMAIL_SMTP_PORT
        self.smtp_username = settings.EMAIL_SMTP_USERNAME
        self.smtp_password = settings.EMAIL_SMTP_PASSWORD
        self.sender_email = settings.EMAIL_SENDER_EMAIL
        self.sender_name = settings.EMAIL_SENDER_NAME
        
        if not all([self.smtp_username, self.smtp_password]):
            logger.warning("Kredensial Gmail SMTP tidak dikonfigurasi. Fungsionalitas email akan dinonaktifkan.")
    
    def _send_email_sync(self, to_email: str, to_name: str, subject: str, html_content: str, text_content: str) -> bool:
        """
        Send email using Gmail SMTP synchronously.
        """
        if not all([self.smtp_username, self.smtp_password]):
            logger.error("Tidak dapat mengirim email: Kredensial Gmail SMTP tidak dikonfigurasi")
            return False
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.sender_name} <{self.sender_email}>"
            message["To"] = f"{to_name} <{to_email}>"
            
            # Create HTML and text parts
            text_part = MIMEText(text_content, "plain")
            html_part = MIMEText(html_content, "html")
            
            # Add parts to message
            message.attach(text_part)
            message.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(message)
            
            logger.info(f"Email berhasil dikirim ke {mask_email(to_email)}")
            return True
            
        except smtplib.SMTPException as e:
            logger.error(f"Error SMTP mengirim email ke {mask_email(to_email)}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error tidak terduga mengirim email ke {mask_email(to_email)}: {str(e)}")
            return False
    
    async def _send_email(self, to_email: str, to_name: str, subject: str, html_content: str, text_content: str) -> bool:
        """
        Async wrapper for sync email sending.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._send_email_sync, 
            to_email, to_name, subject, html_content, text_content
        )
    
    async def send_password_reset_email(self, user_email: str, user_nama: str, reset_token: str) -> bool:
        """
        Send password reset email to user.
        
        Args:
            user_email: User's email address
            user_nama: User's full name
            reset_token: Password reset token
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not user_email or not user_nama or not reset_token:
            logger.error("Parameter tidak valid untuk email reset password")
            return False
        
        # Generate reset link
        from src.utils.password import generate_reset_link
        reset_link = generate_reset_link(reset_token)
        
        # Get email template
        template = EmailTemplates.password_reset_template(user_nama, reset_link)
        
        # Send email
        logger.info(f"Mengirim email reset password ke {mask_email(user_email)}")
        
        success = await self._send_email(
            to_email=user_email,
            to_name=user_nama,
            subject=template["subject"],
            html_content=template["htmlContent"],
            text_content=template["textContent"]
        )
        
        if success:
            logger.info(f"Email reset password berhasil dikirim ke {mask_email(user_email)}")
        else:
            logger.error(f"Gagal mengirim email reset password ke {mask_email(user_email)}")
        
        return success
    
    async def send_password_reset_success_email(self, user_email: str, user_nama: str) -> bool:
        """
        Send password reset success confirmation email.
        
        Args:
            user_email: User's email address
            user_nama: User's full name
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not user_email or not user_nama:
            logger.error("Parameter tidak valid untuk email konfirmasi reset password")
            return False
        
        # Get email template
        template = EmailTemplates.password_reset_success_template(user_nama)
        
        # Send email
        logger.info(f"Mengirim email konfirmasi reset password ke {mask_email(user_email)}")
        
        success = await self._send_email(
            to_email=user_email,
            to_name=user_nama,
            subject=template["subject"],
            html_content=template["htmlContent"],
            text_content=template["textContent"]
        )
        
        if success:
            logger.info(f"Email konfirmasi reset password berhasil dikirim ke {mask_email(user_email)}")
        else:
            logger.error(f"Gagal mengirim email konfirmasi reset password ke {mask_email(user_email)}")
        
        return success
    
    async def test_email_configuration(self) -> Dict[str, Any]:
        """
        Test email configuration by sending a test email.
        
        Returns:
            Dictionary with test results
        """
        if not all([self.smtp_username, self.smtp_password]):
            return {
                "success": False,
                "message": "Kredensial Gmail SMTP tidak dikonfigurasi",
                "smtp_host": self.smtp_host,
                "smtp_port": self.smtp_port,
                "sender_email": self.sender_email,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Send test email to sender email
        test_success = await self._send_email(
            to_email=self.smtp_username,  # Send to self
            to_name="Test User",
            subject="Test Email - Sistem Auth Pemerintah",
            html_content="<h1>Test Email</h1><p>Ini adalah email test untuk verifikasi konfigurasi Gmail SMTP.</p>",
            text_content="Test Email\n\nIni adalah email test untuk verifikasi konfigurasi Gmail SMTP."
        )
        
        return {
            "success": test_success,
            "message": "Email test berhasil dikirim" if test_success else "Gagal mengirim email test",
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "sender_email": self.sender_email,
            "sender_name": self.sender_name,
            "timestamp": datetime.utcnow().isoformat()
        }
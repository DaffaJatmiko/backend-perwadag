"""Email service yang 100% compatible untuk Gmail + Server Pemerintah."""

import smtplib
import asyncio
import logging
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from datetime import datetime

from src.core.config import settings
from src.templates.email_templates import EmailTemplates
from src.utils.password import mask_email

logger = logging.getLogger(__name__)


class EmailService:
    """Email service universal untuk Gmail + Server Pemerintah."""
    
    def __init__(self):
        self.smtp_host = settings.EMAIL_SMTP_HOST
        self.smtp_port = settings.EMAIL_SMTP_PORT
        self.smtp_username = settings.EMAIL_SMTP_USERNAME
        self.smtp_password = settings.EMAIL_SMTP_PASSWORD
        self.sender_email = settings.EMAIL_SENDER_EMAIL
        self.sender_name = settings.EMAIL_SENDER_NAME
        
        # Determine if credentials are required
        self.requires_auth = bool(self.smtp_username and self.smtp_password)
        
        if not self.requires_auth:
            logger.info("🏛️ SMTP mode: No authentication required (Government server mode)")
        else:
            logger.info("📧 SMTP mode: Authentication required (External email provider)")
    
    def _send_email_sync(self, to_email: str, to_name: str, subject: str, html_content: str, text_content: str) -> bool:
        """Send email dengan fallback ke berbagai konfigurasi."""
        
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
        
        # Coba berbagai konfigurasi sampai ada yang berhasil
        configurations = [
            # 1. User specified port dengan STARTTLS (jika ada auth)
            {
                "port": self.smtp_port,
                "use_ssl": False,
                "use_starttls": True,
                "use_auth": self.requires_auth,
                "desc": f"Port {self.smtp_port} dengan STARTTLS",
                "priority": 1
            },
            # 2. Port 465 dengan SSL (jika ada auth)
            {
                "port": 465,
                "use_ssl": True,
                "use_starttls": False,
                "use_auth": self.requires_auth,
                "desc": "Port 465 dengan SSL",
                "priority": 2
            },
            # 3. Port 587 dengan STARTTLS (jika ada auth)
            {
                "port": 587,
                "use_ssl": False,
                "use_starttls": True,
                "use_auth": self.requires_auth,
                "desc": "Port 587 dengan STARTTLS",
                "priority": 3
            },
            # 4. User specified port tanpa TLS dan tanpa auth (untuk server pemerintah)
            {
                "port": self.smtp_port,
                "use_ssl": False,
                "use_starttls": False,
                "use_auth": False,
                "desc": f"Port {self.smtp_port} tanpa enkripsi dan auth",
                "priority": 4
            },
            # 5. Port 25 tanpa enkripsi dan auth (klasik pemerintah)
            {
                "port": 25,
                "use_ssl": False,
                "use_starttls": False,
                "use_auth": False,
                "desc": "Port 25 tanpa enkripsi dan auth",
                "priority": 5
            },
            # 6. Port 587 tanpa auth (server pemerintah dengan port 587)
            {
                "port": 587,
                "use_ssl": False,
                "use_starttls": False,
                "use_auth": False,
                "desc": "Port 587 tanpa enkripsi dan auth",
                "priority": 6
            },
            # 7. Port 1025 (development/internal server)
            {
                "port": 1025,
                "use_ssl": False,
                "use_starttls": False,
                "use_auth": False,
                "desc": "Port 1025 (development server)",
                "priority": 7
            },
            # 8. Port 2525 (alternative)
            {
                "port": 2525,
                "use_ssl": False,
                "use_starttls": False,
                "use_auth": False,
                "desc": "Port 2525 (alternative server)",
                "priority": 8
            }
        ]
        
        auth_error_occurred = False
        
        for config in configurations:
            try:
                logger.info(f"🔄 Mencoba: {config['desc']}")
                
                if config["use_ssl"]:
                    # SSL direct (port 465)
                    context = ssl.create_default_context()
                    with smtplib.SMTP_SSL(self.smtp_host, config["port"], context=context, timeout=30) as server:
                        if config["use_auth"] and self.smtp_username and self.smtp_password:
                            logger.info("🔐 Authenticating with SSL...")
                            server.login(self.smtp_username, self.smtp_password)
                        else:
                            logger.info("🔓 No authentication required")
                        server.send_message(message)
                else:
                    # Plain SMTP dengan optional STARTTLS
                    with smtplib.SMTP(self.smtp_host, config["port"], timeout=30) as server:
                        if config["use_starttls"]:
                            try:
                                logger.info("🔒 Starting TLS...")
                                server.starttls()
                            except Exception as tls_error:
                                logger.info(f"⚠️ STARTTLS tidak didukung: {tls_error}")
                        
                        if config["use_auth"] and self.smtp_username and self.smtp_password:
                            logger.info("🔐 Authenticating...")
                            server.login(self.smtp_username, self.smtp_password)
                        else:
                            logger.info("🔓 No authentication required")
                        
                        server.send_message(message)
                
                logger.info(f"✅ Email berhasil dikirim ke {mask_email(to_email)} via {config['desc']}")
                return True
                
            except smtplib.SMTPAuthenticationError as e:
                logger.warning(f"🔑 Authentication error dengan {config['desc']}: {e}")
                auth_error_occurred = True
                # JANGAN BREAK! Lanjut coba konfigurasi lain
                continue
                
            except smtplib.SMTPConnectError as e:
                logger.warning(f"🌐 Connection error dengan {config['desc']}: {e}")
                continue
                
            except smtplib.SMTPServerDisconnected as e:
                logger.warning(f"🔌 Server disconnected dengan {config['desc']}: {e}")
                continue
                
            except smtplib.SMTPNotSupportedError as e:
                logger.warning(f"🚫 Feature not supported dengan {config['desc']}: {e}")
                continue
                
            except Exception as e:
                logger.warning(f"⚠️ Gagal dengan {config['desc']}: {e}")
                continue
        
        # Error summary
        if auth_error_occurred and self.requires_auth:
            logger.error(f"❌ Authentication failed - periksa kredensial email")
        
        logger.error(f"❌ Semua konfigurasi gagal untuk {mask_email(to_email)}")
        return False
    
    async def _send_email(self, to_email: str, to_name: str, subject: str, html_content: str, text_content: str) -> bool:
        """Async wrapper for sync email sending."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._send_email_sync, 
            to_email, to_name, subject, html_content, text_content
        )
    
    async def send_password_reset_email(self, user_email: str, user_nama: str, reset_token: str) -> bool:
        """Send password reset email to user."""
        if not user_email or not user_nama or not reset_token:
            logger.error("Parameter tidak valid untuk email reset password")
            return False
        
        # Generate reset link
        from src.utils.password import generate_reset_link
        reset_link = generate_reset_link(reset_token)
        
        # Get email template
        template = EmailTemplates.password_reset_template(user_nama, reset_link)
        
        # Send email
        logger.info(f"📧 Mengirim email reset password ke {mask_email(user_email)}")
        
        success = await self._send_email(
            to_email=user_email,
            to_name=user_nama,
            subject=template["subject"],
            html_content=template["htmlContent"],
            text_content=template["textContent"]
        )
        
        if success:
            logger.info(f"✅ Email reset password berhasil dikirim ke {mask_email(user_email)}")
        else:
            logger.error(f"❌ Gagal mengirim email reset password ke {mask_email(user_email)}")
            # Log reset link sebagai fallback
            logger.info(f"🔗 FALLBACK - Reset link: {reset_link}")
        
        return success
    
    async def send_password_reset_success_email(self, user_email: str, user_nama: str) -> bool:
        """Send password reset success confirmation email."""
        if not user_email or not user_nama:
            logger.error("Parameter tidak valid untuk email konfirmasi reset password")
            return False
        
        # Get email template
        template = EmailTemplates.password_reset_success_template(user_nama)
        
        # Send email
        logger.info(f"📧 Mengirim email konfirmasi reset password ke {mask_email(user_email)}")
        
        success = await self._send_email(
            to_email=user_email,
            to_name=user_nama,
            subject=template["subject"],
            html_content=template["htmlContent"],
            text_content=template["textContent"]
        )
        
        if success:
            logger.info(f"✅ Email konfirmasi reset password berhasil dikirim ke {mask_email(user_email)}")
        else:
            logger.error(f"❌ Gagal mengirim email konfirmasi reset password ke {mask_email(user_email)}")
        
        return success
    
    async def test_email_configuration(self) -> Dict[str, Any]:
        """Test email configuration by sending a test email."""
        # Send test email to sender email
        test_success = await self._send_email(
            to_email=self.sender_email or "test@localhost",
            to_name="Test User",
            subject="🧪 Test Email - Sistem Auth Pemerintah",
            html_content="<h1>Test Email</h1><p>Ini adalah email test untuk verifikasi konfigurasi SMTP.</p>",
            text_content="Test Email\n\nIni adalah email test untuk verifikasi konfigurasi SMTP."
        )
        
        return {
            "success": test_success,
            "message": "Email test berhasil dikirim" if test_success else "Gagal mengirim email test",
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "sender_email": self.sender_email,
            "sender_name": self.sender_name,
            "requires_auth": self.requires_auth,
            "timestamp": datetime.utcnow().isoformat()
        }
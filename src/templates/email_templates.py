"""Email templates for password reset functionality."""

from typing import Dict, Any
from src.core.config import settings


class EmailTemplates:
    """Email templates for various notifications."""
    
    @staticmethod
    def password_reset_template(nama: str, reset_link: str) -> Dict[str, Any]:
        return {
            "subject": "Reset Password - Government Auth System",
            "htmlContent": f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Reset Password</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 30px;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .logo {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #2563eb;
                    }}
                    .content {{
                        line-height: 1.6;
                        color: #333;
                    }}
                    .footer {{
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                        font-size: 12px;
                        color: #666;
                    }}
                    .warning {{
                        background-color: #fef3c7;
                        border: 1px solid #f59e0b;
                        padding: 15px;
                        border-radius: 5px;
                        margin: 20px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">Government Auth System</div>
                    </div>

                    <div class="content">
                        <h2>Reset Password Request</h2>
                        <p>Dear {nama},</p>

                        <p>Kami menerima permintaan untuk reset password akun Anda. Jika Anda tidak melakukan permintaan ini, silakan abaikan email ini.</p>

                        <p>Untuk reset password, silakan klik tombol di bawah ini:</p>

                        <div style="text-align: center;">
                            <a href="{reset_link}" style="display: inline-block; padding: 10px 24px; background-color: #2563eb; color: #ffffff; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 6px;">
                                Reset Password
                            </a>
                        </div>

                        <p>Atau copy dan paste link berikut ke browser Anda:</p>
                        <p style="word-break: break-all; background-color: #f8f9fa; padding: 10px; border-radius: 4px; font-family: monospace;">
                            {reset_link}
                        </p>

                        <div class="warning">
                            <strong>⚠️ Penting:</strong>
                            <ul>
                                <li>Link ini hanya berlaku selama 1 jam</li>
                                <li>Link hanya dapat digunakan sekali</li>
                                <li>Jangan bagikan link ini kepada siapa pun</li>
                            </ul>
                        </div>
                    </div>

                    <div class="footer">
                        <p>Email ini dikirim secara otomatis, mohon tidak membalas email ini.</p>
                        <p>Jika Anda mengalami masalah, silakan hubungi administrator sistem.</p>
                        <p>&copy; 2025 Sistem Evaluasi Perwadag. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            "textContent": f"""
            Reset Password - Government Auth System

            Dear {nama},

            Kami menerima permintaan untuk reset password akun Anda. Jika Anda tidak melakukan permintaan ini, silakan abaikan email ini.

            Untuk reset password, silakan buka link berikut:
            {reset_link}

            PENTING:
            - Link ini hanya berlaku selama 1 jam
            - Link hanya dapat digunakan sekali
            - Jangan bagikan link ini kepada siapa pun

            Jika Anda mengalami masalah, silakan hubungi administrator sistem.

            Email ini dikirim secara otomatis, mohon tidak membalas email ini.

            © 2024 Government Auth System. All rights reserved.
            """
        }

    
    @staticmethod
    def password_reset_success_template(nama: str) -> Dict[str, Any]:
        """
        Template untuk konfirmasi password reset berhasil.
        
        Args:
            nama: Nama lengkap user
            
        Returns:
            Email template data untuk Brevo API
        """
        return {
            "subject": "Password Reset Successful - Government Auth System",
            "htmlContent": f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Password Reset Successful</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .logo {{ font-size: 24px; font-weight: bold; color: #2563eb; }}
                    .content {{ line-height: 1.6; color: #333; }}
                    .success {{ background-color: #d1fae5; border: 1px solid #10b981; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                    .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">Government Auth System</div>
                    </div>
                    
                    <div class="content">
                        <h2>Password Reset Successful</h2>
                        <p>Dear {nama},</p>
                        
                        <div class="success">
                            <strong>✅ Password Anda telah berhasil direset!</strong>
                        </div>
                        
                        <p>Password akun Anda telah berhasil diubah. Anda sekarang dapat login dengan password baru Anda.</p>
                        
                        <p>Jika Anda tidak melakukan perubahan password ini, segera hubungi administrator sistem untuk keamanan akun Anda.</p>
                        
                        <p><strong>Tips Keamanan:</strong></p>
                        <ul>
                            <li>Gunakan password yang kuat dan unik</li>
                            <li>Jangan bagikan password kepada siapa pun</li>
                            <li>Logout dari semua perangkat setelah menggunakan</li>
                        </ul>
                    </div>
                    
                    <div class="footer">
                        <p>Email ini dikirim secara otomatis, mohon tidak membalas email ini.</p>
                        <p>Jika Anda mengalami masalah, silakan hubungi administrator sistem.</p>
                        <p>&copy; 2024 Government Auth System. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            "textContent": f"""
            Password Reset Successful - Government Auth System
            
            Dear {nama},
            
            ✅ Password Anda telah berhasil direset!
            
            Password akun Anda telah berhasil diubah. Anda sekarang dapat login dengan password baru Anda.
            
            Jika Anda tidak melakukan perubahan password ini, segera hubungi administrator sistem untuk keamanan akun Anda.
            
            Tips Keamanan:
            - Gunakan password yang kuat dan unik
            - Jangan bagikan password kepada siapa pun
            - Logout dari semua perangkat setelah menggunakan
            
            Email ini dikirim secara otomatis, mohon tidak membalas email ini.
            
            © 2025 Sistem Evaluasi Perwadag. All rights reserved.
            """
        }
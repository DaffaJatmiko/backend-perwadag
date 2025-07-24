"""Email composition service with variable replacement."""

import re
from typing import Dict, Any, Optional
from urllib.parse import quote
from fastapi import HTTPException, status

from src.repositories.email_template import EmailTemplateRepository
from src.services.laporan_hasil import LaporanHasilService
from src.schemas.email_template import EmailComposedResponse


class EmailCompositionService:
    """Service for composing emails with variable replacement."""
    
    def __init__(self, email_template_repo: EmailTemplateRepository, laporan_hasil_service: LaporanHasilService):
        self.email_template_repo = email_template_repo
        self.laporan_hasil_service = laporan_hasil_service
    
    async def compose_laporan_hasil_email(self, laporan_hasil_id: str, user_name: str) -> EmailComposedResponse:
        """Compose email for laporan hasil using active template."""
        # Get active template
        template = await self.email_template_repo.get_active_template()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tidak ada template email yang aktif"
            )
        
        # Get laporan hasil data
        try:
            laporan_data = await self.laporan_hasil_service.get_laporan_hasil_or_404(laporan_hasil_id)
        except HTTPException as e:
            if e.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Laporan hasil tidak ditemukan"
                )
            raise e
        
        # Prepare variables for replacement
        variables = self._prepare_variables(laporan_data, user_name)
        
        # Replace variables in template
        subject = self._replace_variables(template.subject_template, variables)
        body = self._replace_variables(template.body_template, variables)
        
        # Create Gmail URL
        gmail_url = self._create_gmail_url(subject, body)
        
        return EmailComposedResponse(
            subject=subject,
            body=body,
            gmail_url=gmail_url
        )
    
    def _prepare_variables(self, laporan_data: Any, user_name: str) -> Dict[str, str]:
        """Prepare variables for template replacement."""
        variables = {}
        
        # Basic report information
        variables["nama_perwadag"] = getattr(laporan_data, "nama_perwadag", "")
        variables["inspektorat"] = getattr(laporan_data, "inspektorat", "")
        variables["tahun_evaluasi"] = str(getattr(laporan_data, "tahun_evaluasi", ""))
        variables["nomor_laporan"] = getattr(laporan_data, "nomor_laporan", "Belum ada nomor") or "Belum ada nomor"
        
        # Format tanggal laporan
        tanggal_laporan = getattr(laporan_data, "tanggal_laporan", None)
        if tanggal_laporan:
            try:
                from datetime import datetime, date
                if isinstance(tanggal_laporan, str):
                    dt = datetime.fromisoformat(tanggal_laporan.replace('Z', '+00:00'))
                elif isinstance(tanggal_laporan, date):
                    dt = datetime.combine(tanggal_laporan, datetime.min.time())
                else:
                    dt = tanggal_laporan
                variables["tanggal_laporan"] = dt.strftime("%d/%m/%Y")
            except:
                variables["tanggal_laporan"] = "Belum ditentukan"
        else:
            variables["tanggal_laporan"] = "Belum ditentukan"
        
        # Evaluation period
        tanggal_mulai = getattr(laporan_data, "tanggal_evaluasi_mulai", None)
        tanggal_selesai = getattr(laporan_data, "tanggal_evaluasi_selesai", None)
        
        try:
            from datetime import datetime, date
            if isinstance(tanggal_mulai, str):
                dt_mulai = datetime.fromisoformat(tanggal_mulai.replace('Z', '+00:00'))
            elif isinstance(tanggal_mulai, date):
                dt_mulai = datetime.combine(tanggal_mulai, datetime.min.time())
            else:
                dt_mulai = tanggal_mulai
            variables["tanggal_mulai"] = dt_mulai.strftime("%d/%m/%Y")
        except:
            variables["tanggal_mulai"] = ""
        
        try:
            from datetime import datetime, date
            if isinstance(tanggal_selesai, str):
                dt_selesai = datetime.fromisoformat(tanggal_selesai.replace('Z', '+00:00'))
            elif isinstance(tanggal_selesai, date):
                dt_selesai = datetime.combine(tanggal_selesai, datetime.min.time())
            else:
                dt_selesai = tanggal_selesai
            variables["tanggal_selesai"] = dt_selesai.strftime("%d/%m/%Y")
        except:
            variables["tanggal_selesai"] = ""
        
        # Duration from surat_tugas_info
        surat_tugas_info = getattr(laporan_data, "surat_tugas_info", None)
        if surat_tugas_info:
            variables["durasi_evaluasi"] = str(getattr(surat_tugas_info, "durasi_evaluasi", ""))
        else:
            variables["durasi_evaluasi"] = ""
        
        # Status information
        variables["evaluation_status"] = getattr(laporan_data, "evaluation_status", "")
        variables["status_kelengkapan"] = "✅ Lengkap" if getattr(laporan_data, "is_completed", False) else "⚠️ Belum Lengkap"
        variables["persentase"] = str(getattr(laporan_data, "completion_percentage", 0))
        
        # File information
        has_file = getattr(laporan_data, "has_file", False)
        if has_file:
            file_urls = getattr(laporan_data, "file_urls", None)
            if file_urls:
                file_url = getattr(file_urls, "file_url", "")
                variables["file_status"] = "✅ File dokumen tersedia"
                variables["file_url"] = f"🔗 Link Download: {file_url}" if file_url else ""
            else:
                variables["file_status"] = "✅ File dokumen tersedia"
                variables["file_url"] = ""
        else:
            variables["file_status"] = "❌ File dokumen belum tersedia"
            variables["file_url"] = ""
        
        # User information
        variables["user_nama"] = user_name
        
        
        return variables
    
    def _replace_variables(self, template: str, variables: Dict[str, str]) -> str:
        """Replace variables in template with actual values."""
        def replace_func(match):
            var_name = match.group(1)
            return variables.get(var_name, f"{{{{{var_name}}}}}")  # Keep original if not found
        
        # Pattern to match {{variable_name}}
        pattern = r'\{\{([^}]+)\}\}'
        return re.sub(pattern, replace_func, template)
    
    def _create_gmail_url(self, subject: str, body: str) -> str:
        """Create Gmail compose URL."""
        encoded_subject = quote(subject)
        encoded_body = quote(body)
        return f"https://mail.google.com/mail/u/0/?view=cm&su={encoded_subject}&body={encoded_body}"
    
    def get_available_variables(self) -> Dict[str, str]:
        """Get list of available variables for template creation."""
        return {
            "nama_perwadag": "Nama perwadag yang dievaluasi",
            "inspektorat": "Nama inspektorat",
            "tahun_evaluasi": "Tahun evaluasi",
            "nomor_laporan": "Nomor laporan",
            "tanggal_laporan": "Tanggal laporan (dd/mm/yyyy)",
            "tanggal_mulai": "Tanggal mulai evaluasi (dd/mm/yyyy)",
            "tanggal_selesai": "Tanggal selesai evaluasi (dd/mm/yyyy)",
            "durasi_evaluasi": "Durasi evaluasi dalam hari",
            "evaluation_status": "Status evaluasi",
            "status_kelengkapan": "Status kelengkapan (Lengkap/Belum Lengkap)",
            "persentase": "Persentase kelengkapan",
            "file_status": "Status ketersediaan file",
            "file_url": "Link download file (jika tersedia)",
            "user_nama": "Nama user yang mengirim email"
        }
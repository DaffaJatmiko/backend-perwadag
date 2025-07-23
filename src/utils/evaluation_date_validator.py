"""Utility untuk validasi tanggal evaluasi access control."""

from datetime import date
from typing import Optional
from fastapi import HTTPException, status


class EvaluationDateValidator:
    """Validator untuk date-based access control dalam evaluation workflow."""
    
    @staticmethod
    def check_evaluation_date_access(
        tanggal_evaluasi_selesai: date,
        operation: str = "update",
        module_name: str = "record"
    ) -> None:
        """
        Check apakah user masih bisa melakukan operasi berdasarkan tanggal evaluasi.
        
        Args:
            tanggal_evaluasi_selesai: Tanggal selesai evaluasi dari surat tugas
            operation: Jenis operasi (update, upload, delete)
            module_name: Nama module yang diakses (meeting, matriks, kuisioner, dll)
            
        Raises:
            HTTPException: Jika akses ditolak karena tanggal evaluasi sudah lewat
        """
        current_date = date.today()
        
        if current_date > tanggal_evaluasi_selesai:
            # Mapping operasi ke bahasa Indonesia
            operation_mapping = {
                "update": "mengubah",
                "upload": "mengunggah file",
                "delete": "menghapus",
                "edit": "mengedit"
            }
            
            # Mapping module ke bahasa Indonesia
            module_mapping = {
                "meeting": "data meeting",
                "matriks": "data matriks",
                "kuisioner": "data kuisioner",
                "surat pemberitahuan": "surat pemberitahuan",
                "laporan hasil": "laporan hasil",
                "record": "data"
            }
            
            operation_id = operation_mapping.get(operation, operation)
            module_id = module_mapping.get(module_name, module_name)
            
            # UBAH BAGIAN INI - jadi simple response
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tidak dapat {operation_id} {module_id} karena periode evaluasi telah berakhir pada {tanggal_evaluasi_selesai.strftime('%d %B %Y')}"
            )
    
    @staticmethod
    def is_evaluation_editable(tanggal_evaluasi_selesai: date) -> bool:
        """
        Check apakah evaluasi masih bisa diedit berdasarkan tanggal.
        
        Returns:
            bool: True jika masih bisa diedit, False jika sudah tidak bisa
        """
        current_date = date.today()
        return current_date <= tanggal_evaluasi_selesai
    
    @staticmethod
    def get_evaluation_access_info(tanggal_evaluasi_selesai: date) -> dict:
        """
        Get informasi access berdasarkan tanggal evaluasi.
        
        Returns:
            dict: Informasi access control
        """
        current_date = date.today()
        is_editable = current_date <= tanggal_evaluasi_selesai
        
        return {
            "is_editable": is_editable,
            "current_date": current_date.isoformat(),
            "evaluation_end_date": tanggal_evaluasi_selesai.isoformat(),
            "days_remaining": (tanggal_evaluasi_selesai - current_date).days if is_editable else 0,
            "days_past_deadline": (current_date - tanggal_evaluasi_selesai).days if not is_editable else 0,
            "status": "aktif" if is_editable else "berakhir",
            "status_message": f"Periode evaluasi masih berlaku sampai {tanggal_evaluasi_selesai.strftime('%d %B %Y')}" if is_editable else f"Periode evaluasi sudah berakhir pada {tanggal_evaluasi_selesai.strftime('%d %B %Y')}"
        }


# Convenience functions untuk berbagai modules
def validate_meeting_date_access(tanggal_evaluasi_selesai: date, operation: str = "update") -> None:
    """Validasi akses tanggal untuk operasi meeting."""
    EvaluationDateValidator.check_evaluation_date_access(
        tanggal_evaluasi_selesai, operation, "meeting"
    )


def validate_matriks_date_access(tanggal_evaluasi_selesai: date, operation: str = "update") -> None:
    """Validasi akses tanggal untuk operasi matriks."""
    EvaluationDateValidator.check_evaluation_date_access(
        tanggal_evaluasi_selesai, operation, "matriks"
    )


def validate_kuisioner_date_access(tanggal_evaluasi_selesai: date, operation: str = "update") -> None:
    """Validasi akses tanggal untuk operasi kuisioner."""
    EvaluationDateValidator.check_evaluation_date_access(
        tanggal_evaluasi_selesai, operation, "kuisioner"
    )


def validate_surat_pemberitahuan_date_access(tanggal_evaluasi_selesai: date, operation: str = "update") -> None:
    """Validasi akses tanggal untuk operasi surat pemberitahuan."""
    EvaluationDateValidator.check_evaluation_date_access(
        tanggal_evaluasi_selesai, operation, "surat pemberitahuan"
    )


def validate_laporan_hasil_date_access(tanggal_evaluasi_selesai: date, operation: str = "update") -> None:
    """Validasi akses tanggal untuk operasi laporan hasil."""
    EvaluationDateValidator.check_evaluation_date_access(
        tanggal_evaluasi_selesai, operation, "laporan hasil"
    )
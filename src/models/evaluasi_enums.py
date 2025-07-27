"""Enums untuk sistem evaluasi perwadag."""

from enum import Enum


class MeetingType(str, Enum):
    """Enum untuk jenis meeting dalam proses evaluasi."""
    ENTRY = "ENTRY"
    KONFIRMASI = "KONFIRMASI"
    EXIT = "EXIT"
    
    @classmethod
    def get_all_values(cls):
        """Get all meeting type values as list."""
        return [meeting_type.value for meeting_type in cls]
    
    @classmethod
    def is_valid_type(cls, meeting_type: str) -> bool:
        """Check if meeting type is valid."""
        return meeting_type in cls.get_all_values()
    
    @classmethod
    def get_display_name(cls, meeting_type: str) -> str:
        """Get display name untuk meeting type."""
        display_map = {
            cls.ENTRY.value: "Entry Meeting",
            cls.KONFIRMASI.value: "Konfirmasi Meeting",
            cls.EXIT.value: "Exit Meeting"
        }
        return display_map.get(meeting_type, meeting_type)


class StatusEvaluasi(str, Enum):
    """Enum untuk status evaluasi (untuk tracking progress)."""
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    
    @classmethod
    def get_all_values(cls):
        """Get all status values as list."""
        return [status.value for status in cls]
    
    @classmethod
    def get_display_name(cls, status: str) -> str:
        """Get display name untuk status."""
        display_map = {
            cls.DRAFT.value: "Draft",
            cls.IN_PROGRESS.value: "Sedang Berlangsung",
            cls.COMPLETED.value: "Selesai",
            cls.CANCELLED.value: "Dibatalkan"
        }
        return display_map.get(status, status)


class FileType(str, Enum):
    """Enum untuk jenis file yang diupload dalam evaluasi."""
    SURAT_TUGAS = "surat_tugas"
    SURAT_PEMBERITAHUAN = "surat_pemberitahuan"
    MEETING_BUKTI = "meeting_bukti"
    MATRIKS = "matriks"
    LAPORAN_HASIL = "laporan_hasil"
    KUISIONER = "kuisioner"
    FORMAT_KUISIONER = "format_kuisioner"
    
    @classmethod
    def get_allowed_extensions(cls, file_type: str) -> list:
        """Get allowed file extensions for specific file type."""
        # 🔥 UPDATED: Tambah .xls, .xlsx, .png, .jpg, .jpeg, .webp untuk semua tipe
        extensions_map = {
            cls.SURAT_TUGAS.value: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.webp'],
            cls.SURAT_PEMBERITAHUAN.value: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.webp'],
            cls.MEETING_BUKTI.value: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.webp'],
            cls.MATRIKS.value: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.webp'],
            cls.LAPORAN_HASIL.value: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.webp'],
            cls.KUISIONER.value: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.webp'],
            cls.FORMAT_KUISIONER.value: ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg', '.webp']
        }
        return extensions_map.get(file_type, ['.pdf', '.doc', '.docx'])
    
    @classmethod
    def get_max_file_size(cls, file_type: str) -> int:
        """Get max file size in bytes for specific file type."""
        # 🔥 UPDATED: Semua jadi 10MB
        size_map = {
            cls.SURAT_TUGAS.value: 10 * 1024 * 1024,  # 10MB
            cls.SURAT_PEMBERITAHUAN.value: 10 * 1024 * 1024,  # 10MB
            cls.MEETING_BUKTI.value: 10 * 1024 * 1024,  # 10MB (was 15MB)
            cls.MATRIKS.value: 10 * 1024 * 1024,  # 10MB (was 20MB)
            cls.LAPORAN_HASIL.value: 10 * 1024 * 1024,  # 10MB (was 50MB)
            cls.KUISIONER.value: 10 * 1024 * 1024,  # 10MB (was 20MB)
            cls.FORMAT_KUISIONER.value: 10 * 1024 * 1024  # 10MB (was 20MB)
        }
        return size_map.get(file_type, 10 * 1024 * 1024)  # Default 10MB
    
    @classmethod
    def get_display_name(cls, file_type: str) -> str:
        """Get display name untuk file type."""
        display_map = {
            cls.SURAT_TUGAS.value: "Surat Tugas",
            cls.SURAT_PEMBERITAHUAN.value: "Surat Pemberitahuan",
            cls.MEETING_BUKTI.value: "Bukti Meeting",
            cls.MATRIKS.value: "Matriks Rekomendasi",
            cls.LAPORAN_HASIL.value: "Laporan Hasil",
            cls.KUISIONER.value: "Kuisioner",
            cls.FORMAT_KUISIONER.value: "Template Kuisioner"
        }
        return display_map.get(file_type, file_type)


class EvaluasiStage(str, Enum):
    """Enum untuk tahapan evaluasi (untuk progress tracking)."""
    SURAT_PEMBERITAHUAN = "surat_pemberitahuan"
    ENTRY_MEETING = "entry_meeting"
    KONFIRMASI_MEETING = "konfirmasi_meeting"
    EXIT_MEETING = "exit_meeting"
    MATRIKS = "matriks"
    LAPORAN_HASIL = "laporan_hasil"
    KUISIONER = "kuisioner"
    
    @classmethod
    def get_all_stages(cls):
        """Get all stages in order."""
        return [
            cls.SURAT_PEMBERITAHUAN,
            cls.ENTRY_MEETING,
            cls.KONFIRMASI_MEETING,
            cls.EXIT_MEETING,
            cls.MATRIKS,
            cls.LAPORAN_HASIL,
            cls.KUISIONER
        ]
    
    @classmethod
    def get_stage_order(cls, stage: str) -> int:
        """Get order number for stage (1-7)."""
        stages = cls.get_all_stages()
        try:
            return stages.index(cls(stage)) + 1
        except (ValueError, TypeError):
            return 0
    
    @classmethod
    def get_display_name(cls, stage: str) -> str:
        """Get display name untuk stage."""
        display_map = {
            cls.SURAT_PEMBERITAHUAN.value: "Surat Pemberitahuan",
            cls.ENTRY_MEETING.value: "Entry Meeting",
            cls.KONFIRMASI_MEETING.value: "Konfirmasi Meeting",
            cls.EXIT_MEETING.value: "Exit Meeting",
            cls.MATRIKS.value: "Matriks Rekomendasi",
            cls.LAPORAN_HASIL.value: "Laporan Hasil",
            cls.KUISIONER.value: "Kuisioner"
        }
        return display_map.get(stage, stage)


class FileCategory(str, Enum):
    """Enum untuk kategori file (untuk organizasi folder)."""
    DOCUMENT = "document"  # PDF, DOC, DOCX
    SPREADSHEET = "spreadsheet"  # XLS, XLSX
    IMAGE = "image"  # JPG, JPEG, PNG, WEBP
    
    @classmethod
    def get_category_by_extension(cls, extension: str) -> str:
        """Get file category by extension."""
        extension = extension.lower()
        
        if extension in ['.pdf', '.doc', '.docx']:
            return cls.DOCUMENT.value
        elif extension in ['.xls', '.xlsx']:
            return cls.SPREADSHEET.value
        elif extension in ['.jpg', '.jpeg', '.png', '.webp']:  # 🔥 UPDATED: Tambah .webp
            return cls.IMAGE.value
        else:
            return cls.DOCUMENT.value  # Default
    
    @classmethod
    def get_mime_types(cls, category: str) -> list:
        """Get MIME types for category."""
        mime_map = {
            cls.DOCUMENT.value: [
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ],
            cls.SPREADSHEET.value: [
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ],
            cls.IMAGE.value: [
                'image/jpeg',
                'image/png',
                'image/webp'  # 🔥 UPDATED: Tambah webp
            ]
        }
        return mime_map.get(category, [])
"""Service untuk surat tugas dengan auto-generate workflow."""

from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import or_

from src.repositories.surat_tugas import SuratTugasRepository
from src.repositories.surat_pemberitahuan import SuratPemberitahuanRepository
from src.repositories.meeting import MeetingRepository
from src.repositories.matriks import MatriksRepository
from src.repositories.laporan_hasil import LaporanHasilRepository
from src.repositories.kuisioner import KuisionerRepository
from src.schemas.surat_tugas import (
    SuratTugasCreate, SuratTugasUpdate, SuratTugasResponse, 
    SuratTugasListResponse, SuratTugasCreateResponse, SuratTugasOverview,
    EvaluasiProgress, PerwardagSummary, SuratTugasStats, AssignmentInfo
)
from src.schemas.surat_pemberitahuan import SuratPemberitahuanCreate
from src.schemas.meeting import MeetingCreate
from src.schemas.matriks import MatriksCreate
from src.schemas.laporan_hasil import LaporanHasilCreate
from src.schemas.kuisioner import KuisionerCreate
from src.schemas.filters import SuratTugasFilterParams
from src.schemas.common import SuccessResponse
from src.utils.evaluasi_files import evaluasi_file_manager
from src.models.evaluasi_enums import MeetingType
from src.schemas.shared import FileDeleteResponse
from src.schemas.shared import FileUrls, FileMetadata


class SuratTugasService:
    """Service untuk surat tugas dengan auto-generate workflow."""
    
    def __init__(
        self,
        surat_tugas_repo: SuratTugasRepository,
        surat_pemberitahuan_repo: SuratPemberitahuanRepository,
        meeting_repo: MeetingRepository,
        matriks_repo: MatriksRepository,
        laporan_hasil_repo: LaporanHasilRepository,
        kuisioner_repo: KuisionerRepository,
        user_repo=None  # Add user_repo as optional parameter
    ):
        self.surat_tugas_repo = surat_tugas_repo
        self.surat_pemberitahuan_repo = surat_pemberitahuan_repo
        self.meeting_repo = meeting_repo
        self.matriks_repo = matriks_repo
        self.laporan_hasil_repo = laporan_hasil_repo
        self.kuisioner_repo = kuisioner_repo
        self.user_repo = user_repo
    
    # ===== MAIN CREATE WITH AUTO-GENERATE =====
    
    async def create_surat_tugas(
        self, 
        surat_tugas_data: SuratTugasCreate,
        file: UploadFile,
        current_user_id: str
    ) -> SuratTugasCreateResponse:
        """
        Create surat tugas baru dengan auto-generate semua related records.
        
        Workflow:
        1. Validate perwadag exists dan ambil inspektorat-nya
        2. AUTO-DETECT pimpinan inspektorat berdasarkan inspektorat perwadag
        3. Validate nomor surat unique
        4. Upload file surat tugas
        5. Create surat tugas record (dengan pimpinan_inspektorat_id otomatis)
        6. AUTO-GENERATE 6 related records:
        - 1x surat_pemberitahuan (empty)
        - 3x meetings (entry, konfirmasi, exit - all empty)
        - 1x matriks (empty)
        - 1x laporan_hasil (empty)
        - 1x kuisioner (empty)
        7. Return complete response
        """
        
        # 1. Validate perwadag exists DAN ambil inspektorat-nya
        perwadag = await self.surat_tugas_repo.get_perwadag_by_id(surat_tugas_data.user_perwadag_id)
        if not perwadag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perwadag tidak ditemukan atau tidak aktif"
            )
        
        # 1.1 Pastikan perwadag punya inspektorat
        inspektorat_perwadag = perwadag.inspektorat
        if not inspektorat_perwadag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User perwadag tidak memiliki inspektorat yang terdaftar"
            )
        
        # 2. AUTO-DETECT PIMPINAN INSPEKTORAT
        # Cari user dengan role "PIMPINAN" di inspektorat yang sama dengan perwadag
        pimpinan_inspektorat = await self.user_repo.get_pimpinan_by_inspektorat(inspektorat_perwadag)
        if not pimpinan_inspektorat:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tidak ada pimpinan ditemukan di {inspektorat_perwadag}. "
                    f"Silakan pastikan ada user dengan role PIMPINAN di inspektorat tersebut."
            )
        
        # 2.1 Set pimpinan_inspektorat_id ke dalam surat_tugas_data
        # PENTING: Tambahkan field ini ke data sebelum create
        surat_tugas_data_with_pimpinan = surat_tugas_data.dict()
        surat_tugas_data_with_pimpinan['pimpinan_inspektorat_id'] = pimpinan_inspektorat.id
        
        # 3. Validate nomor surat unique
        if await self.surat_tugas_repo.no_surat_exists(surat_tugas_data.no_surat):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nomor surat sudah ada"
            )
        
        # 4. Upload file surat tugas
        file_path = await evaluasi_file_manager.upload_surat_tugas_file(
            file, 
            surat_tugas_data.user_perwadag_id
        )
        
        try:
            # 5. Create surat tugas record DENGAN pimpinan_inspektorat_id otomatis
            # Gunakan data yang sudah include pimpinan_inspektorat_id
            surat_tugas = await self.surat_tugas_repo.create(surat_tugas_data_with_pimpinan, file_path)
            
            # 6. AUTO-GENERATE related records
            auto_generated_records = await self._auto_generate_related_records(surat_tugas.id)
            
            # 7. Build response
            surat_tugas_response = await self._build_surat_tugas_response(surat_tugas)
            
            return SuratTugasCreateResponse(
                success=True,
                message=f"Surat tugas berhasil dibuat dengan pimpinan inspektorat otomatis: {pimpinan_inspektorat.nama}",
                surat_tugas=surat_tugas_response,
                auto_generated_records=auto_generated_records,
                data={
                    "surat_tugas_id": surat_tugas.id,
                    "pimpinan_inspektorat_id": pimpinan_inspektorat.id,
                    "pimpinan_inspektorat_nama": pimpinan_inspektorat.nama,
                    "inspektorat": inspektorat_perwadag,
                    "auto_generated_count": len(auto_generated_records),
                    "auto_generated_records": auto_generated_records
                }
            )
            
        except Exception as e:
            # Cleanup uploaded file if database operations fail
            evaluasi_file_manager.delete_file(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal membuat surat tugas: {str(e)}"
            )
    
    async def _auto_generate_related_records(self, surat_tugas_id: str) -> Dict[str, str]:
        """
        Auto-generate semua related records untuk surat tugas baru.
        
        Returns dict dengan IDs dari generated records.
        """
        auto_generated = {}
        
        try:
            # 1. Generate surat_pemberitahuan
            surat_pemberitahuan = await self.surat_pemberitahuan_repo.create(
                SuratPemberitahuanCreate(surat_tugas_id=surat_tugas_id)
            )
            auto_generated["surat_pemberitahuan_id"] = surat_pemberitahuan.id
            
            # 2. Generate 3 meetings
            from src.models.evaluasi_enums import MeetingType
            from src.schemas.meeting import MeetingCreate
            
            meeting_types = [MeetingType.ENTRY, MeetingType.KONFIRMASI, MeetingType.EXIT]
            
            for meeting_type in meeting_types:
                meeting_data = MeetingCreate(
                    surat_tugas_id=surat_tugas_id,
                    meeting_type=meeting_type
                )
                meeting = await self.meeting_repo.create(meeting_data)
                auto_generated[f"{meeting.meeting_type.value}_meeting_id"] = meeting.id

            # 3. Generate matriks
            matriks = await self.matriks_repo.create(
                MatriksCreate(surat_tugas_id=surat_tugas_id)
            )
            auto_generated["matriks_id"] = matriks.id
            
            # 4. Generate laporan_hasil
            laporan_hasil = await self.laporan_hasil_repo.create(
                LaporanHasilCreate(surat_tugas_id=surat_tugas_id)
            )
            auto_generated["laporan_hasil_id"] = laporan_hasil.id
            
            # 5. Generate kuisioner
            kuisioner = await self.kuisioner_repo.create(
                KuisionerCreate(surat_tugas_id=surat_tugas_id)
            )
            auto_generated["kuisioner_id"] = kuisioner.id
            
            return auto_generated
            
        except Exception as e:
            # If any auto-generate fails, we should cleanup
            # But let the main transaction handle the rollback
            raise Exception(f"Auto-generate gagal: {str(e)}")
    
    # ===== CRUD OPERATIONS =====
    
    async def get_surat_tugas_or_404(self, surat_tugas_id: str) -> SuratTugasResponse:
        """Get surat tugas by ID or raise 404."""
        surat_tugas = await self.surat_tugas_repo.get_by_id(surat_tugas_id)
        if not surat_tugas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas tidak ditemukan"
            )
        
        return await self._build_surat_tugas_response(surat_tugas)
    
    async def get_all_surat_tugas(
        self,
        filters: SuratTugasFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> SuratTugasListResponse:
        """Get all surat tugas dengan filtering berdasarkan role."""
        
        surat_tugas_list, total = await self.surat_tugas_repo.get_all_filtered(
            filters, user_role, user_inspektorat, user_id
        )
        
        # Build responses
        surat_tugas_responses = []
        for surat_tugas in surat_tugas_list:
            response = await self._build_surat_tugas_response(surat_tugas)
            surat_tugas_responses.append(response)
        
        # Calculate pages
        pages = (total + filters.size - 1) // filters.size if total > 0 else 0
        
        return SuratTugasListResponse(
            items=surat_tugas_responses,
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )
    
    async def update_surat_tugas(
        self,
        surat_tugas_id: str,
        surat_tugas_data: SuratTugasUpdate,
        user_id: str
    ) -> SuratTugasResponse:
        """Update surat tugas."""
        
        # Check if surat tugas exists
        surat_tugas = await self.surat_tugas_repo.get_by_id(surat_tugas_id)
        if not surat_tugas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas tidak ditemukan"
            )
        
        # Validate nomor surat unique if being updated
        if surat_tugas_data.no_surat:
            if await self.surat_tugas_repo.no_surat_exists(
                surat_tugas_data.no_surat, 
                exclude_id=surat_tugas_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nomor surat sudah ada"
                )
        
        # Update surat tugas
        updated_surat_tugas = await self.surat_tugas_repo.update(surat_tugas_id, surat_tugas_data)
        
        return await self._build_surat_tugas_response(updated_surat_tugas)

    async def delete_surat_tugas(
        self,
        surat_tugas_id: str,
        user_role: str,
        user_id: str
    ) -> SuccessResponse:
        """
        Delete surat tugas dengan CASCADE DELETE ke semua related records.
        
        Workflow:
        1. Check if surat tugas exists
        2. Get all related data untuk file cleanup
        3. Delete all files from storage
        4. Soft delete all related records (CASCADE)
        5. Soft delete surat tugas
        """
        
        # 1. Check if surat tugas exists
        surat_tugas = await self.surat_tugas_repo.get_by_id(surat_tugas_id)
        if not surat_tugas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas tidak ditemukan"
            )
        
        try:
            # 2. Get all file paths untuk deletion
            file_paths_to_delete = await self._get_all_file_paths_for_surat_tugas(surat_tugas_id)
            
            # 3. Delete all files from storage
            file_deletion_result = {"deleted": 0, "failed": 0, "total": 0}
            if file_paths_to_delete:
                # Handle potential errors in file deletion
                try:
                    file_deletion_result = evaluasi_file_manager.delete_multiple_files(file_paths_to_delete)
                except Exception as file_error:
                    # Log file deletion errors but don't fail the entire operation
                    print(f"Peringatan: Beberapa file tidak dapat dihapus: {str(file_error)}")
                    file_deletion_result = {"deleted": 0, "failed": len(file_paths_to_delete), "total": len(file_paths_to_delete)}
            
            # 4. Cascade soft delete all related records
            cascade_result = await self._cascade_delete_related_records(surat_tugas_id)
            
            # 5. Delete surat tugas itself
            surat_tugas_deleted = await self.surat_tugas_repo.soft_delete(surat_tugas_id)
            
            if not surat_tugas_deleted:
                raise Exception("Gagal menghapus record surat tugas")
            
            # Calculate total cascade deletions
            total_cascade_deletions = sum(cascade_result.values())
            
            return SuccessResponse(
                success=True,
                message=f"Surat tugas {surat_tugas.no_surat} berhasil dihapus beserta semua data terkait",
                data={
                    "deleted_surat_tugas_id": surat_tugas_id,
                    "file_deletion": file_deletion_result,
                    "cascade_deleted": True,
                    "cascade_deletions": cascade_result,
                    "total_cascade_deletions": total_cascade_deletions
                }
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menghapus surat tugas: {str(e)}"
            )

    async def delete_file(
        self,
        surat_tugas_id: str,
        filename: str,
        deleted_by: str,
        current_user: dict = None
    ) -> FileDeleteResponse:
        """Delete file surat tugas by filename."""
        
        # 1. Get surat tugas
        surat_tugas = await self.surat_tugas_repo.get_by_id(surat_tugas_id)
        if not surat_tugas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas tidak ditemukan"
            )
        
        # 2. Check file exists
        if not surat_tugas.file_surat_tugas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tidak ada file untuk dihapus"
            )
        
        # 3. Validate filename matches
        current_filename = evaluasi_file_manager.extract_filename_from_path(surat_tugas.file_surat_tugas)
        if current_filename != filename:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{filename}' tidak ditemukan"
            )
        
        try:
            # 4. Store file path for deletion
            file_to_delete = surat_tugas.file_surat_tugas
            
            # 5. Clear database field FIRST
            updated_surat_tugas = await self.surat_tugas_repo.update_file_path(surat_tugas_id, "")
            if not updated_surat_tugas:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Gagal memperbarui database"
                )
            
            # 6. Set deleted_by
            updated_surat_tugas.updated_by = deleted_by
            await self.surat_tugas_repo.session.commit()
            
            # 7. Delete file from storage
            storage_deleted = evaluasi_file_manager.delete_file(file_to_delete)
            
            return FileDeleteResponse(
                success=True,
                message=f"File '{filename}' berhasil dihapus",
                entity_id=surat_tugas_id,
                deleted_filename=filename,
                file_type="single",
                remaining_files=0,
                storage_deleted=storage_deleted,
                database_updated=True
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menghapus file: {str(e)}"
            )
            
    async def _get_all_file_paths_for_surat_tugas(self, surat_tugas_id: str) -> List[str]:
        """Get semua file paths terkait surat tugas untuk deletion."""
        file_paths = []
        
        try:
            # 1. Get surat tugas file
            surat_tugas = await self.surat_tugas_repo.get_by_id(surat_tugas_id)
            if surat_tugas and surat_tugas.file_surat_tugas:
                file_paths.append(surat_tugas.file_surat_tugas)
            
            # 2. Get surat pemberitahuan file
            surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_surat_tugas_id(surat_tugas_id)
            if surat_pemberitahuan and surat_pemberitahuan.file_dokumen:
                file_paths.append(surat_pemberitahuan.file_dokumen)
            
            # 3. Get all meeting files (PERBAIKAN: gunakan method yang benar)
            meetings = await self.meeting_repo.get_all_by_surat_tugas_id(surat_tugas_id)
            for meeting in meetings:
                # Check file_bukti_hadir yang mungkin berisi JSON array
                if meeting.file_bukti_hadir:
                    try:
                        # Coba parse sebagai JSON jika berisi multiple files
                        import json
                        files_data = json.loads(meeting.file_bukti_hadir)
                        if isinstance(files_data, list):
                            # Multiple files format
                            for file_data in files_data:
                                if isinstance(file_data, dict) and 'path' in file_data:
                                    file_paths.append(file_data['path'])
                        elif isinstance(files_data, dict) and 'path' in files_data:
                            # Single file format
                            file_paths.append(files_data['path'])
                    except (json.JSONDecodeError, TypeError):
                        # Single file path format (string)
                        file_paths.append(meeting.file_bukti_hadir)
            
            # 4. Get matriks file
            matriks = await self.matriks_repo.get_by_surat_tugas_id(surat_tugas_id)
            if matriks and matriks.file_dokumen_matriks:
                file_paths.append(matriks.file_dokumen_matriks)
            
            # 5. Get laporan hasil file
            laporan_hasil = await self.laporan_hasil_repo.get_by_surat_tugas_id(surat_tugas_id)
            if laporan_hasil and laporan_hasil.file_laporan_hasil:
                file_paths.append(laporan_hasil.file_laporan_hasil)
            
            # 6. Get kuisioner file
            kuisioner = await self.kuisioner_repo.get_by_surat_tugas_id(surat_tugas_id)
            if kuisioner and kuisioner.file_kuisioner:
                file_paths.append(kuisioner.file_kuisioner)
            
            return file_paths
            
        except Exception as e:
            # Log error but don't fail the delete process
            print(f"Peringatan: Error mendapatkan file paths untuk surat tugas {surat_tugas_id}: {str(e)}")
            return file_paths

    async def _cascade_delete_related_records(self, surat_tugas_id: str) -> Dict[str, int]:
        """Cascade delete semua related records."""
        deleted_counts = {}
        
        try:
            # 1. Delete surat pemberitahuan
            surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_surat_tugas_id(surat_tugas_id)
            if surat_pemberitahuan:
                await self.surat_pemberitahuan_repo.soft_delete(surat_pemberitahuan.id)
                deleted_counts["surat_pemberitahuan"] = 1
            else:
                deleted_counts["surat_pemberitahuan"] = 0
            
            # 2. Delete all meetings
            meetings = await self.meeting_repo.get_all_by_surat_tugas_id(surat_tugas_id)
            meeting_count = 0
            for meeting in meetings:
                await self.meeting_repo.soft_delete(meeting.id)
                meeting_count += 1
            deleted_counts["meetings"] = meeting_count
            
            # 3. Delete matriks
            matriks = await self.matriks_repo.get_by_surat_tugas_id(surat_tugas_id)
            if matriks:
                await self.matriks_repo.soft_delete(matriks.id)
                deleted_counts["matriks"] = 1
            else:
                deleted_counts["matriks"] = 0
            
            # 4. Delete laporan hasil
            laporan_hasil = await self.laporan_hasil_repo.get_by_surat_tugas_id(surat_tugas_id)
            if laporan_hasil:
                await self.laporan_hasil_repo.soft_delete(laporan_hasil.id)
                deleted_counts["laporan_hasil"] = 1
            else:
                deleted_counts["laporan_hasil"] = 0
            
            # 5. Delete kuisioner
            kuisioner = await self.kuisioner_repo.get_by_surat_tugas_id(surat_tugas_id)
            if kuisioner:
                await self.kuisioner_repo.soft_delete(kuisioner.id)
                deleted_counts["kuisioner"] = 1
            else:
                deleted_counts["kuisioner"] = 0
            
            return deleted_counts
            
        except Exception as e:
            raise Exception(f"Gagal cascade delete related records: {str(e)}")
    
    # ===== FILE OPERATIONS =====
    
    async def upload_surat_tugas_file(
        self,
        surat_tugas_id: str,
        file: UploadFile,
        user_id: str
    ) -> SuccessResponse:
        """Upload or replace file surat tugas."""
        
        surat_tugas = await self.surat_tugas_repo.get_by_id(surat_tugas_id)
        if not surat_tugas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas tidak ditemukan"
            )
        
        # Delete old file if exists
        if surat_tugas.file_surat_tugas:
            evaluasi_file_manager.delete_file(surat_tugas.file_surat_tugas)
        
        # Upload new file
        file_path = await evaluasi_file_manager.upload_surat_tugas_file(file, surat_tugas_id)
        
        # Update database
        await self.surat_tugas_repo.update_file_path(surat_tugas_id, file_path)
        
        return SuccessResponse(
            success=True,
            message="File surat tugas berhasil diunggah",
            data={
                "surat_tugas_id": surat_tugas_id,
                "file_path": file_path,
                "file_url": evaluasi_file_manager.get_file_url(file_path)
            }
        )
    
    # ===== PROGRESS & OVERVIEW =====
    
    async def get_surat_tugas_overview(self, surat_tugas_id: str) -> SuratTugasOverview:
        """Get complete overview surat tugas dengan semua related data."""
        
        # Get surat tugas
        surat_tugas_response = await self.get_surat_tugas_or_404(surat_tugas_id)
        
        # Get all related data
        surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_surat_tugas_id(surat_tugas_id)
        meetings = await self.meeting_repo.get_all_by_surat_tugas(surat_tugas_id)
        matriks = await self.matriks_repo.get_by_surat_tugas_id(surat_tugas_id)
        laporan_hasil = await self.laporan_hasil_repo.get_by_surat_tugas_id(surat_tugas_id)
        kuisioner = await self.kuisioner_repo.get_by_surat_tugas_id(surat_tugas_id)
        
        return SuratTugasOverview(
            surat_tugas=surat_tugas_response,
            surat_pemberitahuan=surat_pemberitahuan.model_dump() if surat_pemberitahuan else None,
            meetings=[meeting.model_dump() for meeting in meetings],
            matriks=matriks.model_dump() if matriks else None,
            laporan_hasil=laporan_hasil.model_dump() if laporan_hasil else None,
            kuisioner=kuisioner.model_dump() if kuisioner else None
        )
    
    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> SuratTugasStats:
        """Get statistik surat tugas berdasarkan role."""
        
        stats_data = await self.surat_tugas_repo.get_statistics(
            user_role, user_inspektorat, user_id
        )
        
        return SuratTugasStats(**stats_data)
    
    async def get_dashboard_summary_with_completion_stats(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None,
        year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get dashboard summary dengan completion statistics per relationship.
        
        ROMBAK TOTAL: Menggunakan repository method baru dan menghitung
        completion stats dari related records secara langsung.
        """
        
        # Get surat tugas data dari repository dengan year filter
        surat_tugas_list = await self.surat_tugas_repo.get_dashboard_completion_data(
            user_role, user_inspektorat, user_id, year
        )


        # Initialize completion counters
        completion_stats = {
            "surat_pemberitahuan": {"completed": 0, "total": 0},
            "entry_meeting": {"completed": 0, "total": 0},
            "konfirmasi_meeting": {"completed": 0, "total": 0},
            "exit_meeting": {"completed": 0, "total": 0},
            "matriks": {"completed": 0, "total": 0},
            "laporan_hasil": {"completed": 0, "total": 0},
            "kuisioner": {"completed": 0, "total": 0}
        }
        
        overall_progress_sum = 0
        total_evaluasi = len(surat_tugas_list)
        recent_surat_tugas_data = []
      
        # Process each surat tugas untuk completion statistics
        for i, surat_tugas in enumerate(surat_tugas_list):
            
            # Get related records untuk setiap surat tugas
            surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_surat_tugas_id(surat_tugas.id)
            meetings = await self.meeting_repo.get_all_by_surat_tugas_id(surat_tugas.id)
            matriks = await self.matriks_repo.get_by_surat_tugas_id(surat_tugas.id)
            laporan_hasil = await self.laporan_hasil_repo.get_by_surat_tugas_id(surat_tugas.id)
            kuisioner = await self.kuisioner_repo.get_by_surat_tugas_id(surat_tugas.id)
            
            # Check completion status per relationship
            surat_pemberitahuan_completed = surat_pemberitahuan.is_completed() if surat_pemberitahuan else False
            
            # Check meetings completion by type
            entry_meeting_completed = False
            konfirmasi_meeting_completed = False
            exit_meeting_completed = False

            for meeting in meetings:
                if meeting.meeting_type == MeetingType.ENTRY and meeting.is_completed():
                    entry_meeting_completed = True
                elif meeting.meeting_type == MeetingType.KONFIRMASI and meeting.is_completed():
                    konfirmasi_meeting_completed = True
                elif meeting.meeting_type == MeetingType.EXIT and meeting.is_completed():
                    exit_meeting_completed = True
            
            matriks_completed = matriks.is_completed() if matriks else False
            laporan_completed = laporan_hasil.is_completed() if laporan_hasil else False
            kuisioner_completed = kuisioner.is_completed() if kuisioner else False

            
            # Count completions per relationship
            if surat_pemberitahuan_completed:
                completion_stats["surat_pemberitahuan"]["completed"] += 1
            completion_stats["surat_pemberitahuan"]["total"] += 1
            
            if entry_meeting_completed:
                completion_stats["entry_meeting"]["completed"] += 1
            completion_stats["entry_meeting"]["total"] += 1
            
            if konfirmasi_meeting_completed:
                completion_stats["konfirmasi_meeting"]["completed"] += 1
            completion_stats["konfirmasi_meeting"]["total"] += 1
            
            if exit_meeting_completed:
                completion_stats["exit_meeting"]["completed"] += 1
            completion_stats["exit_meeting"]["total"] += 1
            
            if matriks_completed:
                completion_stats["matriks"]["completed"] += 1
            completion_stats["matriks"]["total"] += 1
            
            if laporan_completed:
                completion_stats["laporan_hasil"]["completed"] += 1
            completion_stats["laporan_hasil"]["total"] += 1
            
            if kuisioner_completed:
                completion_stats["kuisioner"]["completed"] += 1
            completion_stats["kuisioner"]["total"] += 1
            
            # Calculate individual progress for this surat tugas
            completed_stages = sum([
                surat_pemberitahuan_completed,
                entry_meeting_completed,
                konfirmasi_meeting_completed,
                exit_meeting_completed,
                matriks_completed,
                laporan_completed,
                kuisioner_completed
            ])
            individual_progress = int((completed_stages / 7) * 100)
            overall_progress_sum += individual_progress
            
            # Collect recent surat tugas data (first 5)
            if i < 5:
                # Build full response untuk recent data menggunakan existing method
                full_response = await self._build_surat_tugas_response(surat_tugas)
                recent_data = full_response.model_dump()
                recent_data["progress_percentage"] = individual_progress
                recent_surat_tugas_data.append(recent_data)
        
        # Calculate completion percentages
        completion_percentages = {}
        for relationship, stats in completion_stats.items():
            if stats["total"] > 0:
                percentage = int((stats["completed"] / stats["total"]) * 100)
                completion_percentages[relationship] = {
                    "completed": stats["completed"],
                    "total": stats["total"],
                    "percentage": percentage,
                    "remaining": stats["total"] - stats["completed"]
                }
            else:
                completion_percentages[relationship] = {
                    "completed": 0,
                    "total": 0,
                    "percentage": 0,
                    "remaining": 0
                }
        
        # Calculate overall statistics
        average_progress = int(overall_progress_sum / total_evaluasi) if total_evaluasi > 0 else 0
        
        # Convert completion_percentages to proper format untuk schema
        from src.schemas.surat_tugas import (
            DashboardStatistics, RelationshipCompletionStats, RelationshipSummary,
            CompletionStats, RecentSuratTugasItem
        )
        
        # Build completion stats objects
        completion_stats_objects = {}
        for relationship, stats in completion_percentages.items():
            completion_stats_objects[relationship] = CompletionStats(**stats)
        
        # Build recent surat tugas objects
        recent_items = [RecentSuratTugasItem(**item) for item in recent_surat_tugas_data]
        
        # Get total perwadag count for admin/inspektorat (not affected by year filter)
        total_perwadag = None
        if user_role in ["ADMIN", "INSPEKTORAT"] and self.user_repo:
            total_perwadag = await self.user_repo.get_total_perwadag_count(
                user_role, user_inspektorat
            )
        
        return {
            "statistics": DashboardStatistics(
                total_perwadag=total_perwadag,
                average_progress=average_progress,
                year_filter_applied=year is not None,
                filtered_year=year
            ),
            "completion_stats": RelationshipCompletionStats(**completion_stats_objects),
            "recent_surat_tugas": recent_items,
            "summary_by_relationship": RelationshipSummary(
                most_completed=max(completion_percentages.items(), 
                                 key=lambda x: x[1]["percentage"])[0] if completion_percentages else None,
                least_completed=min(completion_percentages.items(), 
                                  key=lambda x: x[1]["percentage"])[0] if completion_percentages else None,
                total_relationships=len(completion_percentages),
                fully_completed_relationships=sum(1 for stats in completion_percentages.values() 
                                                if stats["percentage"] == 100)
            )
        }
    
    # ===== HELPER METHODS =====
    
    async def _build_surat_tugas_response(self, surat_tugas) -> SuratTugasResponse:
        """Build complete SuratTugasResponse dengan progress tracking dan file metadata."""
        
        # Get progress
        progress = await self._calculate_progress(surat_tugas.id)
        
        # Get perwadag info
        perwadag = await self.surat_tugas_repo.get_perwadag_by_id(surat_tugas.user_perwadag_id)
        if perwadag:
            perwadag_info = PerwardagSummary(
                id=perwadag.id,
                nama=perwadag.nama,
                inspektorat=perwadag.inspektorat
            )
        else:
            # Provide fallback when perwadag is not found
            perwadag_info = PerwardagSummary(
                id=surat_tugas.user_perwadag_id,
                nama=surat_tugas.nama_perwadag,
                inspektorat=surat_tugas.inspektorat
            )
        
        # Build file information
        file_urls = None
        file_metadata = None
        
        if surat_tugas.file_surat_tugas:
            file_urls = FileUrls(
                file_url=evaluasi_file_manager.get_file_url(surat_tugas.file_surat_tugas),
                download_url=f"/api/v1/surat-tugas/{surat_tugas.id}/download",
                view_url=f"/api/v1/surat-tugas/{surat_tugas.id}/view"
            )
            
            # Get file info
            file_info = evaluasi_file_manager.get_file_info(surat_tugas.file_surat_tugas)
            if file_info:
                file_metadata = FileMetadata(
                    filename=file_info['filename'],
                    original_filename=file_info.get('original_filename'),
                    size=file_info['size'],
                    size_mb=round(file_info['size'] / 1024 / 1024, 2),
                    content_type=file_info.get('content_type', 'application/octet-stream'),
                    extension=file_info.get('extension', ''),
                    uploaded_at=surat_tugas.updated_at or surat_tugas.created_at,
                    uploaded_by=surat_tugas.updated_by,
                    is_viewable=file_info.get('content_type', '').startswith(('image/', 'application/pdf'))
                )

        assignment_info = await self._get_assignment_info(surat_tugas)

        # Build response
        return SuratTugasResponse(
            id=surat_tugas.id,
            user_perwadag_id=surat_tugas.user_perwadag_id,
            nama_perwadag=surat_tugas.nama_perwadag,
            inspektorat=surat_tugas.inspektorat,
            tanggal_evaluasi_mulai=surat_tugas.tanggal_evaluasi_mulai,
            tanggal_evaluasi_selesai=surat_tugas.tanggal_evaluasi_selesai,
            no_surat=surat_tugas.no_surat,
            file_surat_tugas=surat_tugas.file_surat_tugas,

            assignment_info=assignment_info,
            
            # TAMBAHAN BARU:
            file_urls=file_urls,
            file_metadata=file_metadata,
            
            tahun_evaluasi=surat_tugas.tahun_evaluasi,
            durasi_evaluasi=surat_tugas.durasi_evaluasi,
            is_evaluation_active=surat_tugas.is_evaluation_active(),
            evaluation_status=surat_tugas.get_evaluation_status(),
            progress=progress,
            perwadag_info=perwadag_info,
            file_surat_tugas_url=evaluasi_file_manager.get_file_url(surat_tugas.file_surat_tugas),
            created_at=surat_tugas.created_at,
            updated_at=surat_tugas.updated_at,
            created_by=surat_tugas.created_by,
            updated_by=surat_tugas.updated_by
        )

    async def _get_assignment_info(self, surat_tugas) -> AssignmentInfo:
        """Get assignment information dengan user details."""
        
        from src.schemas.surat_tugas import AssignmentInfo
        from src.schemas.user import UserSummary
        from src.models.user import User
        from sqlalchemy import select
        
        assignment_info = AssignmentInfo()
        
        # Helper function untuk create UserSummary
        def create_user_summary(user: User) -> UserSummary:
            return UserSummary(
                id=user.id,
                nama=user.nama,
                username=user.username,
                jabatan=user.jabatan,
                role=user.role,
                role_display=user.get_role_display(),
                inspektorat=user.inspektorat,
                has_email=user.has_email(),
                is_active=user.is_active
            )
        
        # Get pengedali mutu
        if surat_tugas.pengedali_mutu_id:
            query = select(User).where(User.id == surat_tugas.pengedali_mutu_id)
            result = await self.surat_tugas_repo.session.execute(query)
            user = result.scalar_one_or_none()
            if user:
                assignment_info.pengedali_mutu = create_user_summary(user)
        
        # Get pengendali teknis
        if surat_tugas.pengendali_teknis_id:
            query = select(User).where(User.id == surat_tugas.pengendali_teknis_id)
            result = await self.surat_tugas_repo.session.execute(query)
            user = result.scalar_one_or_none()
            if user:
                assignment_info.pengendali_teknis = create_user_summary(user)
        
        # Get ketua tim
        if surat_tugas.ketua_tim_id:
            query = select(User).where(User.id == surat_tugas.ketua_tim_id)
            result = await self.surat_tugas_repo.session.execute(query)
            user = result.scalar_one_or_none()
            if user:
                assignment_info.ketua_tim = create_user_summary(user)
        
        # Get pimpinan inspektorat
        if surat_tugas.pimpinan_inspektorat_id:
            query = select(User).where(User.id == surat_tugas.pimpinan_inspektorat_id)
            result = await self.surat_tugas_repo.session.execute(query)
            user = result.scalar_one_or_none()
            if user:
                assignment_info.pimpinan_inspektorat = create_user_summary(user)
        
        # Get anggota tim
        anggota_tim_ids = surat_tugas.get_anggota_tim_list()
        if anggota_tim_ids:
            for user_id in anggota_tim_ids:
                query = select(User).where(User.id == user_id)
                result = await self.surat_tugas_repo.session.execute(query)
                user = result.scalar_one_or_none()
                if user:
                    assignment_info.anggota_tim.append(create_user_summary(user))
        
        return assignment_info
    
    async def _calculate_progress(self, surat_tugas_id: str) -> EvaluasiProgress:
        """Calculate progress evaluasi berdasarkan completion status semua related records."""
        
        # Get all related data dengan error handling
        surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_surat_tugas_id(surat_tugas_id)
        meetings = await self.meeting_repo.get_all_by_surat_tugas_id(surat_tugas_id)  # PERBAIKAN: nama method yang benar
        matriks = await self.matriks_repo.get_by_surat_tugas_id(surat_tugas_id)
        laporan_hasil = await self.laporan_hasil_repo.get_by_surat_tugas_id(surat_tugas_id)
        kuisioner = await self.kuisioner_repo.get_by_surat_tugas_id(surat_tugas_id)
        
        # Check completion status
        surat_pemberitahuan_completed = surat_pemberitahuan.is_completed() if surat_pemberitahuan else False
        
        # Check meetings completion
        entry_meeting_completed = False
        konfirmasi_meeting_completed = False
        exit_meeting_completed = False
        
        for meeting in meetings:
            if meeting.meeting_type == MeetingType.ENTRY:
                entry_meeting_completed = meeting.is_completed()
            elif meeting.meeting_type == MeetingType.KONFIRMASI:
                konfirmasi_meeting_completed = meeting.is_completed()
            elif meeting.meeting_type == MeetingType.EXIT:
                exit_meeting_completed = meeting.is_completed()
        
        matriks_completed = matriks.is_completed() if matriks else False
        laporan_completed = laporan_hasil.is_completed() if laporan_hasil else False
        kuisioner_completed = kuisioner.is_completed() if kuisioner else False
        
        # Calculate overall percentage
        completed_stages = sum([
            surat_pemberitahuan_completed,
            entry_meeting_completed,
            konfirmasi_meeting_completed,
            exit_meeting_completed,
            matriks_completed,
            laporan_completed,
            kuisioner_completed
        ])
        
        overall_percentage = int((completed_stages / 7) * 100)
        
        return EvaluasiProgress(
            surat_pemberitahuan_completed=surat_pemberitahuan_completed,
            entry_meeting_completed=entry_meeting_completed,
            konfirmasi_meeting_completed=konfirmasi_meeting_completed,
            exit_meeting_completed=exit_meeting_completed,
            matriks_completed=matriks_completed,
            laporan_completed=laporan_completed,
            kuisioner_completed=kuisioner_completed,
            overall_percentage=overall_percentage
        )

    async def download_file(
        self, 
        surat_tugas_id: str, 
        download_type: str = "download"
    ) -> FileResponse:
        """Download surat tugas file."""
        
        surat_tugas = await self.surat_tugas_repo.get_by_id(surat_tugas_id)
        if not surat_tugas or not surat_tugas.file_surat_tugas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File tidak ditemukan"
            )
        
        # Get original filename untuk download
        original_filename = f"surat_tugas_{surat_tugas.no_surat}_{surat_tugas_id}"
        
        return evaluasi_file_manager.get_file_download_response(
            file_path=surat_tugas.file_surat_tugas,
            original_filename=original_filename,
            download_type=download_type
        )
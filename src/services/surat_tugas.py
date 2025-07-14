"""Service untuk surat tugas dengan auto-generate workflow."""

from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status, UploadFile

from src.repositories.surat_tugas import SuratTugasRepository
from src.repositories.surat_pemberitahuan import SuratPemberitahuanRepository
from src.repositories.meeting import MeetingRepository
from src.repositories.matriks import MatriksRepository
from src.repositories.laporan_hasil import LaporanHasilRepository
from src.repositories.kuisioner import KuisionerRepository
from src.schemas.surat_tugas import (
    SuratTugasCreate, SuratTugasUpdate, SuratTugasResponse, 
    SuratTugasListResponse, SuratTugasCreateResponse, SuratTugasOverview,
    EvaluasiProgress, PerwardagSummary, SuratTugasStats
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


class SuratTugasService:
    """Service untuk surat tugas dengan auto-generate workflow."""
    
    def __init__(
        self,
        surat_tugas_repo: SuratTugasRepository,
        surat_pemberitahuan_repo: SuratPemberitahuanRepository,
        meeting_repo: MeetingRepository,
        matriks_repo: MatriksRepository,
        laporan_hasil_repo: LaporanHasilRepository,
        kuisioner_repo: KuisionerRepository
    ):
        self.surat_tugas_repo = surat_tugas_repo
        self.surat_pemberitahuan_repo = surat_pemberitahuan_repo
        self.meeting_repo = meeting_repo
        self.matriks_repo = matriks_repo
        self.laporan_hasil_repo = laporan_hasil_repo
        self.kuisioner_repo = kuisioner_repo
    
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
        1. Validate perwadag exists
        2. Validate nomor surat unique
        3. Upload file surat tugas
        4. Create surat tugas record
        5. AUTO-GENERATE 6 related records:
           - 1x surat_pemberitahuan (empty)
           - 3x meetings (entry, konfirmasi, exit - all empty)
           - 1x matriks (empty)
           - 1x laporan_hasil (empty)
           - 1x kuisioner (empty)
        6. Return complete response
        """
        
        # 1. Validate perwadag exists
        perwadag = await self.surat_tugas_repo.get_perwadag_by_id(surat_tugas_data.user_perwadag_id)
        if not perwadag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perwadag not found or not active"
            )
        
        # 2. Validate nomor surat unique
        if await self.surat_tugas_repo.no_surat_exists(surat_tugas_data.no_surat):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nomor surat already exists"
            )
        
        # 3. Upload file surat tugas
        file_path = await evaluasi_file_manager.upload_surat_tugas_file(
            file, 
            surat_tugas_data.user_perwadag_id
        )
        
        try:
            # 4. Create surat tugas record
            surat_tugas = await self.surat_tugas_repo.create(surat_tugas_data, file_path)
            
            # 5. AUTO-GENERATE related records
            auto_generated_records = await self._auto_generate_related_records(surat_tugas.id)
            
            # 6. Build response
            surat_tugas_response = await self._build_surat_tugas_response(surat_tugas)
            
            return SuratTugasCreateResponse(
                success=True,
                message="Surat tugas created successfully with auto-generated records",
                surat_tugas=surat_tugas_response,
                auto_generated_records=auto_generated_records,
                data={
                    "surat_tugas_id": surat_tugas.id,
                    "auto_generated_count": len(auto_generated_records),
                    "auto_generated_records": auto_generated_records
                }
            )
            
        except Exception as e:
            # Cleanup uploaded file if database operations fail
            evaluasi_file_manager.delete_file(file_path)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create surat tugas: {str(e)}"
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
            meetings = await self.meeting_repo.create_all_meetings_for_surat_tugas(surat_tugas_id)
            for meeting in meetings:
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
            raise Exception(f"Auto-generate failed: {str(e)}")
    
    # ===== CRUD OPERATIONS =====
    
    async def get_surat_tugas_or_404(self, surat_tugas_id: str) -> SuratTugasResponse:
        """Get surat tugas by ID or raise 404."""
        surat_tugas = await self.surat_tugas_repo.get_by_id(surat_tugas_id)
        if not surat_tugas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Surat tugas not found"
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
        pages = (total + filters.size - 1) // filters.size
        
        return SuratTugasListResponse(
            surat_tugas=surat_tugas_responses,
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
                detail="Surat tugas not found"
            )
        
        # Validate nomor surat unique if being updated
        if surat_tugas_data.no_surat:
            if await self.surat_tugas_repo.no_surat_exists(
                surat_tugas_data.no_surat, 
                exclude_id=surat_tugas_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Nomor surat already exists"
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
                detail="Surat tugas not found"
            )
        
        try:
            # 2. Get all file paths untuk deletion
            file_paths_to_delete = await self._get_all_file_paths_for_surat_tugas(surat_tugas_id)
            
            # 3. Delete all files from storage
            if file_paths_to_delete:
                deletion_result = evaluasi_file_manager.delete_multiple_files(file_paths_to_delete)
            
            # 4. Cascade soft delete all related records
            await self._cascade_delete_related_records(surat_tugas_id)
            
            # 5. Delete surat tugas itself
            await self.surat_tugas_repo.soft_delete(surat_tugas_id)
            
            return SuccessResponse(
                success=True,
                message=f"Surat tugas {surat_tugas.no_surat} deleted successfully with all related data",
                data={
                    "deleted_surat_tugas_id": surat_tugas_id,
                    "deleted_files_count": len(file_paths_to_delete),
                    "cascade_deleted": True
                }
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete surat tugas: {str(e)}"
            )
    
    async def _cascade_delete_related_records(self, surat_tugas_id: str) -> Dict[str, int]:
        """Cascade delete semua related records."""
        deleted_counts = {}
        
        # Delete all related records
        deleted_counts["surat_pemberitahuan"] = await self.surat_pemberitahuan_repo.soft_delete_by_surat_tugas(surat_tugas_id)
        deleted_counts["meetings"] = await self.meeting_repo.soft_delete_by_surat_tugas(surat_tugas_id)  
        deleted_counts["matriks"] = await self.matriks_repo.soft_delete_by_surat_tugas(surat_tugas_id)
        deleted_counts["laporan_hasil"] = await self.laporan_hasil_repo.soft_delete_by_surat_tugas(surat_tugas_id)
        deleted_counts["kuisioner"] = await self.kuisioner_repo.soft_delete_by_surat_tugas(surat_tugas_id)
        
        return deleted_counts
    
    async def _get_all_file_paths_for_surat_tugas(self, surat_tugas_id: str) -> List[str]:
        """Get semua file paths terkait surat tugas untuk deletion."""
        file_paths = []
        
        # Get surat tugas file
        surat_tugas = await self.surat_tugas_repo.get_by_id(surat_tugas_id)
        if surat_tugas and surat_tugas.file_surat_tugas:
            file_paths.append(surat_tugas.file_surat_tugas)
        
        # Get surat pemberitahuan file
        surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_surat_tugas_id(surat_tugas_id)
        if surat_pemberitahuan and surat_pemberitahuan.file_dokumen:
            file_paths.append(surat_pemberitahuan.file_dokumen)
        
        # Get all meeting files
        meetings = await self.meeting_repo.get_all_by_surat_tugas(surat_tugas_id)
        for meeting in meetings:
            meeting_file_paths = await self.meeting_repo.get_file_paths_for_deletion(meeting.id)
            file_paths.extend(meeting_file_paths)
        
        # Get matriks file
        matriks = await self.matriks_repo.get_by_surat_tugas_id(surat_tugas_id)
        if matriks and matriks.file_dokumen_matriks:
            file_paths.append(matriks.file_dokumen_matriks)
        
        # Get laporan hasil file
        laporan_hasil = await self.laporan_hasil_repo.get_by_surat_tugas_id(surat_tugas_id)
        if laporan_hasil and laporan_hasil.file_laporan_hasil:
            file_paths.append(laporan_hasil.file_laporan_hasil)
        
        # Get kuisioner file
        kuisioner = await self.kuisioner_repo.get_by_surat_tugas_id(surat_tugas_id)
        if kuisioner and kuisioner.file_kuisioner:
            file_paths.append(kuisioner.file_kuisioner)
        
        return file_paths
    
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
                detail="Surat tugas not found"
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
            message="File surat tugas uploaded successfully",
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
    
    # ===== HELPER METHODS =====
    
    async def _build_surat_tugas_response(self, surat_tugas) -> SuratTugasResponse:
        """Build complete SuratTugasResponse dengan progress tracking."""
        
        # Get progress
        progress = await self._calculate_progress(surat_tugas.id)
        
        # Get perwadag info
        perwadag = await self.surat_tugas_repo.get_perwadag_by_id(surat_tugas.user_perwadag_id)
        perwadag_info = PerwardagSummary(
            id=perwadag.id,
            nama=perwadag.nama,
            inspektorat=perwadag.inspektorat
        ) if perwadag else None
        
        return SuratTugasResponse(
            id=surat_tugas.id,
            user_perwadag_id=surat_tugas.user_perwadag_id,
            nama_perwadag=surat_tugas.nama_perwadag,
            inspektorat=surat_tugas.inspektorat,
            tanggal_evaluasi_mulai=surat_tugas.tanggal_evaluasi_mulai,
            tanggal_evaluasi_selesai=surat_tugas.tanggal_evaluasi_selesai,
            no_surat=surat_tugas.no_surat,
            nama_pengedali_mutu=surat_tugas.nama_pengedali_mutu,
            nama_pengendali_teknis=surat_tugas.nama_pengendali_teknis,
            nama_ketua_tim=surat_tugas.nama_ketua_tim,
            file_surat_tugas=surat_tugas.file_surat_tugas,
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
    
    async def _calculate_progress(self, surat_tugas_id: str) -> EvaluasiProgress:
        """Calculate progress evaluasi berdasarkan completion status semua related records."""
        
        # Get all related data
        surat_pemberitahuan = await self.surat_pemberitahuan_repo.get_by_surat_tugas_id(surat_tugas_id)
        meetings = await self.meeting_repo.get_all_by_surat_tugas(surat_tugas_id)
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
# ===== src/services/periode_evaluasi.py =====
"""Service untuk periode evaluasi."""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status

from src.repositories.periode_evaluasi import PeriodeEvaluasiRepository
from src.repositories.penilaian_risiko import PenilaianRisikoRepository
from src.schemas.periode_evaluasi import (
    PeriodeEvaluasiCreate, PeriodeEvaluasiUpdate, PeriodeEvaluasiResponse,
    PeriodeEvaluasiListResponse, PeriodeEvaluasiCreateResponse
)
from src.schemas.filters import PeriodeEvaluasiFilterParams
from src.schemas.common import SuccessResponse
from src.schemas.shared import PaginationInfo


class PeriodeEvaluasiService:
    """Service untuk periode evaluasi operations."""
    
    def __init__(
        self, 
        periode_repo: PeriodeEvaluasiRepository,
        penilaian_repo: PenilaianRisikoRepository
    ):
        self.periode_repo = periode_repo
        self.penilaian_repo = penilaian_repo
    
    async def create_periode_with_bulk_generate(
        self, 
        periode_data: PeriodeEvaluasiCreate,
        user_id: str
    ) -> PeriodeEvaluasiCreateResponse:
        """
        Create periode evaluasi baru dengan auto bulk generate penilaian risiko.
        
        Workflow:
        1. Validate tahun belum ada
        2. Create periode evaluasi
        3. Auto bulk generate penilaian risiko untuk semua perwadag aktif
        4. Return response dengan summary
        """
        
        # 1. Validate tahun belum ada
        if await self.periode_repo.tahun_exists(periode_data.tahun):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tahun periode sudah ada, silakan pilih tahun yang berbeda"
            )
        
        try:
            # 2. Create periode evaluasi
            periode = await self.periode_repo.create(periode_data)
            periode.created_by = user_id
            await self.periode_repo.session.commit()
            
            # 3. Auto bulk generate penilaian risiko
            bulk_result = await self.penilaian_repo.bulk_create_for_periode(periode.id)
            
            # 4. Build response
            periode_response = await self._build_periode_response(periode)
            
            return PeriodeEvaluasiCreateResponse(
                success=True,
                message=f"Periode evaluasi {periode.tahun} berhasil dibuat dengan {bulk_result['created']} penilaian risiko",
                periode_evaluasi=periode_response,
                bulk_generation_summary=bulk_result,
                data={
                    "periode_id": periode.id,
                    "tahun": periode.tahun,
                    "auto_generated_count": bulk_result['created'],
                    "skipped_count": bulk_result['skipped'],
                    "total_perwadag": bulk_result['total_perwadag']
                }
            )
            
        except Exception as e:
            # Cleanup jika ada error
            if 'periode' in locals():
                await self.periode_repo.hard_delete(periode.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal membuat periode evaluasi: {str(e)}"
            )
    
    async def get_all_periode_evaluasi(
        self, 
        filters: PeriodeEvaluasiFilterParams
    ) -> PeriodeEvaluasiListResponse:
        """Get all periode evaluasi dengan filtering."""
        
        enriched_data, total = await self.periode_repo.get_all_filtered(filters)
        
        # Build responses
        periode_responses = []
        for data in enriched_data:
            response = await self._build_periode_response(
                data['periode'],
                data['total_penilaian'],
                data['penilaian_completed'],
                data['completion_rate']
            )
            periode_responses.append(response)
        
        # Calculate pages
        pages = (total + filters.size - 1) // filters.size
        
        return PeriodeEvaluasiListResponse(
            periode_evaluasi=periode_responses,
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )
    
    async def get_periode_or_404(self, periode_id: str) -> PeriodeEvaluasiResponse:
        """Get periode evaluasi by ID or raise 404."""
        periode = await self.periode_repo.get_by_id(periode_id)
        if not periode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Periode evaluasi tidak ditemukan"
            )
        
        return await self._build_periode_response(periode)
    
    async def update_periode_evaluasi(
        self,
        periode_id: str,
        periode_data: PeriodeEvaluasiUpdate,
        user_id: str
    ) -> PeriodeEvaluasiResponse:
        """Update periode evaluasi."""
        
        periode = await self.periode_repo.get_by_id(periode_id)
        if not periode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Periode evaluasi tidak ditemukan"
            )
        
        # Update periode
        updated_periode = await self.periode_repo.update(periode_id, periode_data)
        updated_periode.updated_by = user_id
        await self.periode_repo.session.commit()
        
        return await self._build_periode_response(updated_periode)
    
    async def delete_periode_evaluasi(
        self,
        periode_id: str,
        user_id: str
    ) -> SuccessResponse:
        """
        Delete periode evaluasi dengan cascade delete penilaian risiko.
        
        Hard delete karena data penilaian risiko tidak bermakna tanpa periode.
        """
        
        periode = await self.periode_repo.get_by_id(periode_id)
        if not periode:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Periode evaluasi tidak ditemukan"
            )
        
        try:
            # Get count penilaian yang akan dihapus untuk info
            count_query_result = await self.penilaian_repo.session.execute(
                "SELECT COUNT(*) FROM penilaian_risiko WHERE periode_id = :periode_id",
                {"periode_id": periode_id}
            )
            penilaian_count = count_query_result.scalar() or 0
            
            # Hard delete dengan cascade
            success = await self.periode_repo.hard_delete(periode_id)
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Gagal menghapus periode evaluasi"
                )
            
            return SuccessResponse(
                success=True,
                message=f"Periode evaluasi {periode.tahun} berhasil dihapus beserta {penilaian_count} data penilaian risiko",
                data={
                    "deleted_periode_id": periode_id,
                    "tahun": periode.tahun,
                    "deleted_penilaian_count": penilaian_count
                }
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menghapus periode evaluasi: {str(e)}"
            )
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistik periode evaluasi."""
        return await self.periode_repo.get_statistics()
    
    # ===== HELPER METHODS =====
    
    async def _build_periode_response(
        self, 
        periode,
        total_penilaian: int = 0,
        penilaian_completed: int = 0,
        completion_rate: float = 0.0
    ) -> PeriodeEvaluasiResponse:
        """Build periode evaluasi response dengan computed fields."""
        
        # Get tahun pembanding
        tahun_pembanding = periode.get_tahun_pembanding()
        
        return PeriodeEvaluasiResponse(
            id=periode.id,
            tahun=periode.tahun,
            is_locked=periode.is_locked,
            status=periode.status,
            is_editable=periode.is_editable(),
            status_display=periode.get_status_display(),
            lock_status_display=periode.get_lock_status_display(),
            tahun_pembanding_1=tahun_pembanding["tahun_pembanding_1"],
            tahun_pembanding_2=tahun_pembanding["tahun_pembanding_2"],
            total_penilaian=total_penilaian,
            penilaian_completed=penilaian_completed,
            completion_rate=completion_rate,
            created_at=periode.created_at,
            updated_at=periode.updated_at,
            created_by=periode.created_by,
            updated_by=periode.updated_by
        )
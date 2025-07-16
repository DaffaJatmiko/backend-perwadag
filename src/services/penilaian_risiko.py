# ===== src/services/penilaian_risiko.py =====
"""Service untuk penilaian risiko."""

from typing import Optional, Dict, Any
from decimal import Decimal
from fastapi import HTTPException, status

from src.repositories.penilaian_risiko import PenilaianRisikoRepository
from src.repositories.periode_evaluasi import PeriodeEvaluasiRepository
from src.repositories.user import UserRepository
from src.schemas.penilaian_risiko import (
    PenilaianRisikoUpdate, PenilaianRisikoResponse, PenilaianRisikoListResponse,
    PenilaianRisikoCalculateRequest, PenilaianRisikoCalculateResponse,
    PerwardagSummary, PeriodeSummary, KriteriaOptionsResponse
)
from src.schemas.filters import PenilaianRisikoFilterParams
from src.schemas.shared import PaginationInfo
from src.utils.penilaian_calculator import PenilaianRisikoCalculator


class PenilaianRisikoService:
    """Service untuk penilaian risiko operations."""
    
    def __init__(
        self,
        penilaian_repo: PenilaianRisikoRepository,
        periode_repo: PeriodeEvaluasiRepository,
        user_repo: UserRepository
    ):
        self.penilaian_repo = penilaian_repo
        self.periode_repo = periode_repo
        self.user_repo = user_repo
        self.calculator = PenilaianRisikoCalculator()
    
    async def get_all_penilaian_risiko(
        self,
        filters: PenilaianRisikoFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> PenilaianRisikoListResponse:
        """Get all penilaian risiko dengan filtering berdasarkan role."""
        
        enriched_data, total = await self.penilaian_repo.get_all_filtered(
            filters, user_role, user_inspektorat, user_id
        )
        
        # Build responses
        penilaian_responses = []
        for data in enriched_data:
            response = await self._build_penilaian_response(
                data['penilaian'],
                data['perwadag_nama'],
                data['periode_status'],
                data['periode_locked']
            )
            penilaian_responses.append(response)
        
        # Get statistics if requested
        statistics = None
        if hasattr(filters, 'include_statistics') and filters.include_statistics:
            statistics = await self.penilaian_repo.get_statistics(
                user_role, user_inspektorat, user_id
            )
        
        pages = (total + filters.size - 1) // filters.size if total > 0 else 0

        response = PenilaianRisikoListResponse(
            items=penilaian_responses,  # ✅ penilaian_risiko → items
            total=total,
            page=filters.page,
            size=filters.size,
            pages=pages
        )

        if hasattr(filters, 'include_statistics') and filters.include_statistics:
            response.statistics = statistics

        return response
    
    async def get_penilaian_or_404(self, penilaian_id: str) -> PenilaianRisikoResponse:
        """Get penilaian risiko by ID or raise 404."""
        penilaian = await self.penilaian_repo.get_by_id(penilaian_id)
        if not penilaian:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data penilaian risiko tidak ditemukan"
            )
        
        return await self._build_penilaian_response(penilaian)
    
    async def update_penilaian_risiko(
        self,
        penilaian_id: str,
        penilaian_data: PenilaianRisikoUpdate,
        user_id: str,
        user_role: str,
        user_inspektorat: Optional[str] = None
    ) -> PenilaianRisikoResponse:
        """Update penilaian risiko dengan AUTO-CALCULATE logic - FIXED."""
        
        # 1. Get penilaian risiko
        penilaian = await self.penilaian_repo.get_by_id(penilaian_id)
        if not penilaian:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data penilaian risiko tidak ditemukan"
            )
        
        # 2. Validate access permission
        await self._validate_edit_access(penilaian, user_role, user_inspektorat)
        
        # 3. Validate periode masih editable
        if not await self.penilaian_repo.is_periode_editable(penilaian.periode_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Periode evaluasi telah dikunci dan tidak dapat diedit"
            )
        
        # ✅ 4. Extract auto_calculate BEFORE processing
        auto_calculate = penilaian_data.auto_calculate
        
        # 5. Process kriteria data jika ada
        if penilaian_data.kriteria_data:
            processed_kriteria = self.calculator.process_criteria_input(
                penilaian_data.kriteria_data
            )
            penilaian_data.kriteria_data = processed_kriteria
        
        # ✅ 6. Create clean data tanpa auto_calculate untuk repository
        clean_data = PenilaianRisikoUpdate(
            kriteria_data=penilaian_data.kriteria_data,
            catatan=penilaian_data.catatan
            # ❌ Tidak include auto_calculate
        )
        
        # 7. Update penilaian dengan clean data
        updated_penilaian = await self.penilaian_repo.update(penilaian_id, clean_data)
        updated_penilaian.updated_by = user_id
        await self.penilaian_repo.session.commit()
        
        # 🎯 8. AUTO-CALCULATE Logic berdasarkan extracted flag
        calculation_result = None
        if auto_calculate and updated_penilaian.is_calculation_complete():
            try:
                # Perform automatic calculation
                calculation_result = self.calculator.calculate_total_score(updated_penilaian.kriteria_data)
                
                # Update database dengan hasil kalkulasi
                updated_penilaian = await self.penilaian_repo.update_calculation_result(
                    penilaian_id,
                    calculation_result["total_nilai_risiko"],
                    calculation_result["skor_rata_rata"],
                    calculation_result["profil_risiko_auditan"]
                )
                updated_penilaian.updated_by = user_id
                await self.penilaian_repo.session.commit()
                
            except Exception as e:
                # Log error tapi jangan fail update data
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Auto-calculation failed for penilaian {penilaian_id}: {str(e)}")
        
        # 9. Build response
        response = await self._build_penilaian_response(updated_penilaian)
        
        # ✅ 10. Add calculation info ke response
        if calculation_result:
            # Convert Decimal to float untuk JSON serialization
            if hasattr(response, '__dict__'):
                response.calculation_performed = True
                response.calculation_details = {
                    **calculation_result,
                    "total_nilai_risiko": float(calculation_result["total_nilai_risiko"]),
                    "skor_rata_rata": float(calculation_result["skor_rata_rata"])
                }
            else:
                # Jika response adalah dict
                response = {
                    **response,
                    "calculation_performed": True,
                    "calculation_details": calculation_result
                }
        else:
            if hasattr(response, '__dict__'):
                response.calculation_performed = False
                response.calculation_details = None
            else:
                response = {
                    **response,
                    "calculation_performed": False,
                    "calculation_details": None
                }
        
        return response
    
    async def calculate_penilaian_risiko(
        self,
        penilaian_id: str,
        calculate_request: PenilaianRisikoCalculateRequest,
        user_id: str,
        user_role: str,
        user_inspektorat: Optional[str] = None
    ) -> PenilaianRisikoCalculateResponse:
        """Kalkulasi total nilai risiko dan profil risiko."""
        
        # 1. Get penilaian risiko
        penilaian = await self.penilaian_repo.get_by_id(penilaian_id)
        if not penilaian:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Data penilaian risiko tidak ditemukan"
            )
        
        # 2. Validate access permission
        await self._validate_edit_access(penilaian, user_role, user_inspektorat)
        
        # 3. Validate periode masih editable
        if not await self.penilaian_repo.is_periode_editable(penilaian.periode_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Periode evaluasi telah dikunci dan tidak dapat diedit"
            )
        
        # 4. Check if already calculated dan not forced
        if (penilaian.has_calculation_result() and 
            not calculate_request.force_recalculate):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Penilaian sudah dihitung. Gunakan force_recalculate=true untuk menghitung ulang"
            )
        
        # 5. Validate kriteria data lengkap
        if not penilaian.is_calculation_complete():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Data kriteria belum lengkap untuk menghitung total nilai risiko"
            )
        
        try:
            # 6. Perform calculation
            calculation_result = self.calculator.calculate_total_score(penilaian.kriteria_data)
            
            # 7. Update database dengan hasil kalkulasi
            updated_penilaian = await self.penilaian_repo.update_calculation_result(
                penilaian_id,
                calculation_result["total_nilai_risiko"],
                calculation_result["skor_rata_rata"],
                calculation_result["profil_risiko_auditan"]
            )
            updated_penilaian.updated_by = user_id
            await self.penilaian_repo.session.commit()
            
            # 8. Build response
            penilaian_response = await self._build_penilaian_response(updated_penilaian)
            
            return PenilaianRisikoCalculateResponse(
                success=True,
                message=f"Kalkulasi berhasil. Profil risiko: {calculation_result['profil_risiko_auditan']}",
                penilaian_risiko=penilaian_response,
                calculation_details=calculation_result,
                data=calculation_result
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Gagal menghitung penilaian risiko: {str(e)}"
            )
    
    async def get_kriteria_options(self) -> KriteriaOptionsResponse:
        """Get opsi-opsi untuk dropdown kriteria."""
        return KriteriaOptionsResponse.get_default_options()
    
    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistik penilaian risiko berdasarkan role."""
        return await self.penilaian_repo.get_statistics(
            user_role, user_inspektorat, user_id
        )
    
    # ===== VALIDATION METHODS =====
    
    async def _validate_edit_access(
        self, 
        penilaian, 
        user_role: str, 
        user_inspektorat: Optional[str] = None
    ) -> None:
        """Validate apakah user bisa edit penilaian risiko ini."""
        
        if user_role == "ADMIN":
            # Admin bisa edit semua
            return
        elif user_role == "INSPEKTORAT":
            # Inspektorat hanya bisa edit di wilayah kerjanya
            if user_inspektorat != penilaian.inspektorat:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Anda tidak memiliki akses untuk inspektorat ini"
                )
        else:
            # Role lain tidak bisa edit
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki akses untuk mengedit penilaian risiko"
            )
    
    # ===== HELPER METHODS =====
    
    async def _build_penilaian_response(
        self, 
        penilaian,
        perwadag_nama: Optional[str] = None,
        periode_status: Optional[str] = None,
        periode_locked: Optional[bool] = None
    ) -> PenilaianRisikoResponse:
        """Build penilaian risiko response dengan enriched data."""
        
        # Get perwadag info jika belum ada
        if not perwadag_nama:
            perwadag = await self.user_repo.get_by_id(penilaian.user_perwadag_id)
            if perwadag:
                perwadag_nama = perwadag.nama
        
        # Get periode info jika belum ada
        if periode_status is None or periode_locked is None:
            periode = await self.periode_repo.get_by_id(penilaian.periode_id)
            if periode:
                periode_status = periode.status.value
                periode_locked = periode.is_locked
        
        # Build summary objects
        perwadag_info = PerwardagSummary(
            id=penilaian.user_perwadag_id,
            nama=perwadag_nama or "Unknown",
            inspektorat=penilaian.inspektorat
        )
        
        periode_info = PeriodeSummary(
            id=penilaian.periode_id,
            tahun=penilaian.tahun,
            status=periode_status or "aktif",
            is_locked=periode_locked or False,
            is_editable=not (periode_locked or False) and (periode_status or "aktif") == "aktif"
        )
        
        return PenilaianRisikoResponse(
            id=penilaian.id,
            user_perwadag_id=penilaian.user_perwadag_id,
            periode_id=penilaian.periode_id,
            tahun=penilaian.tahun,
            inspektorat=penilaian.inspektorat,
            total_nilai_risiko=penilaian.total_nilai_risiko,
            skor_rata_rata=penilaian.skor_rata_rata,
            profil_risiko_auditan=penilaian.profil_risiko_auditan,
            catatan=penilaian.catatan,
            kriteria_data=penilaian.kriteria_data,
            is_calculation_complete=penilaian.is_calculation_complete(),
            has_calculation_result=penilaian.has_calculation_result(),
            completion_percentage=penilaian.get_completion_percentage(),
            profil_risiko_color=penilaian.get_profil_risiko_color(),
            perwadag_info=perwadag_info,
            periode_info=periode_info,
            nama_perwadag=perwadag_nama or "Unknown",
            periode_tahun=penilaian.tahun,
            periode_status=periode_status or "aktif",
            created_at=penilaian.created_at,
            updated_at=penilaian.updated_at,
            created_by=penilaian.created_by,
            updated_by=penilaian.updated_by
        )

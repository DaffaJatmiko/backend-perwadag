# ===== src/repositories/penilaian_risiko.py =====
"""Repository untuk penilaian risiko."""

from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.penilaian_risiko import PenilaianRisiko
from src.models.periode_evaluasi import PeriodeEvaluasi
from src.models.user import User
from src.models.enums import UserRole
from src.schemas.penilaian_risiko import PenilaianRisikoUpdate
from src.schemas.filters import PenilaianRisikoFilterParams


class PenilaianRisikoRepository:
    """Repository untuk operasi penilaian risiko."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # ===== CREATE OPERATIONS =====
    
    async def create(
        self, 
        user_perwadag_id: str, 
        periode_id: str, 
        kriteria_data: Dict[str, Any]
    ) -> PenilaianRisiko:
        """Create penilaian risiko baru."""
        
        # Get periode info
        periode = await self.session.get(PeriodeEvaluasi, periode_id)
        if not periode:
            raise ValueError("Periode evaluasi not found")
        
        # Get perwadag info
        perwadag = await self.session.get(User, user_perwadag_id)
        if not perwadag or perwadag.role != UserRole.PERWADAG:
            raise ValueError("Perwadag not found")
        
        penilaian = PenilaianRisiko(
            user_perwadag_id=user_perwadag_id,
            periode_id=periode_id,
            tahun=periode.tahun,
            inspektorat=perwadag.inspektorat,
            kriteria_data=kriteria_data
        )
        
        self.session.add(penilaian)
        await self.session.commit()
        await self.session.refresh(penilaian)
        return penilaian
    
    async def bulk_create_for_periode(self, periode_id: str) -> Dict[str, int]:
        """Bulk create penilaian risiko untuk semua perwadag aktif."""
        
        # Get periode info
        periode = await self.session.get(PeriodeEvaluasi, periode_id)
        if not periode:
            raise ValueError("Periode evaluasi not found")
        
        # Get all active perwadag
        perwadag_query = select(User).where(
            and_(
                User.role == UserRole.PERWADAG,
                User.is_active == True,
                User.deleted_at.is_(None)
            )
        )
        perwadag_result = await self.session.execute(perwadag_query)
        perwadag_list = perwadag_result.scalars().all()
        
        # Generate tahun pembanding
        tahun_pembanding = periode.get_tahun_pembanding()
        
        # Create template kriteria data
        template_kriteria = self._generate_kriteria_template(
            tahun_pembanding["tahun_pembanding_1"],
            tahun_pembanding["tahun_pembanding_2"]
        )
        
        # Bulk create
        created_count = 0
        skipped_count = 0
        
        for perwadag in perwadag_list:
            # Check if already exists
            existing_query = select(PenilaianRisiko.id).where(
                and_(
                    PenilaianRisiko.user_perwadag_id == perwadag.id,
                    PenilaianRisiko.periode_id == periode_id,
                    PenilaianRisiko.deleted_at.is_(None)
                )
            )
            existing_result = await self.session.execute(existing_query)
            if existing_result.scalar_one_or_none():
                skipped_count += 1
                continue
            
            # Create new penilaian
            penilaian = PenilaianRisiko(
                user_perwadag_id=perwadag.id,
                periode_id=periode_id,
                tahun=periode.tahun,
                inspektorat=perwadag.inspektorat,
                kriteria_data=template_kriteria
            )
            
            self.session.add(penilaian)
            created_count += 1
        
        await self.session.commit()
        
        return {
            "created": created_count,
            "skipped": skipped_count,
            "total_perwadag": len(perwadag_list)
        }
    
    def _generate_kriteria_template(self, tahun_1: int, tahun_2: int) -> Dict[str, Any]:
        """Generate template kriteria data dengan tahun pembanding."""
        return {
            "tren_capaian": {
                "tahun_pembanding_1": tahun_1,
                "capaian_tahun_1": None,
                "tahun_pembanding_2": tahun_2,
                "capaian_tahun_2": None,
                "tren": None,
                "pilihan": None,
                "nilai": None
            },
            "realisasi_anggaran": {
                "tahun_pembanding": tahun_2,
                "realisasi": None,
                "pagu": None,
                "persentase": None,
                "pilihan": None,
                "nilai": None
            },
            "tren_ekspor": {
                "tahun_pembanding": tahun_2,
                "deskripsi": None,
                "pilihan": None,
                "nilai": None
            },
            "audit_itjen": {
                "tahun_pembanding": tahun_2,
                "deskripsi": None,
                "pilihan": None,
                "nilai": None
            },
            "perjanjian_perdagangan": {
                "tahun_pembanding": tahun_2,
                "deskripsi": None,
                "pilihan": None,
                "nilai": None
            },
            "peringkat_ekspor": {
                "tahun_pembanding": tahun_2,
                "deskripsi": None,
                "pilihan": None,
                "nilai": None
            },
            "persentase_ik": {
                "tahun_pembanding": tahun_2,
                "ik_tidak_tercapai": None,
                "total_ik": None,
                "persentase": None,
                "pilihan": None,
                "nilai": None
            },
            "realisasi_tei": {
                "tahun_pembanding": tahun_2,
                "nilai_realisasi": None,
                "nilai_potensi": None,
                "deskripsi": None,
                "pilihan": None,
                "nilai": None
            }
        }
    
    # ===== READ OPERATIONS =====
    
    async def get_by_id(self, penilaian_id: str) -> Optional[PenilaianRisiko]:
        """Get penilaian risiko by ID."""
        query = select(PenilaianRisiko).where(
            and_(PenilaianRisiko.id == penilaian_id, PenilaianRisiko.deleted_at.is_(None))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all_filtered(
        self, 
        filters: PenilaianRisikoFilterParams,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get all penilaian risiko dengan filtering dan enriched data - FIXED SORTING."""
        
        # Build base query dengan join untuk enriched data
        query = (
            select(
                PenilaianRisiko,
                User.nama.label('perwadag_nama'),
                PeriodeEvaluasi.is_locked.label('periode_locked')
            )
            .join(User, PenilaianRisiko.user_perwadag_id == User.id)
            .join(PeriodeEvaluasi, PenilaianRisiko.periode_id == PeriodeEvaluasi.id)
            .where(
                and_(
                    PenilaianRisiko.deleted_at.is_(None),
                    User.deleted_at.is_(None),
                    PeriodeEvaluasi.deleted_at.is_(None)
                )
            )
        )
        
        # Apply role-based filtering
        if user_role == "INSPEKTORAT" and user_inspektorat:
            query = query.where(PenilaianRisiko.inspektorat == user_inspektorat)
        # Admin bisa lihat semua data
        
        # Apply search filter
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    User.nama.ilike(search_term),
                    PenilaianRisiko.inspektorat.ilike(search_term)
                )
            )
        
        # Apply specific filters
        if filters.periode_id:
            query = query.where(PenilaianRisiko.periode_id == filters.periode_id)
        
        if filters.user_perwadag_id:
            query = query.where(PenilaianRisiko.user_perwadag_id == filters.user_perwadag_id)
        
        if filters.inspektorat:
            query = query.where(PenilaianRisiko.inspektorat.ilike(f"%{filters.inspektorat}%"))
        
        if filters.tahun:
            query = query.where(PenilaianRisiko.tahun == filters.tahun)
        
        if filters.is_complete is not None:
            if filters.is_complete:
                # Data complete jika ada profil risiko (sudah dihitung)
                query = query.where(PenilaianRisiko.profil_risiko_auditan.is_not(None))
            else:
                # Data incomplete jika belum ada profil risiko
                query = query.where(PenilaianRisiko.profil_risiko_auditan.is_(None))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        # ✅ FIXED: Proper SQLAlchemy sorting syntax
        if filters.sort_by == "skor_tertinggi":
            # Order by skor desc, nulls last
            query = query.order_by(
                PenilaianRisiko.skor_rata_rata.desc(),
                PenilaianRisiko.skor_rata_rata.is_(None).asc()
            )
        elif filters.sort_by == "skor_terendah":
            # Order by skor asc, nulls last  
            query = query.order_by(
                PenilaianRisiko.skor_rata_rata.is_(None).asc(),
                PenilaianRisiko.skor_rata_rata.asc()
            )
        elif filters.sort_by == "nama":
            query = query.order_by(User.nama.asc())
        else:  # default: created_at
            query = query.order_by(PenilaianRisiko.created_at.desc())
        
        # Apply pagination
        offset = (filters.page - 1) * filters.size
        query = query.offset(offset).limit(filters.size)
        
        # Execute query
        result = await self.session.execute(query)
        rows = result.all()
        
        # Build enriched data
        enriched_data = []
        for row in rows:
            penilaian = row[0]
            perwadag_nama = row[1]
            periode_locked = row[2]
            
            enriched_data.append({
                'penilaian': penilaian,
                'perwadag_nama': perwadag_nama,
                'periode_locked': periode_locked or False,
                'periode_editable': not (periode_locked or False)  # ✅ SIMPLIFIED
            })
        
        return enriched_data, total
    
    # ===== UPDATE OPERATIONS =====
    
    async def update(self, penilaian_id: str, penilaian_data: PenilaianRisikoUpdate) -> Optional[PenilaianRisiko]:
        """Update penilaian risiko."""
        penilaian = await self.get_by_id(penilaian_id)
        if not penilaian:
            return None
        
        # Update fields
        update_data = penilaian_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(penilaian, key, value)
        
        penilaian.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(penilaian)
        return penilaian
    
    async def update_calculation_result(
        self, 
        penilaian_id: str, 
        total_nilai_risiko: Decimal,
        skor_rata_rata: Decimal,
        profil_risiko: str
    ) -> Optional[PenilaianRisiko]:
        """Update hasil kalkulasi penilaian risiko."""
        penilaian = await self.get_by_id(penilaian_id)
        if not penilaian:
            return None
        
        penilaian.total_nilai_risiko = total_nilai_risiko
        penilaian.skor_rata_rata = skor_rata_rata
        penilaian.profil_risiko_auditan = profil_risiko
        penilaian.updated_at = datetime.utcnow()
        
        await self.session.commit()
        await self.session.refresh(penilaian)
        return penilaian
    
    # ===== VALIDATION OPERATIONS =====
    
    async def get_by_perwadag_and_periode(
        self, 
        user_perwadag_id: str, 
        periode_id: str
    ) -> Optional[PenilaianRisiko]:
        """Get penilaian risiko by perwadag dan periode."""
        query = select(PenilaianRisiko).where(
            and_(
                PenilaianRisiko.user_perwadag_id == user_perwadag_id,
                PenilaianRisiko.periode_id == periode_id,
                PenilaianRisiko.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def is_periode_editable(self, periode_id: str) -> bool:
        """Check apakah periode masih bisa diedit."""
        query = select(PeriodeEvaluasi).where(PeriodeEvaluasi.id == periode_id)
        result = await self.session.execute(query)
        periode = result.scalar_one_or_none()
        
        if not periode:
            return False
        
        return periode.is_editable()
    
    # ===== STATISTICS =====
    
    async def get_statistics(
        self,
        user_role: str,
        user_inspektorat: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get statistik penilaian risiko berdasarkan role."""
        
        # Base query berdasarkan role
        base_query = select(PenilaianRisiko).where(PenilaianRisiko.deleted_at.is_(None))
        
        if user_role == "INSPEKTORAT" and user_inspektorat:
            base_query = base_query.where(PenilaianRisiko.inspektorat == user_inspektorat)
        # Admin bisa lihat semua data
        
        # Total penilaian
        total_query = select(func.count()).select_from(base_query.subquery())
        total_result = await self.session.execute(total_query)
        total_penilaian = total_result.scalar() or 0
        
        # Penilaian completed (ada profil risiko)
        completed_query = select(func.count()).select_from(
            base_query.where(PenilaianRisiko.profil_risiko_auditan.is_not(None)).subquery()
        )
        completed_result = await self.session.execute(completed_query)
        penilaian_completed = completed_result.scalar() or 0
        
        # Completion rate
        completion_rate = 0.0
        if total_penilaian > 0:
            completion_rate = (penilaian_completed / total_penilaian) * 100
        
        # Breakdown by profil risiko
        profil_query = (
            select(PenilaianRisiko.profil_risiko_auditan, func.count())
            .select_from(base_query.subquery())
            .where(PenilaianRisiko.profil_risiko_auditan.is_not(None))
            .group_by(PenilaianRisiko.profil_risiko_auditan)
        )
        profil_result = await self.session.execute(profil_query)
        profil_breakdown = {row[0]: row[1] for row in profil_result.all()}
        
        # Breakdown by inspektorat (untuk admin)
        by_inspektorat = {}
        if user_role == "ADMIN":
            inspektorat_query = (
                select(PenilaianRisiko.inspektorat, func.count())
                .select_from(base_query.subquery())
                .group_by(PenilaianRisiko.inspektorat)
            )
            inspektorat_result = await self.session.execute(inspektorat_query)
            by_inspektorat = {row[0]: row[1] for row in inspektorat_result.all()}
        
        # Average scores
        avg_query = (
            select(
                func.avg(PenilaianRisiko.total_nilai_risiko),
                func.avg(PenilaianRisiko.skor_rata_rata)
            )
            .select_from(base_query.subquery())
            .where(PenilaianRisiko.profil_risiko_auditan.is_not(None))
        )
        avg_result = await self.session.execute(avg_query)
        avg_row = avg_result.fetchone()
        
        return {
            "total_penilaian": total_penilaian,
            "penilaian_completed": penilaian_completed,
            "completion_rate": round(completion_rate, 2),
            "profil_rendah": profil_breakdown.get("Rendah", 0),
            "profil_sedang": profil_breakdown.get("Sedang", 0),
            "profil_tinggi": profil_breakdown.get("Tinggi", 0),
            "by_inspektorat": by_inspektorat,
            "avg_total_nilai_risiko": float(avg_row[0]) if avg_row[0] else None,
            "avg_skor_rata_rata": float(avg_row[1]) if avg_row[1] else None
        }
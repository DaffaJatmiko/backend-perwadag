# ===== src/utils/penilaian_calculator.py =====
"""Calculator untuk business logic penilaian risiko - FIXED VERSION."""

from typing import Dict, Any, Optional, Tuple
from decimal import Decimal


class PenilaianRisikoCalculator:
    """Calculator untuk kalkulasi penilaian risiko dengan proper null handling."""
    
    def process_criteria_input(self, kriteria_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process dan kalkulasi otomatis untuk setiap kriteria dengan EXPLICIT RESET."""
        
        processed_data = kriteria_data.copy()
        
        # Process setiap kriteria dengan explicit reset
        if "tren_capaian" in processed_data:
            processed_data["tren_capaian"] = self._process_tren_capaian(
                processed_data["tren_capaian"]
            )
        
        if "realisasi_anggaran" in processed_data:
            processed_data["realisasi_anggaran"] = self._process_realisasi_anggaran(
                processed_data["realisasi_anggaran"]
            )
        
        if "tren_ekspor" in processed_data:
            processed_data["tren_ekspor"] = self._process_tren_ekspor(
                processed_data["tren_ekspor"]
            )
        
        if "audit_itjen" in processed_data:
            processed_data["audit_itjen"] = self._process_audit_itjen(
                processed_data["audit_itjen"]
            )
        
        if "perjanjian_perdagangan" in processed_data:
            processed_data["perjanjian_perdagangan"] = self._process_perjanjian_perdagangan(
                processed_data["perjanjian_perdagangan"]
            )
        
        if "peringkat_ekspor" in processed_data:
            processed_data["peringkat_ekspor"] = self._process_peringkat_ekspor(
                processed_data["peringkat_ekspor"]
            )
        
        if "persentase_ik" in processed_data:
            processed_data["persentase_ik"] = self._process_persentase_ik(
                processed_data["persentase_ik"]
            )
        
        if "realisasi_tei" in processed_data:
            processed_data["realisasi_tei"] = self._process_realisasi_tei(
                processed_data["realisasi_tei"]
            )
        
        return processed_data
    
    def calculate_total_score(self, kriteria_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Kalkulasi total nilai risiko dan profil risiko.
        
        Returns:
            Dict jika semua kriteria lengkap, None jika ada yang kosong
        """
        
        # Extract nilai dari setiap kriteria
        criteria_names = [
            "tren_capaian", "realisasi_anggaran", "tren_ekspor", "audit_itjen",
            "perjanjian_perdagangan", "peringkat_ekspor", "persentase_ik", "realisasi_tei"
        ]
        
        nilai_scores = []
        missing_criteria = []
        
        for criteria_name in criteria_names:
            if criteria_name in kriteria_data:
                nilai = kriteria_data[criteria_name].get("nilai")
                if nilai is not None:
                    nilai_scores.append(nilai)
                else:
                    missing_criteria.append(criteria_name)
            else:
                missing_criteria.append(criteria_name)
        
        # ✅ PERBAIKAN: Return None jika ada kriteria yang kosong
        if len(nilai_scores) != 8:
            return None  # Tidak bisa kalkulasi, return None bukan raise error
        
        # Kalkulasi berdasarkan business rules
        weights = [15, 10, 15, 25, 5, 10, 10, 10]  # Bobot untuk masing-masing kriteria
        
        # Total nilai risiko dengan bobot
        total_nilai_risiko = sum(
            nilai * weight for nilai, weight in zip(nilai_scores, weights)
        ) / 5
        
        # Skor rata-rata
        skor_rata_rata = sum(nilai_scores) / len(nilai_scores)
        
        # Profil risiko berdasarkan skor rata-rata
        if skor_rata_rata <= 2.0:
            profil_risiko_auditan = "Rendah"
        elif skor_rata_rata <= 3.5:
            profil_risiko_auditan = "Sedang"
        else:
            profil_risiko_auditan = "Tinggi"
        
        return {
            "total_nilai_risiko": Decimal(str(round(total_nilai_risiko, 2))),
            "skor_rata_rata": Decimal(str(round(skor_rata_rata, 2))),
            "profil_risiko_auditan": profil_risiko_auditan,
            "individual_scores": nilai_scores,
            "weights": weights,
            "weighted_scores": [nilai * weight for nilai, weight in zip(nilai_scores, weights)]
        }
    
    def is_calculation_complete(self, kriteria_data: Dict[str, Any]) -> Tuple[bool, list]:
        """
        Check apakah semua kriteria lengkap untuk kalkulasi.
        
        Returns:
            Tuple(is_complete: bool, missing_criteria: list)
        """
        criteria_names = [
            "tren_capaian", "realisasi_anggaran", "tren_ekspor", "audit_itjen",
            "perjanjian_perdagangan", "peringkat_ekspor", "persentase_ik", "realisasi_tei"
        ]
        
        missing_criteria = []
        
        for criteria_name in criteria_names:
            if criteria_name not in kriteria_data:
                missing_criteria.append(criteria_name)
                continue
                
            criteria_data_item = kriteria_data[criteria_name]
            nilai = criteria_data_item.get("nilai")
            
            if nilai is None:
                missing_criteria.append(criteria_name)
        
        is_complete = len(missing_criteria) == 0
        return is_complete, missing_criteria
    
    # ===== INDIVIDUAL CRITERIA PROCESSORS WITH EXPLICIT RESET =====
    
    def _process_tren_capaian(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process kriteria tren capaian dengan EXPLICIT RESET."""
        
        # ✅ ALWAYS RESET calculated fields FIRST
        data["tren"] = None
        data["pilihan"] = None
        data["nilai"] = None
        
        # Then calculate IF conditions are met
        if (data.get("capaian_tahun_1") is not None and 
            data.get("capaian_tahun_2") is not None):
            
            capaian_1 = float(data["capaian_tahun_1"])
            capaian_2 = float(data["capaian_tahun_2"])
            
            if capaian_1 != 0:
                tren = ((capaian_2 - capaian_1) / capaian_1) * 100
                data["tren"] = round(tren, 2)
                
                # Determine pilihan dan nilai
                if tren >= 41:
                    data["pilihan"] = "Naik ≥ 41%"
                    data["nilai"] = 1
                elif tren >= 21:
                    data["pilihan"] = "Naik 21% - 40%"
                    data["nilai"] = 2
                elif tren >= 0:
                    data["pilihan"] = "Naik 0% - 20%"
                    data["nilai"] = 3
                elif tren >= -25:
                    data["pilihan"] = "Turun < 25%"
                    data["nilai"] = 4
                else:
                    data["pilihan"] = "Turun ≥ 25%"
                    data["nilai"] = 5
        
        return data
    
    def _process_realisasi_anggaran(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process kriteria realisasi anggaran dengan EXPLICIT RESET."""
        
        # ✅ ALWAYS RESET calculated fields FIRST
        data["persentase"] = None
        data["pilihan"] = None
        data["nilai"] = None
        
        if (data.get("realisasi") is not None and 
            data.get("pagu") is not None):
            
            realisasi = float(data["realisasi"])
            pagu = float(data["pagu"])
            
            if pagu != 0:
                persentase = (realisasi / pagu) * 100
                data["persentase"] = round(persentase, 2)
                
                # Determine pilihan dan nilai
                if persentase > 98:
                    data["pilihan"] = "> 98%"
                    data["nilai"] = 1
                elif persentase > 95:
                    data["pilihan"] = "95% - 97%"
                    data["nilai"] = 2
                elif persentase > 90:
                    data["pilihan"] = "90% - 94%"
                    data["nilai"] = 3
                elif persentase >= 85:
                    data["pilihan"] = "85% - 89%"
                    data["nilai"] = 4
                else:
                    data["pilihan"] = "< 85%"
                    data["nilai"] = 5
        
        return data
    
    def _process_tren_ekspor(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process kriteria tren ekspor dengan EXPLICIT RESET."""
        
        # ✅ ALWAYS RESET calculated fields FIRST
        data["pilihan"] = None
        data["nilai"] = None
        
        if data.get("deskripsi") is not None:
            deskripsi = float(data["deskripsi"])
            
            # Determine pilihan dan nilai
            if deskripsi >= 35:
                data["pilihan"] = "Naik ≥ 35%"
                data["nilai"] = 1
            elif deskripsi >= 20:
                data["pilihan"] = "Naik 20% - 34%"
                data["nilai"] = 2
            elif deskripsi >= 0:
                data["pilihan"] = "Naik 0% - 19%"
                data["nilai"] = 3
            elif deskripsi >= -25:
                data["pilihan"] = "Turun < 25%"
                data["nilai"] = 4
            else:
                data["pilihan"] = "Turun ≥ 25%"
                data["nilai"] = 5
        
        return data
    
    def _process_audit_itjen(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process kriteria audit itjen dengan EXPLICIT RESET."""
        
        # ✅ ALWAYS RESET calculated fields FIRST
        data["nilai"] = None
        
        if data.get("pilihan") is not None:
            pilihan = data["pilihan"]
            
            # Map pilihan ke nilai
            pilihan_map = {
                "1 Tahun": 1,
                "2 Tahun": 2,
                "3 Tahun": 3,
                "4 Tahun": 4,
                "Belum pernah diaudit": 5
            }
            
            data["nilai"] = pilihan_map.get(pilihan)
        
        return data
    
    def _process_perjanjian_perdagangan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process kriteria perjanjian perdagangan dengan EXPLICIT RESET."""
        
        # ✅ ALWAYS RESET calculated fields FIRST
        data["nilai"] = None
        
        if data.get("pilihan") is not None:
            pilihan = data["pilihan"]
            
            # Map pilihan ke nilai
            pilihan_map = {
                "Tidak ada perjanjian internasional": 1,
                "Sedang diusulkan/ Being Proposed": 2,
                "Masih berproses/ on going": 3,
                "Sudah disepakati namun belum diratifikasi": 4,
                "Sudah diimplementasikan": 5
            }
            
            data["nilai"] = pilihan_map.get(pilihan)
        
        return data
    
    def _process_peringkat_ekspor(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process kriteria peringkat ekspor dengan EXPLICIT RESET."""
        
        # ✅ ALWAYS RESET calculated fields FIRST
        data["pilihan"] = None
        data["nilai"] = None
        
        if data.get("deskripsi") is not None:
            deskripsi = int(data["deskripsi"])
            
            # Determine pilihan dan nilai
            if 1 <= deskripsi <= 5:
                data["pilihan"] = "Peringkat 1 - 6"
                data["nilai"] = 1
            elif 7 <= deskripsi <= 11:
                data["pilihan"] = "Peringkat 7 - 12"
                data["nilai"] = 2
            elif 13 <= deskripsi <= 18:
                data["pilihan"] = "Peringkat 13 - 18"
                data["nilai"] = 3
            elif 19 <= deskripsi <= 23:
                data["pilihan"] = "Peringkat 19 - 23"
                data["nilai"] = 4
            else:
                data["pilihan"] = "Peringkat diatas 23"
                data["nilai"] = 5
        
        return data
    
    def _process_persentase_ik(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process kriteria persentase IK dengan EXPLICIT RESET."""
        
        # ✅ ALWAYS RESET calculated fields FIRST
        data["persentase"] = None
        data["pilihan"] = None
        data["nilai"] = None
        
        if (data.get("ik_tidak_tercapai") is not None and 
            data.get("total_ik") is not None):
            
            ik_tidak_tercapai = int(data["ik_tidak_tercapai"])
            total_ik = int(data["total_ik"])
            
            if total_ik != 0:
                persentase = (ik_tidak_tercapai / total_ik) * 100
                data["persentase"] = round(persentase, 2)
                
                # Determine pilihan dan nilai
                if persentase <= 5:
                    data["pilihan"] = "< 5%"
                    data["nilai"] = 1
                elif persentase <= 10:
                    data["pilihan"] = "6% - 10%"
                    data["nilai"] = 2
                elif persentase <= 15:
                    data["pilihan"] = "11% - 15%"
                    data["nilai"] = 3
                elif persentase <= 20:
                    data["pilihan"] = "16% - 20%"
                    data["nilai"] = 4
                else:
                    data["pilihan"] = "> 20%"
                    data["nilai"] = 5
        
        return data
    
    def _process_realisasi_tei(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process kriteria realisasi TEI dengan EXPLICIT RESET."""
        
        # ✅ ALWAYS RESET calculated fields FIRST
        data["deskripsi"] = None
        data["pilihan"] = None
        data["nilai"] = None
        
        if (data.get("nilai_realisasi") is not None and 
            data.get("nilai_potensi") is not None):
            
            nilai_realisasi = float(data["nilai_realisasi"])
            nilai_potensi = float(data["nilai_potensi"])
            
            # Special case: both zero
            if nilai_potensi == 0 or nilai_realisasi == 0:
                data["deskripsi"] = 0
                data["pilihan"] = "Belum Ada Realisasi"
                data["nilai"] = 5
            elif nilai_potensi != 0:
                deskripsi = (nilai_realisasi / nilai_potensi) * 100
                data["deskripsi"] = round(deskripsi, 2)
                
                # Determine pilihan dan nilai
                if deskripsi > 70:
                    data["pilihan"] = "> 70%"
                    data["nilai"] = 1
                elif deskripsi >= 50:
                    data["pilihan"] = "50% - 70%"
                    data["nilai"] = 2
                elif deskripsi >= 25:
                    data["pilihan"] = "25% - 49%"
                    data["nilai"] = 3
                else:
                    data["pilihan"] = "< 25%"
                    data["nilai"] = 4
        
        return data
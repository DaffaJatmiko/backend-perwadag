# ===== UPDATED: src/services/pdf_generator.py =====

import io
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from zoneinfo import ZoneInfo  # Python 3.9+ built-in
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

class MatriksPDFGenerator:
    """Service untuk generate PDF matriks evaluasi dengan layout landscape."""
    
    def __init__(self):
        # LANDSCAPE orientation
        self.page_width, self.page_height = landscape(A4)
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _format_date_indonesia(self, date_obj) -> str:
        """Format tanggal ke format Indonesia: 15 Agustus 2025"""
        if not date_obj:
            return "-"
            
        try:
            # Konversi string ke date object jika perlu
            if isinstance(date_obj, str):
                date_obj = datetime.fromisoformat(date_obj.replace('Z', '+00:00')).date()
            
            # Array nama bulan Indonesia
            months = [
                '', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
            ]
            
            month_name = months[date_obj.month]
            return f"{date_obj.day} {month_name} {date_obj.year}"
            
        except Exception:
            return str(date_obj) if date_obj else "-"
    
    def _setup_custom_styles(self):
        """Setup custom styles untuk PDF landscape."""
        
        # Header kop surat style
        self.styles.add(ParagraphStyle(
            name='KopSurat',
            parent=self.styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT,
            spaceAfter=3
        ))
        
        # Title matriks style  
        self.styles.add(ParagraphStyle(
            name='TitleMatriks',
            parent=self.styles['Title'],
            fontSize=14,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=12,
            spaceBefore=12
        ))
        
        # Info detail style
        self.styles.add(ParagraphStyle(
            name='InfoDetail',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica',
            alignment=TA_LEFT,
            leading=14
        ))
        
        # Signature style
        self.styles.add(ParagraphStyle(
            name='Signature',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica',
            alignment=TA_LEFT
        ))

    def generate_matriks_pdf(
        self, 
        matriks_data: Dict[str, Any],
        surat_tugas_data: Dict[str, Any],
        exit_meeting_data: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate PDF matriks evaluasi dengan layout landscape."""
        
        # Create PDF buffer dengan landscape orientation
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=1.5*cm,
            leftMargin=2.5*cm,
            topMargin=1.5*cm,
            bottomMargin=2*cm
        )
        
        # Build PDF content
        story = []
        
        # Header dan Title dalam satu flow
        story.extend(self._build_header_and_title())
        
        # Info Section
        story.extend(self._build_info_section(surat_tugas_data, exit_meeting_data))
        
        # Main Table
        story.extend(self._build_main_table(matriks_data))
        
        # Signature Section
        story.extend(self._build_signature_section(surat_tugas_data, exit_meeting_data))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _build_header_and_title(self) -> List[Any]:
        """Build header kop surat dan title di tengah."""
        elements = []
        
        # Header kop surat saja (tanpa formulir V)
        header_data = [
            [
                # Kolom kiri: Kop surat
                Paragraph("KEMENTERIAN PERDAGANGAN<br/>INSPEKTORAT JENDERAL", self.styles['KopSurat']),
                # Kolom kanan: kosong (formulir V dihilangkan)
                ""
            ]
        ]
        
        # OPTIMIZED: Perbesar column widths untuk mengisi ruang
        header_table = Table(header_data, colWidths=[12*cm, 13*cm])  # Total 28cm
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 1*cm))
        
        # Title utama di tengah
        elements.append(Paragraph("MATRIKS HASIL EVALUASI", self.styles['TitleMatriks']))
        elements.append(Spacer(1, 0.8*cm))
        
        return elements
    
    def _build_info_section(
        self, 
        surat_tugas_data: Dict[str, Any],
        exit_meeting_data: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Build info section tanpa dotted lines, data kosong jadi dash."""
        elements = []
        
        # Extract data
        perwadag_name = surat_tugas_data.get('nama_perwadag', '') or '-'
        periode_mulai = surat_tugas_data.get('tanggal_evaluasi_mulai', '')
        periode_selesai = surat_tugas_data.get('tanggal_evaluasi_selesai', '')
        no_surat = surat_tugas_data.get('no_surat', '') or '-'
        
        # Format periode dengan format Indonesia
        periode_text = "-"
        if periode_mulai and periode_selesai:
            try:
                tanggal_mulai_formatted = self._format_date_indonesia(periode_mulai)
                tanggal_selesai_formatted = self._format_date_indonesia(periode_selesai)
                periode_text = f"{tanggal_mulai_formatted} - {tanggal_selesai_formatted}"
            except:
                periode_text = f"{periode_mulai} - {periode_selesai}" if periode_mulai and periode_selesai else "-"

        # Exit briefing date dengan format Indonesia
        exit_date = "-"
        if exit_meeting_data and exit_meeting_data.get('tanggal_meeting'):
            try:
                exit_date = self._format_date_indonesia(exit_meeting_data['tanggal_meeting'])
            except:
                exit_date = str(exit_meeting_data.get('tanggal_meeting', '')) or "-"
        
        # Create info table dengan format yang bersih
        info_data = [
            ['Perwadag', ':', perwadag_name],
            ['Periode Yang Dievaluasi', ':', periode_text],
            ['Nomor Surat Tugas', ':', no_surat],
            ['Exit Briefing Tanggal', ':', exit_date]
        ]
        
        # OPTIMIZED: Perbesar column widths untuk mengisi ruang
        info_table = Table(info_data, colWidths=[5*cm, 0.5*cm, 19.5*cm])  # Total 28cm
        info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 1*cm))
        
        return elements
    
    def _build_main_table(self, matriks_data: Dict[str, Any]) -> List[Any]:
        """Build main table tanpa background color dan subheader."""
        elements = []
        
        # Get temuan data
        temuan_items = []
        if matriks_data.get('temuan_rekomendasi_summary'):
            temuan_items = matriks_data['temuan_rekomendasi_summary'].get('data', [])
        
        # Table headers saja (hapus subheader 1,2,3,4)
        table_data = [['No', 'Kondisi', 'Kriteria', 'Rekomendasi']]
        
        # Add data rows atau empty rows
        if temuan_items:
            for i, item in enumerate(temuan_items, 1):
                kondisi = item.get('kondisi', '') or '-'
                kriteria = item.get('kriteria', '') or '-'
                rekomendasi = item.get('rekomendasi', '') or '-'
                
                # Wrap text dalam Paragraph untuk auto-wrapping
                kondisi_para = Paragraph(kondisi, ParagraphStyle(name='CellText', fontSize=8, leading=10))
                kriteria_para = Paragraph(kriteria, ParagraphStyle(name='CellText', fontSize=8, leading=10))
                rekomendasi_para = Paragraph(rekomendasi, ParagraphStyle(name='CellText', fontSize=8, leading=10))
                
                table_data.append([str(i), kondisi_para, kriteria_para, rekomendasi_para])
        else:
            # Empty row dengan tinggi yang cukup untuk isian manual (3 empty rows)
            for i in range(1, 4):
                empty_cell = Paragraph("&nbsp;<br/>&nbsp;<br/>&nbsp;", ParagraphStyle(name='EmptyCell', fontSize=8))
                table_data.append([str(i), empty_cell, empty_cell, empty_cell])
        
        # OPTIMIZED: Perbesar column widths untuk mengisi ruang - Total ~28cm
        col_widths = [1.5*cm, 7.5*cm, 7.5*cm, 8.5*cm]
        
        # Create table
        main_table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Table styling tanpa background color
        main_table.setStyle(TableStyle([
            # Header row styling (row 0) - TANPA background color
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            
            # Data rows styling (from row 1)
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # No column center
            ('ALIGN', (1, 1), (-1, -1), 'LEFT'),   # Text columns left
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            
            # Borders saja
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        ]))
        
        elements.append(main_table)
        elements.append(Spacer(1, 1.5*cm))
        
        return elements
    
    def _build_signature_section(
        self, 
        surat_tugas_data: Dict[str, Any],
        exit_meeting_data: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """Build signature section dengan struktur tabel yang benar dan sejajar."""
        elements = []
        
        # Get assignment info
        assignment_info = surat_tugas_data.get('assignment_info', {})
        
        # Extract names dan jabatan dengan fallback ke placeholder
        inspektur_name = "................................"
        inspektur_jabatan = "Inspektur"  # default fallback
        pengedali_mutu_name = "................................"
        pengedali_teknis_name = "................................"
        ketua_tim_name = "................................"

        if assignment_info.get('pimpinan_inspektorat'):
            pimpinan_data = assignment_info['pimpinan_inspektorat']
            name = pimpinan_data.get('nama', '')
            if name and name != '-':
                inspektur_name = name
            
            # Ambil jabatan dari user pimpinan inspektorat
            jabatan = pimpinan_data.get('jabatan', '')
            if jabatan and jabatan != '-':
                inspektur_jabatan = jabatan
        
        if assignment_info.get('pengedali_mutu'):
            name = assignment_info['pengedali_mutu'].get('nama', '')
            if name and name != '-':
                pengedali_mutu_name = name
            
        if assignment_info.get('pengendali_teknis'):
            name = assignment_info['pengendali_teknis'].get('nama', '')
            if name and name != '-':
                pengedali_teknis_name = name
            
        if assignment_info.get('ketua_tim'):
            name = assignment_info['ketua_tim'].get('nama', '')
            if name and name != '-':
                ketua_tim_name = name
        
        # Tanggal Jakarta hari ini dengan format yang konsisten
        try:
            jakarta_tz = ZoneInfo('Asia/Jakarta')
            today = datetime.now(jakarta_tz).date()
        except:
            today = datetime.now().date()

        # Gunakan helper function untuk konsistensi
        formatted_today = self._format_date_indonesia(today)
        location_date = f"Jakarta, {formatted_today}"
        
        # ===== TABEL UTAMA DENGAN ROW STRUCTURE YANG BENAR =====
        
        # OPTIMIZED: Perbesar column widths untuk tim evaluasi
        nama_tim_paragraphs = [
            Paragraph(f"({pengedali_mutu_name})", ParagraphStyle(
                name='NamaTim', fontSize=10, fontName='Helvetica', alignment=TA_CENTER, leading=12)),
            Paragraph(f"({pengedali_teknis_name})", ParagraphStyle(
                name='NamaTim', fontSize=10, fontName='Helvetica', alignment=TA_CENTER, leading=12)),
            Paragraph(f"({ketua_tim_name})", ParagraphStyle(
                name='NamaTim', fontSize=10, fontName='Helvetica', alignment=TA_CENTER, leading=12))
        ]
        
        nama_tim_table = Table([nama_tim_paragraphs], colWidths=[7*cm, 7*cm, 7*cm])  # Total 21cm
        nama_tim_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        jabatan_tim_table = Table([["Pengendali Mutu", "Pengendali Teknis", "Ketua Tim"]], 
                                colWidths=[7*cm, 7*cm, 7*cm])  # Total 21cm
        jabatan_tim_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        # ===== MAIN SIGNATURE TABLE DENGAN STRUKTUR ROW YANG SEJAJAR =====
        
        # Buat Paragraph untuk nama inspektur agar bisa wrap
        nama_inspektur_para = Paragraph(f"({inspektur_name})", ParagraphStyle(
            name='NamaInspektur',
            fontSize=10,
            fontName='Helvetica',
            alignment=TA_CENTER,
            leading=12
        ))
        
        signature_data = [
            # Row 1: Header
            ["Menyetujui,", location_date],
            
            # Row 2: Title - jabatan dinamis
            [f"{inspektur_jabatan},", "Tim Evaluasi,"],
            
            # Row 3: Jabatan (kiri kosong, kanan ada jabatan)
            ["", jabatan_tim_table],
            
            # Row 4-6: Ruang tanda tangan (keduanya kosong dengan tinggi sama)
            ["", ""],
            ["", ""],
            ["", ""],
            
            # Row 7: Nama (SEJAJAR PERFECT dengan wrapping!)
            [nama_inspektur_para, nama_tim_table]
        ]
        
        # OPTIMIZED: Perbesar column widths untuk mengisi ruang
        signature_table = Table(signature_data, colWidths=[6*cm, 19*cm])  # Total 28cm
        
        # PERBAIKAN: Tambahkan KeepTogether untuk memastikan signature tidak terpotong
        from reportlab.platypus import KeepTogether
        
        # Table styling dengan row heights yang konsisten
        signature_table.setStyle(TableStyle([
            # Font dan alignment dasar
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            
            # Row 1: Header alignment
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),   # "Menyetujui" center
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),   # Tanggal center
            
            # Row 2: Title alignment  
            ('ALIGN', (0, 1), (0, 1), 'CENTER'),   # "Inspektur" center
            ('ALIGN', (1, 1), (1, 1), 'CENTER'),   # "Tim Evaluasi" center
            
            # Row 3: Jabatan (kiri kosong, kanan center)
            ('ALIGN', (0, 2), (0, 2), 'CENTER'),   # Kosong
            ('ALIGN', (1, 2), (1, 2), 'CENTER'),   # Jabatan tim center
            
            # Row 4-6: Ruang kosong
            ('ALIGN', (0, 3), (-1, 5), 'CENTER'),
            
            # Row 7: Nama (SEJAJAR!)
            ('ALIGN', (0, 6), (0, 6), 'CENTER'),   # Nama inspektur center
            ('ALIGN', (1, 6), (1, 6), 'CENTER'),   # Nama tim center
            
            # Padding untuk spacing yang konsisten
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            
            # Row spacing khusus
            ('TOPPADDING', (0, 1), (-1, 1), 8),    # Space setelah header
            ('TOPPADDING', (0, 2), (-1, 2), 8),    # Space setelah title
            ('TOPPADDING', (0, 3), (-1, 5), 10),   # Ruang tanda tangan
            ('TOPPADDING', (0, 6), (-1, 6), 0),    # Nama (no extra padding)
        ]))
        
        # Wrap signature table dengan KeepTogether agar tidak terpotong halaman
        signature_with_keeper = KeepTogether([signature_table])
        elements.append(signature_with_keeper)
        
        return elements
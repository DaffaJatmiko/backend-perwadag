"""Add complete inspektorat users data

Revision ID: 002_add_complete_inspektorat_users
Revises: 001_initial_setup
Create Date: 2025-01-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from datetime import datetime, date
import uuid

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001_initial_setup'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add complete inspektorat users data."""
    connection = op.get_bind()
    
    # Hash password @Kemendag123 (sama untuk semua user)
    default_password_hash = "$2b$12$6SO28mFb6kEi3QN8h14b5uOFTC6V218f/Tf6DKRMnni6oNiQWYmn2"
    
    def generate_username_inspektorat(nama: str, inspektorat: str) -> str:
        """
        Generate username untuk inspektorat: nama_depan + _ir + nomor_inspektorat
        Mengikuti logik dari username_generator.py
        """
        # Ambil nama depan (kata pertama)
        nama_parts = nama.lower().split()
        nama_depan = nama_parts[0] if nama_parts else "user"
        
        # Extract nomor inspektorat
        inspektorat_map = {
            'Inspektorat 1': '1',
            'Inspektorat 2': '2', 
            'Inspektorat 3': '3',
            'Inspektorat 4': '4'
        }
        nomor = inspektorat_map.get(inspektorat, '1')
        
        # Format: nama_depan_ir{nomor}
        return f"{nama_depan}_ir{nomor}"
    
    def generate_username_with_conflict_resolution(nama: str, inspektorat: str) -> str:
        """
        Generate username dengan conflict resolution: nama_depan_nama_kedua_ir{nomor}
        Mengikuti logik dari username_generator.py
        """
        nama_parts = nama.lower().split()
        if len(nama_parts) < 2:
            # Jika hanya 1 kata, tambah suffix angka
            base = generate_username_inspektorat(nama, inspektorat)
            return f"{base}2"
        
        nama_depan = nama_parts[0]
        nama_kedua = nama_parts[1]
        
        # Extract nomor inspektorat
        inspektorat_map = {
            'Inspektorat 1': '1',
            'Inspektorat 2': '2', 
            'Inspektorat 3': '3',
            'Inspektorat 4': '4'
        }
        nomor = inspektorat_map.get(inspektorat, '1')
        
        # Format: nama_depan_nama_kedua_ir{nomor}
        return f"{nama_depan}_{nama_kedua}_ir{nomor}"

    def check_username_exists(username: str) -> bool:
        """Check if username already exists in database."""
        result = connection.execute(
            sa.text("SELECT 1 FROM users WHERE username = :username LIMIT 1"),
            {'username': username}
        )
        return result.fetchone() is not None

    def get_unique_username(nama: str, inspektorat: str) -> str:
        """
        Get unique username dengan conflict resolution sesuai contoh:
        - abdul gofur ir 2 = abdul_ir2
        - abdul gani ir 2 = abdul_gani_ir2 (karena 'abdul' sudah ada)
        - abdul falah ir 3 = abdul_ir3 (karena abdul_ir2 sudah ada di inspektorat 2)
        """
        # Coba base username dulu
        base_username = generate_username_inspektorat(nama, inspektorat)
        
        if not check_username_exists(base_username):
            return base_username
        
        # Jika conflict, coba dengan nama kedua
        conflict_username = generate_username_with_conflict_resolution(nama, inspektorat)
        
        if not check_username_exists(conflict_username):
            return conflict_username
        
        # Jika masih conflict, tambah suffix angka
        for i in range(2, 100):
            numbered_username = f"{base_username}{i}"
            if not check_username_exists(numbered_username):
                return numbered_username
        
        # Fallback dengan timestamp
        import time
        return f"{base_username}_{int(time.time() % 1000)}"

    # ===== DATA INSPEKTORAT LENGKAP (TANPA PANGKAT) =====
    
    # INSPEKTORAT 1 - Additional users (yang belum ada di migration pertama)
    inspektorat_1_additional = [
        {'nama': 'Fenny Rosa', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Daniel Maruli', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Andi Ika Ovenia', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Bunga Uli', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Leo Spornayan', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Ruwarto', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Raden Dicky Ramadhan', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Ahmad Kiflan Deemas Anshari', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Adittrasna Iyan Kuswindana', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Hana Nadhifa Khalda', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Dara Nabila Usmaryoto', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Okto Pendar W', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Elsa Zuhara Damayanti', 'jabatan': 'Auditor Ahli Pertama'},
    ]
    
    # INSPEKTORAT 2 - Additional users
    inspektorat_2_additional = [
        {'nama': 'Puri Dinasti', 'jabatan': 'Auditor Ahli Madya'},
        {'nama': 'Angga Widodo Saputro', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Gusti Ayu Komang Ardiyani', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Diah Ekowati N', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Rizky Beta Puspitasari', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Widya Soehandoko', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Lina Rahmawati', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Tonny Anderson', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Nabila Auliyya Rodja', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Ifham Ilmy Hakim', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Kurnia Sari Dewi', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Muhammad Adhitya Kusuma Istadi', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Rosalia Krenata Mufarokhah', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Khalda Nabilah', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Ikhlasul Ardi Dewantara', 'jabatan': 'Auditor Ahli Pertama'},
    ]
    
    # INSPEKTORAT 3 - Additional users
    inspektorat_3_additional = [
        {'nama': 'Tri Djuliyanto', 'jabatan': 'Auditor Ahli Madya'},
        {'nama': 'Didiet Maharani Bahariyanti Purnama Dewi', 'jabatan': 'Auditor Ahli Madya'},
        {'nama': 'Givana Arizani', 'jabatan': 'Auditor Ahli Madya'},
        {'nama': 'Yani Mulia Banjarsari', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Wardini Wulansari', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Elviana Novita', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Berta', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Ezar Nurrizal Kamil', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Ana Najiyya', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Surya', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Namira Tita Amelia', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Muhammad Adrian', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Muhammad Farhan', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Clarissa Putri Kharisma', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Raihanah Aulya Kusumaputri', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Adinda Vinka Maharani', 'jabatan': 'Auditor Ahli Pertama'},
    ]
    
    # INSPEKTORAT 4 - Additional users
    inspektorat_4_additional = [
        {'nama': 'Lili Yuliadi', 'jabatan': 'Auditor Ahli Madya'},
        {'nama': 'Raden Roro Dyah Lestari Adityas Ningrum', 'jabatan': 'Auditor Ahli Madya'},
        {'nama': 'Windy Solihin', 'jabatan': 'Auditor Ahli Madya'},
        {'nama': 'Asnita Riani Sembiring', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Fathoni Ahmad', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Redho Alfasumma Putra', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Yoyoh Haeriah', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Rio Basana Margaretha Pane', 'jabatan': 'Auditor Ahli Muda'},
        {'nama': 'Raden Muhammad Ali Fathoni', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Aristia Rizki Putra', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Umi Chulsum', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Shinta Dewi Noviany', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Rahma Kusuma Wardani', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Muhammad Farhan', 'jabatan': 'Auditor Terampil'},
        {'nama': 'Siti Nurmala Sari', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Farizal Julio Hakim', 'jabatan': 'Auditor Ahli Pertama'},
    ]
    
    # Insert all additional users
    all_additional_users = [
        (inspektorat_1_additional, 'Inspektorat 1'),
        (inspektorat_2_additional, 'Inspektorat 2'),
        (inspektorat_3_additional, 'Inspektorat 3'),
        (inspektorat_4_additional, 'Inspektorat 4'),
    ]
    
    for users_list, inspektorat in all_additional_users:
        print(f"\n=== Processing {inspektorat} ===")
        for user in users_list:
            user_id = str(uuid.uuid4())
            username = get_unique_username(user['nama'], inspektorat)
            
            print(f"Creating: {user['nama']} -> {username}")
            
            connection.execute(
                sa.text("""
                    INSERT INTO users (
                        id, nama, username, jabatan, hashed_password, email, 
                        is_active, role, inspektorat, created_at
                    ) VALUES (
                        :id, :nama, :username, :jabatan, :hashed_password, :email,
                        :is_active, :role, :inspektorat, :created_at
                    )
                """),
                {
                    'id': user_id,
                    'nama': user['nama'],
                    'username': username,
                    'jabatan': user['jabatan'],
                    'hashed_password': default_password_hash,
                    'email': None,
                    'is_active': True,
                    'role': 'INSPEKTORAT',
                    'inspektorat': inspektorat,
                    'created_at': datetime.utcnow()
                }
            )
    
    print("\n✅ All additional inspektorat users have been added successfully!")


def downgrade() -> None:
    """Remove additional inspektorat users added in this migration."""
    connection = op.get_bind()
    
    # List nama-nama yang ditambahkan di migration ini
    users_to_remove = [
        # Inspektorat 1
        'Fenny Rosa', 'Daniel Maruli', 'Andi Ika Ovenia', 'Bunga Uli', 'Leo Spornayan', 
        'Ruwarto', 'Raden Dicky Ramadhan', 'Ahmad Kiflan Deemas Anshari', 
        'Adittrasna Iyan Kuswindana', 'Hana Nadhifa Khalda', 'Dara Nabila Usmaryoto', 
        'Okto Pendar W', 'Elsa Zuhara Damayanti',
        
        # Inspektorat 2  
        'Puri Dinasti', 'Angga Widodo Saputro', 'Gusti Ayu Komang Ardiyani', 
        'Diah Ekowati N', 'Rizky Beta Puspitasari', 'Widya Soehandoko',
        'Lina Rahmawati', 'Tonny Anderson', 'Nabila Auliyya Rodja', 'Ifham Ilmy Hakim', 
        'Kurnia Sari Dewi', 'Muhammad Adhitya Kusuma Istadi', 'Rosalia Krenata Mufarokhah', 
        'Khalda Nabilah', 'Ikhlasul Ardi Dewantara',
        
        # Inspektorat 3
        'Tri Djuliyanto', 'Didiet Maharani Bahariyanti Purnama Dewi', 'Givana Arizani', 
        'Yani Mulia Banjarsari', 'Wardini Wulansari', 'Elviana Novita', 'Berta', 
        'Ezar Nurrizal Kamil', 'Ana Najiyya', 'Surya', 'Namira Tita Amelia', 
        'Muhammad Adrian', 'Muhammad Farhan', 'Clarissa Putri Kharisma', 
        'Raihanah Aulya Kusumaputri', 'Adinda Vinka Maharani',
        
        # Inspektorat 4
        'Lili Yuliadi', 'Raden Roro Dyah Lestari Adityas Ningrum', 'Windy Solihin', 
        'Asnita Riani Sembiring', 'Fathoni Ahmad', 'Redho Alfasumma Putra', 
        'Yoyoh Haeriah', 'Rio Basana Margaretha Pane', 'Raden Muhammad Ali Fathoni', 
        'Aristia Rizki Putra', 'Umi Chulsum', 'Shinta Dewi Noviany', 
        'Rahma Kusuma Wardani', 'Muhammad Farhan', 'Siti Nurmala Sari', 'Farizal Julio Hakim',
    ]
    
    for nama in users_to_remove:
        connection.execute(
            sa.text("DELETE FROM users WHERE nama = :nama AND role = 'INSPEKTORAT'"),
            {'nama': nama}
        )
    
    print("✅ Additional inspektorat users have been removed successfully!")
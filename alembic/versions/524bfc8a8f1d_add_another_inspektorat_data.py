"""add_another_inspektorat_data

Revision ID: 524bfc8a8f1d
Revises: 6673f62706b9
Create Date: 2025-07-20 11:34:35.426651

"""
from typing import Sequence, Union

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from datetime import datetime
import uuid


# revision identifiers, used by Alembic.
revision: str = '524bfc8a8f1d'
down_revision: Union[str, Sequence[str], None] = '6673f62706b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing inspektorat users data."""
    
    # Get connection
    connection = op.get_bind()
    
    # Hash password @Kemendag123 (sama untuk semua user)
    default_password_hash = "$2b$12$6SO28mFb6kEi3QN8h14b5uOFTC6V218f/Tf6DKRMnni6oNiQWYmn2"
    
    # Helper function untuk generate username
    def generate_username(nama, inspektorat_num):
        """Generate username: nama_depan_ir{nomor}"""
        import re
        # Clean nama dan ambil kata pertama
        nama_clean = re.sub(r'[^a-zA-Z\s]', '', nama).strip()
        nama_depan = nama_clean.split()[0].lower()
        return f"{nama_depan}_ir{inspektorat_num}"
    
    def generate_username_with_second_name(nama, inspektorat_num):
        """Generate username dengan nama kedua untuk conflict resolution"""
        import re
        nama_clean = re.sub(r'[^a-zA-Z\s]', '', nama).strip()
        words = nama_clean.split()
        if len(words) >= 2:
            nama_depan = words[0].lower()
            nama_kedua = words[1].lower()
            return f"{nama_depan}_{nama_kedua}_ir{inspektorat_num}"
        return generate_username(nama, inspektorat_num)
    
    # Check existing usernames untuk avoid conflict
    existing_usernames = set()
    result = connection.execute(sa.text("SELECT username FROM users WHERE deleted_at IS NULL"))
    for row in result:
        existing_usernames.add(row.username)
    
    def get_available_username(nama, inspektorat_num):
        """Get available username dengan conflict resolution"""
        username = generate_username(nama, inspektorat_num)
        if username not in existing_usernames:
            existing_usernames.add(username)
            return username
        
        # Try dengan nama kedua
        username_alt = generate_username_with_second_name(nama, inspektorat_num)
        if username_alt not in existing_usernames:
            existing_usernames.add(username_alt)
            return username_alt
        
        # Fallback dengan nomor
        for i in range(1, 10):
            username_num = f"{username}{i}"
            if username_num not in existing_usernames:
                existing_usernames.add(username_num)
                return username_num
        
        # Ultimate fallback
        timestamp_suffix = str(int(datetime.utcnow().timestamp()) % 1000)
        final_username = f"{username}{timestamp_suffix}"
        existing_usernames.add(final_username)
        return final_username
    
    # ===== INSPEKTORAT I - TAMBAHAN (13 orang) =====
    # Yang sudah ada: Malahayati, Karunia Sari Nur Pangesti, Imatona Hasriya Harahap, Ririn Kurniani, Intan Permata Sari
    
    inspektorat_i_new = [
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
        {'nama': 'Elsa Zuhara Damayanti', 'jabatan': 'Auditor Ahli Pertama'}
    ]
    
    # ===== INSPEKTORAT II - TAMBAHAN (15 orang) =====
    # Yang sudah ada: Digdiyono Basuki Susanto, Iz Irene Farah Zubaida, Ditya Novita Dewi
    
    inspektorat_ii_new = [
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
        {'nama': 'Ikhlasul Ardi Dewantara', 'jabatan': 'Auditor Ahli Pertama'}
    ]
    
    # ===== INSPEKTORAT III - TAMBAHAN (16 orang) =====
    # Yang sudah ada: Asep Asmara, Daru Sukendri
    
    inspektorat_iii_new = [
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
        {'nama': 'Adinda Vinka Maharani', 'jabatan': 'Auditor Ahli Pertama'}
    ]
    
    # ===== INSPEKTORAT IV - TAMBAHAN (16 orang) =====
    # Yang sudah ada: Rr. Dyah Palupi, Etti Susilowaty
    
    inspektorat_iv_new = [
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
        {'nama': 'Muhammad Farhan', 'jabatan': 'Auditor Terampil'},  # Note: ada nama yang sama dengan Inspektorat III
        {'nama': 'Siti Nurmala Sari', 'jabatan': 'Auditor Ahli Pertama'},
        {'nama': 'Farizal Julio Hakim', 'jabatan': 'Auditor Ahli Pertama'}
    ]
    
    # Function untuk insert users
    def insert_inspektorat_users(users_data, inspektorat_name, inspektorat_num):
        """Insert users untuk inspektorat tertentu"""
        for user in users_data:
            user_id = str(uuid.uuid4())
            username = get_available_username(user['nama'], inspektorat_num)
            
            connection.execute(
                sa.text("""
                    INSERT INTO users (
                        id, nama, username, jabatan, hashed_password, 
                        email, is_active, role, inspektorat, created_at
                    ) VALUES (
                        :id, :nama, :username, :jabatan, :hashed_password,
                        :email, :is_active, :role, :inspektorat, :created_at
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
                    'inspektorat': inspektorat_name,
                    'created_at': datetime.utcnow()
                }
            )
            print(f"✅ Added: {user['nama']} → {username} ({inspektorat_name})")
    
    # Insert semua data baru
    print("🚀 Adding missing Inspektorat users...")
    
    insert_inspektorat_users(inspektorat_i_new, 'Inspektorat 1', 1)
    print(f"📊 Inspektorat 1: Added {len(inspektorat_i_new)} users")
    
    insert_inspektorat_users(inspektorat_ii_new, 'Inspektorat 2', 2)
    print(f"📊 Inspektorat 2: Added {len(inspektorat_ii_new)} users")
    
    insert_inspektorat_users(inspektorat_iii_new, 'Inspektorat 3', 3)
    print(f"📊 Inspektorat 3: Added {len(inspektorat_iii_new)} users")
    
    insert_inspektorat_users(inspektorat_iv_new, 'Inspektorat 4', 4)
    print(f"📊 Inspektorat 4: Added {len(inspektorat_iv_new)} users")
    
    total_added = len(inspektorat_i_new) + len(inspektorat_ii_new) + len(inspektorat_iii_new) + len(inspektorat_iv_new)
    print(f"✅ Successfully added {total_added} inspektorat users")
    
    # Verify total counts
    verification_query = sa.text("""
        SELECT inspektorat, COUNT(*) as total
        FROM users 
        WHERE role = 'INSPEKTORAT' AND deleted_at IS NULL
        GROUP BY inspektorat
        ORDER BY inspektorat
    """)
    
    print("\n📈 Final Inspektorat counts:")
    result = connection.execute(verification_query)
    for row in result:
        print(f"   {row.inspektorat}: {row.total} users")


def downgrade() -> None:
    """Remove added inspektorat users."""
    connection = op.get_bind()
    
    # List nama-nama yang ditambahkan di migration ini
    added_users = [
        # Inspektorat 1
        'Fenny Rosa', 'Daniel Maruli', 'Andi Ika Ovenia', 'Bunga Uli', 'Leo Spornayan',
        'Ruwarto', 'Raden Dicky Ramadhan', 'Ahmad Kiflan Deemas Anshari', 'Adittrasna Iyan Kuswindana',
        'Hana Nadhifa Khalda', 'Dara Nabila Usmaryoto', 'Okto Pendar W', 'Elsa Zuhara Damayanti',
        
        # Inspektorat 2
        'Puri Dinasti', 'Angga Widodo Saputro', 'Gusti Ayu Komang Ardiyani', 'Diah Ekowati N',
        'Rizky Beta Puspitasari', 'Widya Soehandoko', 'Lina Rahmawati', 'Tonny Anderson',
        'Nabila Auliyya Rodja', 'Ifham Ilmy Hakim', 'Kurnia Sari Dewi', 'Muhammad Adhitya Kusuma Istadi',
        'Rosalia Krenata Mufarokhah', 'Khalda Nabilah', 'Ikhlasul Ardi Dewantara',
        
        # Inspektorat 3
        'Tri Djuliyanto', 'Didiet Maharani Bahariyanti Purnama Dewi', 'Givana Arizani',
        'Yani Mulia Banjarsari', 'Wardini Wulansari', 'Elviana Novita', 'Berta',
        'Ezar Nurrizal Kamil', 'Ana Najiyya', 'Surya', 'Namira Tita Amelia',
        'Muhammad Adrian', 'Muhammad Farhan', 'Clarissa Putri Kharisma',
        'Raihanah Aulya Kusumaputri', 'Adinda Vinka Maharani',
        
        # Inspektorat 4
        'Lili Yuliadi', 'Raden Roro Dyah Lestari Adityas Ningrum', 'Windy Solihin',
        'Asnita Riani Sembiring', 'Fathoni Ahmad', 'Redho Alfasumma Putra', 'Yoyoh Haeriah',
        'Rio Basana Margaretha Pane', 'Raden Muhammad Ali Fathoni', 'Aristia Rizki Putra',
        'Umi Chulsum', 'Shinta Dewi Noviany', 'Rahma Kusuma Wardani', 'Siti Nurmala Sari',
        'Farizal Julio Hakim'
    ]
    
    # Note: Ada 2 "Muhammad Farhan" di Inspektorat 3 dan 4, jadi perlu hati-hati
    
    # Delete users yang ditambahkan
    for nama in added_users:
        connection.execute(
            sa.text("""
                DELETE FROM users 
                WHERE nama = :nama 
                AND role = 'INSPEKTORAT' 
                AND created_at > '2025-07-20 09:00:00'
            """),
            {'nama': nama}
        )
    
    print(f"🗑️ Removed {len(added_users)} inspektorat users added by this migration")


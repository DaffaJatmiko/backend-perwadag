"""init user data

Revision ID: 7711be8c3721
Revises: 
Create Date: 2025-07-14 23:04:49.702655

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, date
import uuid


# revision identifiers, used by Alembic.
revision: str = '7711be8c3721'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert initial users data."""
    
    # Get connection
    connection = op.get_bind()
    
    # Hash password @Kemendag123 (sama untuk semua user)
    # Generated using: bcrypt.hashpw("@Kemendag123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    default_password_hash = "$2b$12$6SO28mFb6kEi3QN8h14b5uOFTC6V218f/Tf6DKRMnni6oNiQWYmn2"
    
    # ===== ADMIN USERS =====
    admin_users = [
        {
            'id': 'admin-001',
            'nama': 'Administrator Sistem',
            'username': 'administrator01011990',
            'tempat_lahir': 'Jakarta',
            'tanggal_lahir': date(1990, 1, 1),
            'pangkat': 'Pembina Utama',
            'jabatan': 'Administrator Sistem Utama',
            'email': 'admin@kemendag.go.id',
            'role': 'ADMIN',
            'inspektorat': None
        }
    ]
    
    # ===== INSPEKTORAT USERS =====
    inspektorat_users = [
        # INSPEKTORAT I
        {
            'nama': 'Malahayati',
            'tempat_lahir': 'Jakarta',
            'tanggal_lahir': date(1966, 3, 26),
            'pangkat': 'IV/c',
            'jabatan': 'Auditor Ahli Madya',
            'role': 'INSPEKTORAT',
            'inspektorat': 'Inspektorat I'
        },
        {
            'nama': 'Karunia Sari Nur Pangesti',
            'tempat_lahir': 'Pekalongan',
            'tanggal_lahir': date(1984, 3, 28),
            'pangkat': 'IV/b',
            'jabatan': 'Auditor Ahli Madya',
            'role': 'INSPEKTORAT',
            'inspektorat': 'Inspektorat I'
        },
        {
            'nama': 'Imatona Hasriya Harahap',
            'tempat_lahir': 'Jakarta',
            'tanggal_lahir': date(1967, 5, 21),
            'pangkat': 'IV/a',
            'jabatan': 'Auditor Ahli Madya',
            'role': 'INSPEKTORAT',
            'inspektorat': 'Inspektorat I'
        },
        {
            'nama': 'Ririn Kurniani',
            'tempat_lahir': 'Jakarta',
            'tanggal_lahir': date(1975, 6, 12),
            'pangkat': 'III/d',
            'jabatan': 'Auditor Ahli Muda',
            'role': 'INSPEKTORAT',
            'inspektorat': 'Inspektorat I'
        },
        {
            'nama': 'Intan Permata Sari',
            'tempat_lahir': 'Tangerang',
            'tanggal_lahir': date(1985, 9, 19),
            'pangkat': 'III/d',
            'jabatan': 'Auditor Ahli Muda',
            'role': 'INSPEKTORAT',
            'inspektorat': 'Inspektorat I'
        },
        
        # INSPEKTORAT II  
        {
            'nama': 'Digdiyono Basuki Susanto',
            'tempat_lahir': 'Kediri',
            'tanggal_lahir': date(1970, 4, 8),
            'pangkat': 'IV/b',
            'jabatan': 'Inspektur II',
            'role': 'INSPEKTORAT',
            'inspektorat': 'Inspektorat II'
        },
        {
            'nama': 'Iz Irene Farah Zubaida',
            'tempat_lahir': 'Malang',
            'tanggal_lahir': date(1978, 9, 11),
            'pangkat': 'IV/b',
            'jabatan': 'Auditor Ahli Madya',
            'role': 'INSPEKTORAT',
            'inspektorat': 'Inspektorat II'
        },
        {
            'nama': 'Ditya Novita Dewi',
            'tempat_lahir': 'Jakarta',
            'tanggal_lahir': date(1980, 11, 19),
            'pangkat': 'IV/a',
            'jabatan': 'Auditor Ahli Madya',
            'role': 'INSPEKTORAT',
            'inspektorat': 'Inspektorat II'
        },
        
        # INSPEKTORAT III
        {
            'nama': 'Asep Asmara',
            'tempat_lahir': 'Jakarta',
            'tanggal_lahir': date(1966, 1, 5),
            'pangkat': 'IV/d',
            'jabatan': 'Inspektur III',
            'role': 'INSPEKTORAT',
            'inspektorat': 'Inspektorat III'
        },
        {
            'nama': 'Daru Sukendri',
            'tempat_lahir': 'Klaten',
            'tanggal_lahir': date(1962, 8, 10),
            'pangkat': 'IV/e',
            'jabatan': 'Auditor Ahli Utama',
            'role': 'INSPEKTORAT',
            'inspektorat': 'Inspektorat III'
        },
        
        # INSPEKTORAT IV
        {
            'nama': 'Rr. Dyah Palupi',
            'tempat_lahir': 'Jakarta',
            'tanggal_lahir': date(1966, 6, 26),
            'pangkat': 'IV/c',
            'jabatan': 'Inspektur IV',
            'role': 'INSPEKTORAT',
            'inspektorat': 'Inspektorat IV'
        },
        {
            'nama': 'Etti Susilowaty',
            'tempat_lahir': 'Pekalongan',
            'tanggal_lahir': date(1965, 7, 7),
            'pangkat': 'IV/d',
            'jabatan': 'Auditor Ahli Utama',
            'role': 'INSPEKTORAT',
            'inspektorat': 'Inspektorat IV'
        }
    ]
    
    # ===== PERWADAG USERS =====
    perwadag_users = [
        # INSPEKTORAT I
        {'nama': 'Atdag Moscow', 'inspektorat': 'Inspektorat I'},
        {'nama': 'Atdag Washington DC', 'inspektorat': 'Inspektorat I'},
        {'nama': 'ITPC Vancouver', 'inspektorat': 'Inspektorat I'},
        {'nama': 'Atdag Ottawa', 'inspektorat': 'Inspektorat I'},
        {'nama': 'Atdag Madrid', 'inspektorat': 'Inspektorat I'},
        {'nama': 'ITPC Johannesburg', 'inspektorat': 'Inspektorat I'},
        {'nama': 'Atdag Kairo', 'inspektorat': 'Inspektorat I'},
        {'nama': 'ITPC Osaka', 'inspektorat': 'Inspektorat I'},
        {'nama': 'ITPC Dubai', 'inspektorat': 'Inspektorat I'},
        {'nama': 'Atdag London', 'inspektorat': 'Inspektorat I'},
        {'nama': 'Atdag New Delhi', 'inspektorat': 'Inspektorat I'},
        {'nama': 'Atdag Manila', 'inspektorat': 'Inspektorat I'},
        
        # INSPEKTORAT II
        {'nama': 'Atdag Paris', 'inspektorat': 'Inspektorat II'},
        {'nama': 'ITPC Lagos', 'inspektorat': 'Inspektorat II'},
        {'nama': 'ITPC Barcelona', 'inspektorat': 'Inspektorat II'},
        {'nama': 'ITPC Budapest', 'inspektorat': 'Inspektorat II'},
        {'nama': 'ITPC Jeddah', 'inspektorat': 'Inspektorat II'},
        {'nama': 'Atdag Ankara', 'inspektorat': 'Inspektorat II'},
        {'nama': 'Atdag Canberra', 'inspektorat': 'Inspektorat II'},
        {'nama': 'Atdag Beijing', 'inspektorat': 'Inspektorat II'},
        {'nama': 'Atdag Roma', 'inspektorat': 'Inspektorat II'},
        {'nama': 'ITPC Chicago', 'inspektorat': 'Inspektorat II'},
        {'nama': 'ITPC Shanghai', 'inspektorat': 'Inspektorat II'},
        
        # INSPEKTORAT III
        {'nama': 'ITPC Sao Paulo', 'inspektorat': 'Inspektorat III'},
        {'nama': 'Konsuldag Hongkong', 'inspektorat': 'Inspektorat III'},
        {'nama': 'Atdag Tokyo', 'inspektorat': 'Inspektorat III'},
        {'nama': 'Atdag Seoul', 'inspektorat': 'Inspektorat III'},
        {'nama': 'Atdag Den Haag', 'inspektorat': 'Inspektorat III'},
        {'nama': 'ITPC Sydney', 'inspektorat': 'Inspektorat III'},
        {'nama': 'Atdag Jenewa', 'inspektorat': 'Inspektorat III'},
        {'nama': 'ITPC Los Angeles', 'inspektorat': 'Inspektorat III'},
        {'nama': 'ITPC Mexico City', 'inspektorat': 'Inspektorat III'},
        {'nama': 'Atdag Riyadh', 'inspektorat': 'Inspektorat III'},
        {'nama': 'Atdag Kuala Lumpur', 'inspektorat': 'Inspektorat III'},
        
        # INSPEKTORAT IV
        {'nama': 'ITPC Santiago', 'inspektorat': 'Inspektorat IV'},
        {'nama': 'Atdag Hanoi', 'inspektorat': 'Inspektorat IV'},
        {'nama': 'Atdag Brussels', 'inspektorat': 'Inspektorat IV'},
        {'nama': 'Atdag Singapura', 'inspektorat': 'Inspektorat IV'},
        {'nama': 'Atdag Berlin', 'inspektorat': 'Inspektorat IV'},
        {'nama': 'Atdag Bangkok', 'inspektorat': 'Inspektorat IV'},
        {'nama': 'ITPC Busan', 'inspektorat': 'Inspektorat IV'},
        {'nama': 'ITPC Milan', 'inspektorat': 'Inspektorat IV'},
        {'nama': 'KDEI Taipei', 'inspektorat': 'Inspektorat IV'},
        {'nama': 'ITPC Hamburg', 'inspektorat': 'Inspektorat IV'},
        {'nama': 'ITPC Chennai', 'inspektorat': 'Inspektorat IV'},
        {'nama': 'Dubes WTO', 'inspektorat': 'Inspektorat IV'}
    ]
    
    # Helper functions
    def generate_username_admin_inspektorat(nama, tanggal_lahir):
        """Generate username untuk admin/inspektorat: nama_depan + ddmmyyyy"""
        import re
        nama_clean = re.sub(r'[^a-zA-Z\s]', '', nama).strip()
        nama_depan = nama_clean.split()[0].lower()
        return f"{nama_depan}{tanggal_lahir.strftime('%d%m%Y')}"
    
    def generate_username_perwadag(nama):
        """Generate username untuk perwadag: format khusus"""
        import re
        # Remove special chars and normalize
        nama_clean = re.sub(r'[–—\-\s]+', '_', nama.lower())
        nama_clean = re.sub(r'[^a-z0-9_]', '', nama_clean)
        
        # Extract meaningful parts
        parts = nama_clean.split('_')
        if len(parts) >= 2:
            return f"{parts[0]}_{parts[1]}"
        return parts[0] if parts else "perwadag"
    
    # Insert Admin users
    for user in admin_users:
        connection.execute(
            sa.text("""
                INSERT INTO users (
                    id, nama, username, tempat_lahir, tanggal_lahir, 
                    pangkat, jabatan, hashed_password, email, is_active, 
                    role, inspektorat, created_at
                ) VALUES (
                    :id, :nama, :username, :tempat_lahir, :tanggal_lahir,
                    :pangkat, :jabatan, :hashed_password, :email, :is_active,
                    :role, :inspektorat, :created_at
                )
            """),
            {
                'id': user['id'],
                'nama': user['nama'],
                'username': user['username'],
                'tempat_lahir': user['tempat_lahir'],
                'tanggal_lahir': user['tanggal_lahir'],
                'pangkat': user['pangkat'],
                'jabatan': user['jabatan'],
                'hashed_password': default_password_hash,
                'email': user['email'],
                'is_active': True,
                'role': user['role'],
                'inspektorat': user['inspektorat'],
                'created_at': datetime.utcnow()
            }
        )
    
    # Insert Inspektorat users
    for user in inspektorat_users:
        user_id = str(uuid.uuid4())
        username = generate_username_admin_inspektorat(user['nama'], user['tanggal_lahir'])
        
        connection.execute(
            sa.text("""
                INSERT INTO users (
                    id, nama, username, tempat_lahir, tanggal_lahir, 
                    pangkat, jabatan, hashed_password, email, is_active, 
                    role, inspektorat, created_at
                ) VALUES (
                    :id, :nama, :username, :tempat_lahir, :tanggal_lahir,
                    :pangkat, :jabatan, :hashed_password, :email, :is_active,
                    :role, :inspektorat, :created_at
                )
            """),
            {
                'id': user_id,
                'nama': user['nama'],
                'username': username,
                'tempat_lahir': user['tempat_lahir'],
                'tanggal_lahir': user['tanggal_lahir'],
                'pangkat': user['pangkat'],
                'jabatan': user['jabatan'],
                'hashed_password': default_password_hash,
                'email': None,
                'is_active': True,
                'role': user['role'],
                'inspektorat': user['inspektorat'],
                'created_at': datetime.utcnow()
            }
        )
    
    # Insert Perwadag users
    for user in perwadag_users:
        user_id = str(uuid.uuid4())
        username = generate_username_perwadag(user['nama'])
        
        connection.execute(
            sa.text("""
                INSERT INTO users (
                    id, nama, username, tempat_lahir, tanggal_lahir, 
                    pangkat, jabatan, hashed_password, email, is_active, 
                    role, inspektorat, created_at
                ) VALUES (
                    :id, :nama, :username, :tempat_lahir, :tanggal_lahir,
                    :pangkat, :jabatan, :hashed_password, :email, :is_active,
                    :role, :inspektorat, :created_at
                )
            """),
            {
                'id': user_id,
                'nama': user['nama'],
                'username': username,
                'tempat_lahir': 'Jakarta',  # Default
                'tanggal_lahir': date(1990, 1, 1),  # Default
                'pangkat': 'Madya',  # Default
                'jabatan': 'Perwakilan Dagang',  # Default
                'hashed_password': default_password_hash,
                'email': None,
                'is_active': True,
                'role': 'PERWADAG',
                'inspektorat': user['inspektorat'],
                'created_at': datetime.utcnow()
            }
        )

def downgrade() -> None:
    """Remove initial users data."""
    connection = op.get_bind()
    
    # Delete all users yang di-insert oleh migration ini
    connection.execute(
        sa.text("DELETE FROM users WHERE id = 'admin-001' OR role IN ('INSPEKTORAT', 'PERWADAG')")
    )
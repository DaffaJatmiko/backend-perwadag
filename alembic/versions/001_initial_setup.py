from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text
from datetime import datetime
import uuid

# revision identifiers, used by Alembic.
revision: str = '001_initial_setup'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create UserRole enum type (only if not exists)
    connection = op.get_bind()
    result = connection.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'userrole'"))
    if not result.fetchone():
        user_role_enum = postgresql.ENUM('ADMIN', 'INSPEKTORAT', 'PERWADAG', name='userrole')
        user_role_enum.create(connection)
    
    # Create users table (only if not exists)
    if not connection.execute(sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = 'users'")).fetchone():
        op.create_table('users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('nama', sa.String(length=200), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('jabatan', sa.String(length=200), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('role', postgresql.ENUM('ADMIN', 'INSPEKTORAT', 'PERWADAG', name='userrole'), nullable=False),
        sa.Column('inspektorat', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_nama'), 'users', ['nama'], unique=False)
        op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
        op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    
    # Create password_reset_tokens table (only if not exists)
    if not connection.execute(sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = 'password_reset_tokens'")).fetchone():
        op.create_table('password_reset_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_password_reset_tokens_token'), 'password_reset_tokens', ['token'], unique=True)
        op.create_index(op.f('ix_password_reset_tokens_user_id'), 'password_reset_tokens', ['user_id'], unique=False)
    
    # Hash password @Kemendag123 (sama untuk semua user)
    # Generated using: bcrypt.hashpw("@Kemendag123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    default_password_hash = "$2b$12$6SO28mFb6kEi3QN8h14b5uOFTC6V218f/Tf6DKRMnni6oNiQWYmn2"
    
    # Helper functions
    def generate_username_admin(nama):
        """Generate username untuk admin: nama lowercase"""
        import re
        nama_clean = re.sub(r'[^a-zA-Z\s]', '', nama).strip()
        return nama_clean.replace(' ', '').lower()
    
    def generate_username_inspektorat(nama, inspektorat):
        """Generate username untuk inspektorat: nama_depan + _ir + nomor_inspektorat"""
        import re
        nama_clean = re.sub(r'[^a-zA-Z\s]', '', nama).strip()
        nama_depan = nama_clean.split()[0].lower()
        
        # Extract nomor inspektorat (1, 2, 3, 4)
        inspektorat_map = {
            'Inspektorat 1': '1',
            'Inspektorat 2': '2', 
            'Inspektorat 3': '3',
            'Inspektorat 4': '4'
        }
        nomor = inspektorat_map.get(inspektorat, '1')
        
        return f"{nama_depan}_ir{nomor}"
    
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
    
    # ===== INSERT ADMIN USER =====
    admin_username = generate_username_admin('Administrator')
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
            'id': 'admin-001',
            'nama': 'Administrator',
            'username': admin_username,
            'jabatan': 'Administrator Sistem Utama',
            'hashed_password': default_password_hash,
            'email': 'projectkemendag@gmail.com',
            'is_active': True,
            'role': 'ADMIN',
            'inspektorat': None,
            'created_at': datetime.utcnow()
        }
    )
    
    # ===== INSERT INSPEKTORAT USERS =====
    inspektorat_users = [
        # INSPEKTORAT 1
        {'nama': 'Malahayati', 'jabatan': 'Auditor Ahli Madya', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'Karunia Sari Nur Pangesti', 'jabatan': 'Auditor Ahli Madya', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'Imatona Hasriya Harahap', 'jabatan': 'Auditor Ahli Madya', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'Ririn Kurniani', 'jabatan': 'Auditor Ahli Muda', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'Intan Permata Sari', 'jabatan': 'Auditor Ahli Muda', 'inspektorat': 'Inspektorat 1'},
        
        # INSPEKTORAT 2  
        {'nama': 'Digdiyono Basuki Susanto', 'jabatan': 'Inspektur II', 'inspektorat': 'Inspektorat 2'},
        {'nama': 'Iz Irene Farah Zubaida', 'jabatan': 'Auditor Ahli Madya', 'inspektorat': 'Inspektorat 2'},
        {'nama': 'Ditya Novita Dewi', 'jabatan': 'Auditor Ahli Madya', 'inspektorat': 'Inspektorat 2'},
        
        # INSPEKTORAT 3
        {'nama': 'Asep Asmara', 'jabatan': 'Inspektur III', 'inspektorat': 'Inspektorat 3'},
        {'nama': 'Daru Sukendri', 'jabatan': 'Auditor Ahli Utama', 'inspektorat': 'Inspektorat 3'},
        
        # INSPEKTORAT 4
        {'nama': 'Rr. Dyah Palupi', 'jabatan': 'Inspektur IV', 'inspektorat': 'Inspektorat 4'},
        {'nama': 'Etti Susilowaty', 'jabatan': 'Auditor Ahli Utama', 'inspektorat': 'Inspektorat 4'}
    ]
    
    for user in inspektorat_users:
        user_id = str(uuid.uuid4())
        username = generate_username_inspektorat(user['nama'], user['inspektorat'])
        
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
                'inspektorat': user['inspektorat'],
                'created_at': datetime.utcnow()
            }
        )
    
    # ===== INSERT PERWADAG USERS =====
    # ===== INSERT PERWADAG USERS =====
    perwadag_users = [
        # INSPEKTORAT 1
        {'nama': 'Atdag Moscow', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'Atdag Washington DC', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'ITPC Vancouver', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'Atdag Ottawa', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'Atdag Madrid', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'ITPC Johannesburg', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'Atdag Kairo', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'ITPC Osaka', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'ITPC Dubai', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'Atdag London', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'Atdag New Delhi', 'inspektorat': 'Inspektorat 1'},
        {'nama': 'Atdag Manila', 'inspektorat': 'Inspektorat 1'},
        
        # INSPEKTORAT 2
        {'nama': 'Atdag Paris', 'inspektorat': 'Inspektorat 2'},
        {'nama': 'ITPC Lagos', 'inspektorat': 'Inspektorat 2'},
        {'nama': 'ITPC Barcelona', 'inspektorat': 'Inspektorat 2'},
        {'nama': 'ITPC Budapest', 'inspektorat': 'Inspektorat 2'},
        {'nama': 'ITPC Jeddah', 'inspektorat': 'Inspektorat 2'},
        {'nama': 'Atdag Ankara', 'inspektorat': 'Inspektorat 2'},
        {'nama': 'Atdag Canberra', 'inspektorat': 'Inspektorat 2'},
        {'nama': 'Atdag Beijing', 'inspektorat': 'Inspektorat 2'},
        {'nama': 'Atdag Roma', 'inspektorat': 'Inspektorat 2'},
        {'nama': 'ITPC Chicago', 'inspektorat': 'Inspektorat 2'},
        {'nama': 'ITPC Shanghai', 'inspektorat': 'Inspektorat 2'},
        
        # INSPEKTORAT 3
        {'nama': 'ITPC Sao Paulo', 'inspektorat': 'Inspektorat 3'},
        {'nama': 'Konsuldag Hongkong', 'inspektorat': 'Inspektorat 3'},
        {'nama': 'Atdag Tokyo', 'inspektorat': 'Inspektorat 3'},
        {'nama': 'Atdag Seoul', 'inspektorat': 'Inspektorat 3'},
        {'nama': 'Atdag Den Haag', 'inspektorat': 'Inspektorat 3'},
        {'nama': 'ITPC Sydney', 'inspektorat': 'Inspektorat 3'},
        {'nama': 'Atdag Jenewa', 'inspektorat': 'Inspektorat 3'},
        {'nama': 'ITPC Los Angeles', 'inspektorat': 'Inspektorat 3'},
        {'nama': 'ITPC Mexico City', 'inspektorat': 'Inspektorat 3'},
        {'nama': 'Atdag Riyadh', 'inspektorat': 'Inspektorat 3'},
        {'nama': 'Atdag Kuala Lumpur', 'inspektorat': 'Inspektorat 3'},
        
        # INSPEKTORAT 4
        {'nama': 'ITPC Santiago', 'inspektorat': 'Inspektorat 4'},
        {'nama': 'Atdag Hanoi', 'inspektorat': 'Inspektorat 4'},
        {'nama': 'Atdag Brussels', 'inspektorat': 'Inspektorat 4'},
        {'nama': 'Atdag Singapura', 'inspektorat': 'Inspektorat 4'},
        {'nama': 'Atdag Berlin', 'inspektorat': 'Inspektorat 4'},
        {'nama': 'Atdag Bangkok', 'inspektorat': 'Inspektorat 4'},
        {'nama': 'ITPC Busan', 'inspektorat': 'Inspektorat 4'},
        {'nama': 'ITPC Milan', 'inspektorat': 'Inspektorat 4'},
        {'nama': 'KDEI Taipei', 'inspektorat': 'Inspektorat 4'},
        {'nama': 'ITPC Hamburg', 'inspektorat': 'Inspektorat 4'},
        {'nama': 'ITPC Chennai', 'inspektorat': 'Inspektorat 4'},
        {'nama': 'Dubes WTO', 'inspektorat': 'Inspektorat 4'}
    ]
    
    for user in perwadag_users:
        user_id = str(uuid.uuid4())
        username = generate_username_perwadag(user['nama'])
        
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
                'jabatan': 'Perwakilan Dagang',
                'hashed_password': default_password_hash,
                'email': None,
                'is_active': True,
                'role': 'PERWADAG',
                'inspektorat': user['inspektorat'],
                'created_at': datetime.utcnow()
            }
        )


def downgrade() -> None:
    # Drop tables
    op.drop_index(op.f('ix_password_reset_tokens_user_id'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_password_reset_tokens_token'), table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
    
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_role'), table_name='users')
    op.drop_index(op.f('ix_users_nama'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    # Drop enum type
    user_role_enum = postgresql.ENUM('ADMIN', 'INSPEKTORAT', 'PERWADAG', name='userrole')
    user_role_enum.drop(op.get_bind())
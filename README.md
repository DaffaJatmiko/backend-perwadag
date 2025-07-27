# 🏛️ Perwadag Backend - API Sistem Evaluasi Pemerintahan

Backend API untuk **Sistem Evaluasi Perdagangan (Perwadag)** yang dibangun dengan FastAPI, PostgreSQL, dan arsitektur modern. Sistem ini menyediakan REST API yang komprehensif untuk mengelola proses evaluasi pemerintahan dengan fitur autentikasi, manajemen user, workflow evaluasi, dan pelaporan.

## 🏗️ Arsitektur Sistem

API ini dirancang dengan arsitektur berlapis yang bersih dan modular:

- **API Layer** - FastAPI endpoints dengan dokumentasi otomatis
- **Service Layer** - Business logic dan orchestration
- **Repository Layer** - Data access dan database operations
- **Model Layer** - SQLAlchemy models dan database schema
- **Auth Layer** - JWT authentication dan role-based authorization

## 🚀 Getting Started

### Prerequisites

Pastikan Anda memiliki yang berikut terinstal:

- **Docker** & **Docker Compose** (Recommended)
- **Python** >= 3.11 (untuk development tanpa Docker)
- **PostgreSQL** >= 14 (jika tidak menggunakan Docker)

## 🐳 Docker Setup (Recommended)

### Quick Start dengan Docker

1. **Clone repository:**
```bash
git clone https://github.com/DaffaJatmiko/backend-perwadag.git backend
cd perwadag/backend
```

2. **Setup environment variables:**
```bash
# File .env sudah ada dengan konfigurasi default
# Edit .env untuk production atau sesuai kebutuhan
```

3. **Start semua services:**
```bash
# Start database & redis
docker compose up -d postgres redis

# Build dan start application
docker compose up -d app

# Jalankan database migration
docker compose exec app alembic upgrade head
```

4. **Akses aplikasi:**
- API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Database: `localhost:5432` (untuk debugging)

### Docker Commands

```bash
# Stop semua services
docker compose down

# Stop dan hapus volumes (reset database)
docker compose down -v

# Rebuild application (setelah code changes)
docker compose build --no-cache app
docker compose up -d app

# View logs
docker compose logs app
docker compose logs postgres

# Execute commands dalam container
docker compose exec app alembic upgrade head
docker compose exec app python scripts/seed_data.py
docker compose exec postgres psql -U postgres -d perwadag
```

### Hot Reload untuk Development

Docker sudah dikonfigurasi untuk hot reload:
- Source code di-mount ke container
- FastAPI otomatis restart ketika ada perubahan kode
- Ubah kode → simpan → aplikasi otomatis restart

### Environment Variables untuk Docker

File `.env` sudah dikonfigurasi untuk Docker dengan:

```env
# Database (Docker networking)
POSTGRES_SERVER=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=perwadag

# Redis (Docker networking)
REDIS_HOST=redis

# Application
DEBUG=true
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## 💻 Local Development (Tanpa Docker)

### Prerequisites Local

- **Python** >= 3.11
- **PostgreSQL** >= 14
- **Redis** >= 6
- **pip** untuk dependency management

### Installation Local

1. **Clone repository:**
```bash
git clone https://github.com/DaffaJatmiko/backend-perwadag.git backend
cd perwadag/backend
```

2. **Setup virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# atau
venv\Scripts\activate     # Windows
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Setup database lokal:**
```bash
# Buat database PostgreSQL
createdb perwadag

# Update .env untuk local database
# POSTGRES_SERVER=localhost
# REDIS_HOST=localhost
```

5. **Jalankan migrasi:**
```bash
alembic upgrade head
```

6. **Run aplikasi:**
```bash
python main.py
```

API akan berjalan di `http://localhost:8000`

## 📜 Environment Variables

Buat file `.env` dengan konfigurasi berikut:

```env
# Database
DATABASE_URL=postgresql://username:password@localhost/perwadag_db

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Email (untuk password reset)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# File Upload
UPLOADS_PATH=static/uploads
MAX_FILE_SIZE=10485760  # 10MB

# Rate Limiting
RATE_LIMIT_CALLS=100
RATE_LIMIT_PERIOD=60
AUTH_RATE_LIMIT_CALLS=5
AUTH_RATE_LIMIT_PERIOD=60

# Application
PROJECT_NAME=Sistem Evaluasi Perwadag
VERSION=1.0.0
DEBUG=true
```

## 🛠️ Tech Stack

### Core Framework
- **FastAPI** - Modern, fast web framework untuk building APIs
- **Python 3.11+** - Bahasa pemrograman dengan type hints
- **Uvicorn** - ASGI server untuk production

### Database
- **PostgreSQL** - Database relasional yang robust
- **SQLAlchemy** - ORM Python yang powerful
- **Alembic** - Database migration tool

### Authentication & Security
- **JWT** - JSON Web Tokens untuk authentication
- **bcrypt** - Password hashing yang aman
- **python-jose** - JWT implementation untuk Python

### Validation & Serialization
- **Pydantic** - Data validation menggunakan Python type hints
- **email-validator** - Validasi email address

### File Handling
- **python-multipart** - Untuk file upload
- **Pillow** - Image processing (jika diperlukan)

### Development Tools
- **pytest** - Testing framework
- **black** - Code formatter
- **isort** - Import sorter
- **mypy** - Static type checker

## 📁 Struktur Proyek

```
backend/
├── src/
│   ├── api/
│   │   ├── endpoints/            # API endpoints
│   │   │   ├── auth.py          # Authentication endpoints
│   │   │   ├── users.py         # User management
│   │   │   ├── surat_tugas.py   # Surat tugas evaluasi
│   │   │   ├── meeting.py       # Entry/Exit meeting
│   │   │   ├── kuisioner.py     # Kuisioner evaluasi
│   │   │   └── files.py         # File upload/download
│   │   └── router.py            # Main API router
│   ├── auth/
│   │   ├── jwt.py              # JWT utilities
│   │   └── permissions.py       # Role-based permissions
│   ├── core/
│   │   ├── config.py           # Application configuration
│   │   └── database.py         # Database connection
│   ├── middleware/
│   │   ├── error_handler.py    # Global error handling
│   │   ├── rate_limiting.py    # Rate limiting
│   │   └── logging.py          # Request logging
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py            # User model
│   │   ├── surat_tugas.py     # Surat tugas model
│   │   ├── meeting.py         # Meeting models
│   │   └── kuisioner.py       # Kuisioner model
│   ├── repositories/           # Data access layer
│   │   ├── user.py            # User repository
│   │   ├── surat_tugas.py     # Surat tugas repository
│   │   └── meeting.py         # Meeting repository
│   ├── schemas/                # Pydantic schemas
│   │   ├── user.py            # User schemas
│   │   ├── surat_tugas.py     # Surat tugas schemas
│   │   └── auth.py            # Authentication schemas
│   ├── services/               # Business logic
│   │   ├── auth.py            # Authentication service
│   │   ├── user.py            # User service
│   │   ├── surat_tugas.py     # Surat tugas service
│   │   └── email.py           # Email service
│   └── utils/
│       ├── logging.py         # Logging utilities
│       └── username_generator.py # Username generation
├── alembic/                   # Database migrations
│   ├── versions/             # Migration files
│   └── env.py               # Alembic configuration
├── static/
│   └── uploads/             # Uploaded files
├── tests/                   # Test files
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── alembic.ini             # Alembic configuration
├── doc-api.md              # API documentation
└── README.md               # File ini
```

## 🌟 Fitur API

### 🔐 Authentication & Authorization
- **JWT-based Authentication** - Access dan refresh tokens
- **Role-based Access Control** - Admin, Inspektorat, Perwadag roles
- **Password Reset** - Reset password via email

### 👥 User Management
- **Multi-role User System** - Kelola user dengan berbagai role
- **Profile Management** - User dapat update profil sendiri
- **Username Auto-generation** - Generate username otomatis dari nama
- **User Statistics** - Statistik user untuk dashboard admin

### 📋 Workflow Evaluasi
- **Surat Tugas** - CRUD surat tugas dengan auto-generate workflow
- **Surat Pemberitahuan** - Notifikasi evaluasi
- **Meeting Management** - Entry dan exit meeting
- **Konfirmasi Meeting** - Konfirmasi jadwal meeting
- **Matriks Evaluasi** - Input dan kelola matriks penilaian
- **Kuisioner** - Template dan pengisian kuisioner
- **Laporan Hasil** - Generate dan kelola laporan evaluasi

### 📁 File Management
- **File Upload/Download** - Upload dokumen dengan validasi
- **Static File Serving** - Serve uploaded files
- **File Type Validation** - Validasi tipe file yang diizinkan

### 🔍 Search & Filtering
- **Advanced Filtering** - Filter berdasarkan berbagai kriteria
- **Pagination** - Pagination untuk semua list endpoints
- **Search Functionality** - Full-text search di berbagai field

## 📚 API Documentation

### Akses Dokumentasi
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

### Dokumentasi Lengkap
Lihat [doc-api.md](./doc-api.md) untuk dokumentasi API yang komprehensif dengan:
- Semua endpoints dan parameter
- Request/response schemas
- Authentication requirements
- Contoh penggunaan

## 🔧 Database Management

### Migrasi Database

#### Dengan Docker:
```bash
# Buat migrasi baru
docker compose exec app alembic revision --autogenerate -m "Deskripsi perubahan"

# Jalankan migrasi
docker compose exec app alembic upgrade head

# Rollback migrasi
docker compose exec app alembic downgrade -1

# Reset database lengkap
docker compose down -v
docker compose up -d postgres redis
docker compose exec app alembic upgrade head
```

#### Tanpa Docker:
```bash
# Buat migrasi baru
alembic revision --autogenerate -m "Deskripsi perubahan"

# Jalankan migrasi
alembic upgrade head

# Rollback migrasi
alembic downgrade -1
```

### Initial Database Setup

Database migration `001_initial_setup.py` sudah menyertakan:

**Sample Users dengan password default: `@Kemendag123`**

1. **Admin User:**
   - Username: `administrator`
   - Email: `projectkemendag@gmail.com`
   - Role: `ADMIN`

2. **Inspektorat Users** (12 users):
   - Inspektorat 1-4 dengan format username: `{nama_depan}_ir{nomor}`
   - Role: `INSPEKTORAT`

3. **Perwadag Users** (54 users):
   - Berbagai perwakilan dagang global
   - Format username: `{prefix}_{location}`
   - Role: `PERWADAG`

### Database Reset untuk Production

```bash
# HATI-HATI: Ini akan menghapus semua data!
docker compose down -v
docker compose up -d postgres redis
docker compose exec app alembic upgrade head
```

## 🧪 Testing

### Jalankan Tests

```bash
# Jalankan semua tests
pytest

# Jalankan tests dengan coverage
pytest --cov=src

# Jalankan tests tertentu
pytest tests/test_auth.py
```

### Test Structure

```
tests/
├── conftest.py              # Test configuration
├── test_auth.py            # Authentication tests
├── test_users.py           # User management tests
├── test_surat_tugas.py     # Surat tugas tests
└── test_api/               # API endpoint tests
```

## 🚀 Deployment

### Development dengan Docker

```bash
# Hot reload enabled untuk development
docker compose up -d
```

### Production dengan Docker

1. **Update .env untuk production:**
```env
DEBUG=false
POSTGRES_PASSWORD=strong-production-password
JWT_SECRET_KEY=secure-production-jwt-key-min-32-chars
CORS_ORIGINS=https://yourdomain.com
EMAIL_SMTP_USERNAME=your-production-email
EMAIL_SMTP_PASSWORD=your-app-password
```

2. **Build dan deploy:**
```bash
# Remove --reload flag dari Dockerfile untuk production
# Edit Dockerfile: CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Build production image
docker compose build --no-cache app

# Start production
docker compose up -d
```

### Production Docker Compose Override

Buat `docker-compose.prod.yml`:
```yaml
services:
  app:
    command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
    environment:
      - DEBUG=false
    volumes:
      # Remove source code mounting untuk production
      - ./static/uploads:/app/static/uploads
      - ./logs:/app/logs
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
```

Deploy production:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Production tanpa Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Set production environment
export DEBUG=false
export POSTGRES_SERVER=your-db-host
export JWT_SECRET_KEY=your-secure-key

# Run dengan multiple workers
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📊 Monitoring & Logging

### Health Checks
- **Health Endpoint**: `GET /health`
- **API Info**: `GET /api/v1/info`

### Logging
- Structured logging dengan JSON format
- Request/response logging
- Error tracking dengan stack traces

### Rate Limiting
- Global rate limiting: 100 requests/minute
- Auth endpoints: 5 requests/minute
- Configurable per endpoint

## 🔒 Security Features

- **Password Hashing** - bcrypt dengan salt
- **JWT Security** - Secure token generation dan validation
- **CORS Configuration** - Configurable CORS origins
- **Input Validation** - Pydantic schema validation
- **SQL Injection Protection** - SQLAlchemy ORM
- **Rate Limiting** - Prevent abuse dan DDoS

## 🤝 Contributing

1. Fork repository
2. Buat feature branch (`git checkout -b feature/amazing-feature`)
3. Commit perubahan (`git commit -m 'Add some amazing feature'`)
4. Push ke branch (`git push origin feature/amazing-feature`)
5. Buka Pull Request

### Code Style

```bash
# Format code
black src/

# Sort imports
isort src/

# Type checking
mypy src/
```

## 📄 License

Proyek ini dilisensikan di bawah MIT License - lihat file [LICENSE](LICENSE) untuk detail.

## 🆘 Support

Jika Anda mengalami masalah atau memiliki pertanyaan:

1. Periksa [dokumentasi API](./doc-api.md)
2. Cari [issues](../../issues) yang sudah ada
3. Buat [issue baru](../../issues/new) jika diperlukan

---

Dibangun dengan ❤️ untuk Sistem Evaluasi Pemerintahan Indonesia
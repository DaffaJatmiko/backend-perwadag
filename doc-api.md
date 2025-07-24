# API Documentation - Perwadag Backend

## Overview
This document provides comprehensive mapping of all API endpoints in the Perwadag Backend system, including their request/response schemas, authentication requirements, and functionality.

## Base URL
All endpoints are prefixed with the base URL configured in your environment.

## Authentication Endpoints
**Base Path**: `/auth`

| Method | Route | Request Schema | Response Schema | Auth Required | Description |
|--------|-------|---------------|----------------|---------------|-------------|
| POST | `/login` | `UserLogin` | `Token` | None | Login with nama (as username) and password |
| POST | `/refresh` | `TokenRefresh` | `Token` | None | Refresh access token using refresh token |
| POST | `/logout` | None | `MessageResponse` | JWT | Logout current user |
| GET | `/password-reset-eligibility` | None | Dict | JWT | Check if user is eligible for password reset |
| POST | `/request-password-reset` | `PasswordReset` | `MessageResponse` | None | Request password reset token |
| POST | `/confirm-password-reset` | `PasswordResetConfirm` | `MessageResponse` | None | Confirm password reset with token |
| POST | `/change-password` | `UserChangePassword` | `MessageResponse` | JWT | Change current user password |
| GET | `/verify-token` | None | Dict | JWT | Verify if JWT token is valid |
| GET | `/default-password-info` | None | Dict | JWT | Get default password policy info |

### Key Features:
- Simplified authentication using nama (full name) as username
- JWT-based authentication with access and refresh tokens
- Password reset functionality via email
- Default password system: All users start with `@Kemendag123`
- Token verification for frontend applications
- Role-based password information access

### Request/Response Schemas:

#### **UserLogin**
```json
{
  "username": "string (nama lengkap)",
  "password": "string (minimum 1 char)"
}
```

#### **Token**
```json
{
  "access_token": "string",
  "refresh_token": "string", 
  "token_type": "bearer",
  "expires_in": "int (seconds)",
  "user": "UserResponse"
}
```

#### **TokenRefresh**
```json
{
  "refresh_token": "string"
}
```

#### **PasswordReset**
```json
{
  "email": "string (valid email, must be set in profile first)"
}
```

#### **PasswordResetConfirm**
```json
{
  "token": "string (reset token from email)",
  "new_password": "string (minimum 6 chars, max 128 chars)"
}
```

#### **UserChangePassword**
```json
{
  "current_password": "string (current password)",
  "new_password": "string (minimum 6 chars, max 128 chars)"
}
```

#### **Password Reset Eligibility Response**
```json
{
  "eligible": "bool",
  "has_email": "bool",
  "email": "string or null",
  "message": "string (explanation)"
}
```

#### **Token Verification Response**
```json
{
  "valid": "bool",
  "user_id": "string",
  "nama": "string",
  "roles": ["string"],
  "message": "string"
}
```

#### **Default Password Info Response**
```json
{
  "message": "string",
  "description": "string",
  "recommendation": "string",
  "policy": "string",
  "actual_password": "string (admin only)"
}
```

### Authentication Flow:
1. **Login**: POST `/auth/login` with `nama` and `password`
2. **Token Usage**: Include `Authorization: Bearer <access_token>` in headers
3. **Token Refresh**: POST `/auth/refresh` when access token expires
4. **Password Reset**: 
   - Check eligibility: GET `/auth/password-reset-eligibility`
   - Request reset: POST `/auth/request-password-reset`
   - Confirm reset: POST `/auth/confirm-password-reset`
5. **Change Password**: POST `/auth/change-password` with current and new password

### Login Examples:
```json
{
  "username": "Administrator Sistem",
  "password": "@Kemendag123"
}
```

```json
{
  "username": "ITPC Lagos – Nigeria", 
  "password": "@Kemendag123"
}
```

### Password Reset Process:
1. User must first set email address via PUT `/users/me`
2. Check eligibility via GET `/auth/password-reset-eligibility`
3. Request reset token via POST `/auth/request-password-reset`
4. Check email for reset link with token
5. Confirm reset with token via POST `/auth/confirm-password-reset`

### Security Notes:
- All users start with default password `@Kemendag123`
- Password reset requires email to be set in user profile first
- Reset tokens expire after 1 hour
- Case-sensitive nama matching for login
- JWT tokens have configurable expiration times

---

## 1. Users Endpoints
**Base Path**: `/users`

| Method | Route | Request Schema | Response Schema | Auth Required | Description |
|--------|-------|---------------|----------------|---------------|-------------|
| GET | `/me` | None | `UserResponse` | JWT | Get current user profile |
| PUT | `/me` | `UserUpdate` | `UserResponse` | JWT | Update current user profile |
| POST | `/me/change-password` | `UserChangePassword` | `MessageResponse` | JWT | Change current user password |
| GET | `/` | `UserFilterParams` | `UserListResponse` | Admin/Inspektorat | Get all users with filters |
| GET | `/by-role/{role_name}` | None | `List[UserSummary]` | Admin/Inspektorat | Get users by role |
| GET | `/statistics` | None | Dict | Admin | Get user statistics |
| POST | `/preview-username` | `UsernameGenerationPreview` | `UsernameGenerationResponse` | Admin | Preview username generation |
| POST | `/` | `UserCreate` | `UserResponse` | Admin | Create new user |
| GET | `/perwadag` | `PerwadagSearchParams` | `PerwadagListResponse` | JWT | Search perwadag users |
| GET | `/{user_id}` | None | `UserResponse` | JWT + Access Control | Get user by ID |
| PUT | `/{user_id}` | `UserUpdate` | `UserResponse` | Admin | Update user |
| POST | `/{user_id}/reset-password` | None | `MessageResponse` | Admin | Reset user password |
| POST | `/{user_id}/activate` | None | `UserResponse` | Admin | Activate user |
| POST | `/{user_id}/deactivate` | None | `UserResponse` | Admin | Deactivate user |
| DELETE | `/{user_id}` | None | `MessageResponse` | Admin | Soft delete user |

### Key Features:
- Simplified user management with role-based access (ADMIN, INSPEKTORAT, PERWADAG)
- Auto-generated usernames based on nama only
- Comprehensive filtering and search capabilities
- Dedicated perwadag search endpoint with pagination
- Profile self-management
- Password management with default password system
- User statistics and analytics
- Removed unnecessary fields (tempat_lahir, tanggal_lahir, pangkat, age calculations)

### Request/Response Schemas:

#### **UserCreate**
```json
{
  "nama": "string (1-200 chars)",
  "jabatan": "string (1-200 chars)",
  "email": "string? (valid email)",
  "is_active": "bool (default: true)",
  "role": "enum (ADMIN/INSPEKTORAT/PERWADAG)",
  "inspektorat": "string? (required for PERWADAG roles)"
}
```

#### **UserUpdate**
```json
{
  "nama": "string? (1-200 chars)",
  "jabatan": "string? (1-200 chars)",
  "email": "string? (valid email)",
  "is_active": "bool?",
  "role": "enum? (ADMIN/INSPEKTORAT/PERWADAG)",
  "inspektorat": "string? (max 100 chars)"
}
```

#### **UserChangePassword**
```json
{
  "current_password": "string",
  "new_password": "string (min 6 chars)"
}
```

#### **UserResponse**
```json
{
  "id": "string",
  "nama": "string",
  "username": "string",
  "jabatan": "string",
  "email": "string?",
  "is_active": "bool",
  "role": "enum",
  "inspektorat": "string?",
  "display_name": "string",
  "has_email": "bool",
  "last_login": "datetime?",
  "role_display": "string",
  "created_at": "datetime",
  "updated_at": "datetime?"
}
```

#### **UserListResponse**
```json
{
  "items": ["UserResponse"],
  "total": "int",
  "page": "int",
  "size": "int",
  "pages": "int"
}
```

#### **UserSummary**
```json
{
  "id": "string",
  "nama": "string",
  "username": "string",
  "jabatan": "string",
  "role": "enum",
  "role_display": "string",
  "inspektorat": "string?",
  "has_email": "bool",
  "is_active": "bool"
}
```

#### **UsernameGenerationPreview**
```json
{
  "nama": "string",
  "role": "enum (ADMIN/INSPEKTORAT/PERWADAG)"
}
```

#### **UsernameGenerationResponse**
```json
{
  "generated_username": "string",
  "is_available": "bool",
  "existing_username": "string?",
  "format_explanation": "string"
}
```

#### **PerwadagSummary**
```json
{
  "id": "string",
  "nama": "string",
  "inspektorat": "string",
  "is_active": "bool"
}
```

#### **PerwadagListResponse**
```json
{
  "items": ["PerwadagSummary"],
  "total": "int",
  "page": "int",
  "size": "int",
  "pages": "int"
}
```

#### **UserFilterParams** (Query Parameters)
- **page**: Page number (default: 1)
- **size**: Items per page (default: 20, max: 100)
- **search**: Search in nama, username, jabatan, email, inspektorat
- **role**: Filter by role (ADMIN/INSPEKTORAT/PERWADAG)
- **inspektorat**: Filter by inspektorat
- **jabatan**: Filter by jabatan
- **has_email**: Filter by email status (true/false)
- **is_active**: Filter by active status (true/false)

#### **PerwadagSearchParams** (Query Parameters)
- **search**: Search term for nama perwadag or inspektorat
- **inspektorat**: Filter by specific inspektorat
- **is_active**: Filter by active status (default: true)
- **page**: Page number (default: 1)
- **size**: Items per page (default: 50, max: 100)

### Access Control Rules:
- **Personal Profile** (`/me`): All authenticated users can view/update their own profile
- **View User by ID**: Users can view their own profile; Admin/Inspektorat can view any user
- **User Management**: Admin-only for create, update, activate, deactivate, delete, reset password
- **User Listing**: Admin and Inspektorat can list users
- **Perwadag Search**: All authenticated users can search perwadag users
- **Statistics**: Admin-only

### Username Generation Rules:
- **Admin/Inspektorat**: Simplified format based on nama only
- **Perwadag**: Extracted from organization name (e.g., "ITPC Lagos" → "itpc_lagos")

### Default Password:
All users are created with default password: `@Kemendag123`

---

## 5. Surat Tugas Endpoints
**Base Path**: `/surat-tugas`

| Method | Route | Request Schema | Response Schema | Auth Required | Description |
|--------|-------|---------------|----------------|---------------|-------------|
| POST | `/` | `SuratTugasCreate` + File | `SuratTugasCreateResponse` | Admin/Inspektorat | Create surat tugas with auto-generate |
| GET | `/` | `SuratTugasFilterParams` | `SuratTugasListResponse` | JWT + Role Scope | Get all surat tugas with filters |
| GET | `/{surat_tugas_id}` | None | `SuratTugasResponse` | JWT + Role Scope | Get surat tugas by ID |
| PUT | `/{surat_tugas_id}` | `SuratTugasUpdate` | `SuratTugasResponse` | Admin/Inspektorat | Update surat tugas |
| POST | `/{surat_tugas_id}/upload-file` | `UploadFile` | `SuccessResponse` | Admin/Inspektorat | Upload surat tugas file |
| DELETE | `/{surat_tugas_id}` | None | `SuccessResponse` | Admin/Inspektorat | Delete surat tugas with cascade |
| GET | `/perwadag/list` | None | Dict | Admin/Inspektorat | Get available perwadag users |
| GET | `/dashboard/summary` | None | Dict | JWT + Role Scope | Get dashboard summary |

### Key Features:
- Auto-generates 6 related evaluation records
- Role-based data filtering
- Cascade delete functionality
- Dashboard integration

### Request/Response Schemas:

#### **SuratTugasCreate**
```json
{
  "user_perwadag_id": "string",
  "tanggal_evaluasi_mulai": "date",
  "tanggal_evaluasi_selesai": "date", 
  "no_surat": "string (1-100 chars)",
  "nama_pengedali_mutu": "string (1-200 chars)",
  "nama_pengendali_teknis": "string (1-200 chars)",
  "nama_ketua_tim": "string (1-200 chars)"
}
```

#### **SuratTugasUpdate**
```json
{
  "tanggal_evaluasi_mulai": "date?",
  "tanggal_evaluasi_selesai": "date?",
  "no_surat": "string? (1-100 chars)",
  "nama_pengedali_mutu": "string? (1-200 chars)",
  "nama_pengendali_teknis": "string? (1-200 chars)",
  "nama_ketua_tim": "string? (1-200 chars)"
}
```

#### **SuratTugasResponse**
```json
{
  "id": "string",
  "user_perwadag_id": "string",
  "nama_perwadag": "string",
  "inspektorat": "string",
  "tanggal_evaluasi_mulai": "date",
  "tanggal_evaluasi_selesai": "date",
  "no_surat": "string",
  "nama_pengedali_mutu": "string",
  "nama_pengendali_teknis": "string", 
  "nama_ketua_tim": "string",
  "file_surat_tugas": "string",
  "tahun_evaluasi": "int?",
  "durasi_evaluasi": "int?",
  "is_evaluation_active": "bool?",
  "evaluation_status": "string?",
  "progress": {
    "surat_pemberitahuan_completed": "bool",
    "entry_meeting_completed": "bool",
    "konfirmasi_meeting_completed": "bool", 
    "exit_meeting_completed": "bool",
    "matriks_completed": "bool",
    "laporan_completed": "bool",
    "kuisioner_completed": "bool",
    "overall_percentage": "int (0-100)"
  },
  "perwadag_info": {
    "id": "string",
    "nama": "string",
    "inspektorat": "string"
  },
  "file_surat_tugas_url": "string",
  "created_at": "datetime",
  "updated_at": "datetime?",
  "created_by": "string?",
  "updated_by": "string?"
}
```

#### **SuratTugasListResponse**
```json
{
  "items": ["SuratTugasResponse"],
  "total": "int",
  "page": "int", 
  "size": "int",
  "pages": "int"
}
```

#### **SuratTugasCreateResponse**
```json
{
  "success": "bool",
  "message": "string",
  "data": "SuratTugasResponse",
  "surat_tugas": "SuratTugasResponse",
  "auto_generated_records": {
    "surat_pemberitahuan_id": "string",
    "entry_meeting_id": "string",
    "konfirmasi_meeting_id": "string",
    "exit_meeting_id": "string",
    "matriks_id": "string",
    "laporan_hasil_id": "string",
    "kuisioner_id": "string"
  }
}
```

---

## 6. Format Kuisioner Endpoints
**Base Path**: `/format-kuisioner`

| Method | Route | Request Schema | Response Schema | Auth Required | Description |
|--------|-------|---------------|----------------|---------------|-------------|
| POST | `/` | Form + `UploadFile` | `FormatKuisionerResponse` | Admin | Create format kuisioner template |
| GET | `/` | `FormatKuisionerFilterParams` | `FormatKuisionerListResponse` | JWT | Get all format kuisioner |
| GET | `/tahun/{tahun}` | None | Dict | JWT | Get format kuisioner by year |
| GET | `/{format_kuisioner_id}` | None | `FormatKuisionerResponse` | JWT | Get format kuisioner by ID |
| PUT | `/{format_kuisioner_id}` | `FormatKuisionerUpdate` | `FormatKuisionerResponse` | Admin | Update format kuisioner |
| POST | `/{format_kuisioner_id}/upload-file` | `UploadFile` | `FormatKuisionerFileUploadResponse` | Admin | Upload template file |
| DELETE | `/{format_kuisioner_id}` | None | `SuccessResponse` | Admin | Delete format kuisioner |
| GET | `/download/{format_kuisioner_id}` | None | `RedirectResponse` | JWT | Download template file |
| GET | `/admin/statistics` | None | Dict | Admin | Get template statistics |

### Key Features:
- Master template management
- Year-based organization
- File upload/download
- Admin-only management

### Request/Response Schemas:

#### **FormatKuisionerCreate**
```json
{
  "nama_template": "string (1-200 chars)",
  "deskripsi": "string?",
  "tahun": "int (2020-2030)"
}
```

#### **FormatKuisionerUpdate**
```json
{
  "nama_template": "string? (1-200 chars)",
  "deskripsi": "string?",
  "tahun": "int? (2020-2030)"
}
```

#### **FormatKuisionerResponse**
```json
{
  "id": "string",
  "nama_template": "string",
  "deskripsi": "string?",
  "tahun": "int",
  "link_template": "string",
  "file_urls": {
    "file_url": "string",
    "download_url": "string", 
    "view_url": "string"
  },
  "file_metadata": {
    "filename": "string",
    "original_filename": "string?",
    "size": "int",
    "size_mb": "float",
    "content_type": "string",
    "extension": "string",
    "uploaded_at": "datetime",
    "uploaded_by": "string?",
    "is_viewable": "bool"
  },
  "display_name": "string",
  "has_file": "bool",
  "is_downloadable": "bool",
  "is_current_year": "bool",
  "usage_count": "int",
  "last_used": "datetime?",
  "created_at": "datetime",
  "updated_at": "datetime?",
  "created_by": "string?",
  "updated_by": "string?"
}
```

#### **FormatKuisionerListResponse**
```json
{
  "items": ["FormatKuisionerResponse"],
  "total": "int",
  "page": "int",
  "size": "int", 
  "pages": "int",
  "statistics": {
    "total_records": "int",
    "completed_records": "int",
    "with_files": "int",
    "without_files": "int",
    "completion_rate": "float (0-100)",
    "last_updated": "datetime"
  }
}
```

#### **FormatKuisionerFileUploadResponse**
```json
{
  "success": "bool",
  "message": "string",
  "data": "any",
  "format_kuisioner_id": "string",
  "file_path": "string",
  "file_url": "string"
}
```

---

## 7. Evaluation Module Endpoints

### 7.1 Kuisioner Endpoints
**Base Path**: `/kuisioner`

| Method | Route | Request Schema | Response Schema | Auth Required | Description |
|--------|-------|---------------|----------------|---------------|-------------|
| GET | `/` | `KuisionerFilterParams` | `KuisionerListResponse` | JWT + Role Scope | Get all kuisioner with filters |
| GET | `/{kuisioner_id}` | None | `KuisionerResponse` | JWT + Role Scope | Get kuisioner by ID |
| GET | `/surat-tugas/{surat_tugas_id}` | None | `KuisionerResponse` | JWT + Role Scope | Get kuisioner by surat tugas ID |
| PUT | `/{kuisioner_id}` | `KuisionerUpdate` | `KuisionerResponse` | Role-specific | Update kuisioner |
| POST | `/{kuisioner_id}/upload-file` | `UploadFile` | `KuisionerFileUploadResponse` | Role-specific | Upload file |
| GET | `/{kuisioner_id}/download` | None | `FileResponse` | JWT + Role Scope | Download file |
| GET | `/{kuisioner_id}/view` | None | `FileResponse` | JWT + Role Scope | View file in browser |

#### **Kuisioner Schemas:**

**KuisionerCreate**
```json
{
  "surat_tugas_id": "string"
}
```

**KuisionerUpdate**
```json
{
  "tanggal_kuisioner": "date?"
}
```

**KuisionerResponse**
```json
{
  "id": "string",
  "surat_tugas_id": "string", 
  "tanggal_kuisioner": "date?",
  "file_dokumen": "string?",
  "file_urls": {
    "file_url": "string",
    "download_url": "string",
    "view_url": "string"
  },
  "file_metadata": {
    "filename": "string",
    "original_filename": "string?",
    "size": "int",
    "size_mb": "float",
    "content_type": "string",
    "extension": "string",
    "uploaded_at": "datetime",
    "uploaded_by": "string?",
    "is_viewable": "bool"
  },
  "is_completed": "bool",
  "has_file": "bool",
  "completion_percentage": "int (0-100)",
  "surat_tugas_info": {
    "id": "string",
    "no_surat": "string",
    "nama_perwadag": "string",
    "inspektorat": "string",
    "tanggal_evaluasi_mulai": "date",
    "tanggal_evaluasi_selesai": "date",
    "tahun_evaluasi": "int",
    "durasi_evaluasi": "int",
    "evaluation_status": "string",
    "is_evaluation_active": "bool"
  },
  "nama_perwadag": "string",
  "inspektorat": "string",
  "tanggal_evaluasi_mulai": "date",
  "tanggal_evaluasi_selesai": "date",
  "tahun_evaluasi": "int",
  "evaluation_status": "string",
  "created_at": "datetime",
  "updated_at": "datetime?",
  "created_by": "string?",
  "updated_by": "string?"
}
```

**KuisionerListResponse**
```json
{
  "items": ["KuisionerResponse"],
  "total": "int",
  "page": "int",
  "size": "int",
  "pages": "int",
  "statistics": {
    "total_records": "int",
    "completed_records": "int",
    "with_files": "int",
    "without_files": "int",
    "completion_rate": "float (0-100)",
    "last_updated": "datetime"
  }
}
```

**KuisionerFileUploadResponse**
```json
{
  "success": "bool",
  "message": "string",
  "data": "any",
  "kuisioner_id": "string",
  "file_path": "string",
  "file_url": "string"
}
```

### 7.2 Laporan Hasil Endpoints
**Base Path**: `/laporan-hasil`

| Method | Route | Request Schema | Response Schema | Auth Required | Description |
|--------|-------|---------------|----------------|---------------|-------------|
| GET | `/` | `LaporanHasilFilterParams` | `LaporanHasilListResponse` | JWT + Role Scope | Get all laporan hasil with filters |
| GET | `/{laporan_hasil_id}` | None | `LaporanHasilResponse` | JWT + Role Scope | Get laporan hasil by ID |
| GET | `/surat-tugas/{surat_tugas_id}` | None | `LaporanHasilResponse` | JWT + Role Scope | Get laporan hasil by surat tugas ID |
| PUT | `/{laporan_hasil_id}` | `LaporanHasilUpdate` | `LaporanHasilResponse` | Role-specific | Update laporan hasil |
| POST | `/{laporan_hasil_id}/upload-file` | `UploadFile` | `LaporanHasilFileUploadResponse` | Role-specific | Upload file |
| GET | `/{laporan_hasil_id}/download` | None | `FileResponse` | JWT + Role Scope | Download file |
| GET | `/{laporan_hasil_id}/view` | None | `FileResponse` | JWT + Role Scope | View file in browser |

#### **Laporan Hasil Schemas:**

**LaporanHasilCreate**
```json
{
  "surat_tugas_id": "string"
}
```

**LaporanHasilUpdate**
```json
{
  "nomor_laporan": "string? (max 100 chars)",
  "tanggal_laporan": "date?"
}
```

**LaporanHasilResponse**
```json
{
  "id": "string",
  "surat_tugas_id": "string",
  "nomor_laporan": "string?",
  "tanggal_laporan": "date?",
  "file_dokumen": "string?",
  "file_urls": {
    "file_url": "string",
    "download_url": "string",
    "view_url": "string"
  },
  "file_metadata": {
    "filename": "string",
    "original_filename": "string?",
    "size": "int",
    "size_mb": "float",
    "content_type": "string",
    "extension": "string",
    "uploaded_at": "datetime",
    "uploaded_by": "string?",
    "is_viewable": "bool"
  },
  "is_completed": "bool",
  "has_file": "bool",
  "has_nomor": "bool",
  "completion_percentage": "int (0-100)",
  "surat_tugas_info": {
    "id": "string",
    "no_surat": "string",
    "nama_perwadag": "string",
    "inspektorat": "string",
    "tanggal_evaluasi_mulai": "date",
    "tanggal_evaluasi_selesai": "date",
    "tahun_evaluasi": "int",
    "durasi_evaluasi": "int",
    "evaluation_status": "string",
    "is_evaluation_active": "bool"
  },
  "nama_perwadag": "string",
  "inspektorat": "string",
  "tanggal_evaluasi_mulai": "date",
  "tanggal_evaluasi_selesai": "date",
  "tahun_evaluasi": "int",
  "evaluation_status": "string",
  "created_at": "datetime",
  "updated_at": "datetime?",
  "created_by": "string?",
  "updated_by": "string?"
}
```

**LaporanHasilListResponse**
```json
{
  "items": ["LaporanHasilResponse"],
  "total": "int",
  "page": "int",
  "size": "int",
  "pages": "int",
  "statistics": {
    "total_records": "int",
    "completed_records": "int",
    "with_files": "int",
    "without_files": "int",
    "completion_rate": "float (0-100)",
    "last_updated": "datetime"
  }
}
```

**LaporanHasilFileUploadResponse**
```json
{
  "success": "bool",
  "message": "string",
  "data": "any",
  "laporan_hasil_id": "string",
  "file_path": "string",
  "file_url": "string"
}
```

### 7.3 Matriks Endpoints
**Base Path**: `/matriks`

| Method | Route | Request Schema | Response Schema | Auth Required | Description |
|--------|-------|---------------|----------------|---------------|-------------|
| GET | `/` | `MatriksFilterParams` | `MatriksListResponse` | JWT + Role Scope | Get all matriks with filters |
| GET | `/{matriks_id}` | None | `MatriksResponse` | JWT + Role Scope | Get matriks by ID |
| GET | `/surat-tugas/{surat_tugas_id}` | None | `MatriksResponse` | JWT + Role Scope | Get matriks by surat tugas ID |
| PUT | `/{matriks_id}` | `MatriksUpdate` | `MatriksResponse` | Role-specific | Update matriks |
| POST | `/{matriks_id}/upload-file` | `UploadFile` | `MatriksFileUploadResponse` | Role-specific | Upload file |
| GET | `/{matriks_id}/download` | None | `FileResponse` | JWT + Role Scope | Download file |
| GET | `/{matriks_id}/view` | None | `FileResponse` | JWT + Role Scope | View file in browser |

#### **Matriks Schemas:**

**MatriksCreate**
```json
{
  "surat_tugas_id": "string"
}
```

**MatriksUpdate**
```json
{
  "temuan_rekomendasi": {
    "items": [
      {
        "temuan": "string (tidak boleh kosong)",
        "rekomendasi": "string (tidak boleh kosong)"
      }
    ]
  }
}
```

**MatriksResponse**
```json
{
  "id": "string",
  "surat_tugas_id": "string",
  "nomor_matriks": "string?",
  "file_dokumen": "string?",
  "temuan_rekomendasi": {
    "items": [
      {
        "temuan": "string",
        "rekomendasi": "string"
      }
    ],
    "total_items": "int",
    "has_items": "bool"
  },
  "file_urls": {
    "file_url": "string",
    "download_url": "string",
    "view_url": "string"
  },
  "file_metadata": {
    "filename": "string",
    "original_filename": "string?",
    "size": "int",
    "size_mb": "float",
    "content_type": "string",
    "extension": "string",
    "uploaded_at": "datetime",
    "uploaded_by": "string?",
    "is_viewable": "bool"
  },
  "is_completed": "bool",
  "has_file": "bool",
  "has_nomor": "bool",
  "has_temuan_rekomendasi": "bool",
  "completion_percentage": "int (0-100)",
  "surat_tugas_info": {
    "id": "string",
    "no_surat": "string",
    "nama_perwadag": "string",
    "inspektorat": "string",
    "tanggal_evaluasi_mulai": "date",
    "tanggal_evaluasi_selesai": "date",
    "tahun_evaluasi": "int",
    "durasi_evaluasi": "int",
    "evaluation_status": "string",
    "is_evaluation_active": "bool"
  },
  "nama_perwadag": "string",
  "inspektorat": "string",
  "tanggal_evaluasi_mulai": "date",
  "tanggal_evaluasi_selesai": "date",
  "tahun_evaluasi": "int",
  "evaluation_status": "string",
  "created_at": "datetime",
  "updated_at": "datetime?",
  "created_by": "string?",
  "updated_by": "string?"
}
```

**MatriksListResponse**
```json
{
  "items": ["MatriksResponse"],
  "total": "int",
  "page": "int",
  "size": "int",
  "pages": "int",
  "statistics": {
    "total_records": "int",
    "completed_records": "int",
    "with_files": "int",
    "without_files": "int",
    "completion_rate": "float (0-100)",
    "last_updated": "datetime"
  }
}
```

**MatriksFileUploadResponse**
```json
{
  "success": "bool",
  "message": "string",
  "data": "any",
  "matriks_id": "string",
  "file_path": "string",
  "file_url": "string"
}
```

### 7.4 Surat Pemberitahuan Endpoints
**Base Path**: `/surat-pemberitahuan`

| Method | Route | Request Schema | Response Schema | Auth Required | Description |
|--------|-------|---------------|----------------|---------------|-------------|
| GET | `/` | `SuratPemberitahuanFilterParams` | `SuratPemberitahuanListResponse` | JWT + Role Scope | Get all surat pemberitahuan with filters |
| GET | `/{surat_pemberitahuan_id}` | None | `SuratPemberitahuanResponse` | JWT + Role Scope | Get surat pemberitahuan by ID |
| GET | `/surat-tugas/{surat_tugas_id}` | None | `SuratPemberitahuanResponse` | JWT + Role Scope | Get surat pemberitahuan by surat tugas ID |
| PUT | `/{surat_pemberitahuan_id}` | `SuratPemberitahuanUpdate` | `SuratPemberitahuanResponse` | Role-specific | Update surat pemberitahuan |
| POST | `/{surat_pemberitahuan_id}/upload-file` | `UploadFile` | `SuratPemberitahuanFileUploadResponse` | Role-specific | Upload file |
| GET | `/{surat_pemberitahuan_id}/download` | None | `FileResponse` | JWT + Role Scope | Download file |
| GET | `/{surat_pemberitahuan_id}/view` | None | `FileResponse` | JWT + Role Scope | View file in browser |

#### **Surat Pemberitahuan Schemas:**

**SuratPemberitahuanCreate**
```json
{
  "surat_tugas_id": "string"
}
```

**SuratPemberitahuanUpdate**
```json
{
  "tanggal_surat_pemberitahuan": "date?"
}
```

**SuratPemberitahuanResponse**
```json
{
  "id": "string",
  "surat_tugas_id": "string",
  "tanggal_surat_pemberitahuan": "date?",
  "file_dokumen": "string?",
  "file_urls": {
    "file_url": "string",
    "download_url": "string",
    "view_url": "string"
  },
  "file_metadata": {
    "filename": "string",
    "original_filename": "string?",
    "size": "int",
    "size_mb": "float",
    "content_type": "string",
    "extension": "string",
    "uploaded_at": "datetime",
    "uploaded_by": "string?",
    "is_viewable": "bool"
  },
  "is_completed": "bool",
  "has_file": "bool",
  "has_date": "bool",
  "completion_percentage": "int (0-100)",
  "surat_tugas_info": {
    "id": "string",
    "no_surat": "string",
    "nama_perwadag": "string",
    "inspektorat": "string",
    "tanggal_evaluasi_mulai": "date",
    "tanggal_evaluasi_selesai": "date",
    "tahun_evaluasi": "int",
    "durasi_evaluasi": "int",
    "evaluation_status": "string",
    "is_evaluation_active": "bool"
  },
  "nama_perwadag": "string",
  "inspektorat": "string",
  "tanggal_evaluasi_mulai": "date",
  "tanggal_evaluasi_selesai": "date",
  "tahun_evaluasi": "int",
  "evaluation_status": "string",
  "created_at": "datetime",
  "updated_at": "datetime?",
  "created_by": "string?",
  "updated_by": "string?"
}
```

**SuratPemberitahuanListResponse**
```json
{
  "items": ["SuratPemberitahuanResponse"],
  "total": "int",
  "page": "int",
  "size": "int",
  "pages": "int",
  "statistics": {
    "total_records": "int",
    "completed_records": "int",
    "with_files": "int",
    "without_files": "int",
    "completion_rate": "float (0-100)",
    "last_updated": "datetime"
  }
}
```

**SuratPemberitahuanFileUploadResponse**
```json
{
  "success": "bool",
  "message": "string",
  "data": "any",
  "surat_pemberitahuan_id": "string",
  "file_path": "string",
  "file_url": "string"
}
```

---

## 8. Periode Evaluasi Endpoints
**Base Path**: `/periode-evaluasi`

| Method | Route | Request Schema | Response Schema | Auth Required | Description |
|--------|-------|---------------|----------------|---------------|-------------|
| POST | `/` | `PeriodeEvaluasiCreate` | `PeriodeEvaluasiCreateResponse` | Admin | Create periode evaluasi with auto bulk generate |
| GET | `/` | `PeriodeEvaluasiFilterParams` | `PeriodeEvaluasiListResponse` | Admin/Inspektorat | Get all periode evaluasi with filters |
| GET | `/{periode_id}` | None | `PeriodeEvaluasiResponse` | Admin/Inspektorat | Get periode evaluasi by ID |
| PUT | `/{periode_id}` | `PeriodeEvaluasiUpdate` | `PeriodeEvaluasiResponse` | Admin | Update periode evaluasi |
| DELETE | `/{periode_id}` | None | `SuccessResponse` | Admin | Delete periode evaluasi with cascade |
| GET | `/check/tahun-availability` | Query: `tahun` | Dict | Admin | Check tahun availability |
| GET | `/statistics/overview` | None | Dict | Admin | Get comprehensive statistics |

### Key Features:
- **Auto bulk generate**: Automatically creates penilaian risiko for all active perwadag
- **Tahun pembanding**: Auto-generates comparison years (tahun-2, tahun-1)
- **Cascade delete**: Deletes all related penilaian risiko when periode is deleted
- **Lock/unlock**: Controls editing permissions for the periode

### Request/Response Schemas:

#### **PeriodeEvaluasiCreate**
```json
{
  "tahun": "int (2020-2050)",
  "status": "enum (aktif/tutup, default: aktif)"
}
```

#### **PeriodeEvaluasiUpdate**
```json
{
  "is_locked": "bool?",
  "status": "enum? (aktif/tutup)"
}
```

#### **PeriodeEvaluasiResponse**
```json
{
  "id": "string",
  "tahun": "int",
  "is_locked": "bool",
  "status": "enum",
  "is_editable": "bool",
  "status_display": "string",
  "lock_status_display": "string",
  "tahun_pembanding_1": "int",
  "tahun_pembanding_2": "int",
  "total_penilaian": "int",
  "penilaian_completed": "int",
  "completion_rate": "float",
  "created_at": "datetime",
  "updated_at": "datetime?",
  "created_by": "string?",
  "updated_by": "string?"
}
```

#### **PeriodeEvaluasiCreateResponse**
```json
{
  "success": "bool",
  "message": "string",
  "data": "any",
  "periode_evaluasi": "PeriodeEvaluasiResponse",
  "bulk_generation_summary": {
    "total_perwadag": "int",
    "generated_penilaian": "int",
    "failed_generation": "int",
    "errors": ["string"]
  }
}
```

#### **PeriodeEvaluasiFilterParams** (Query Parameters)
- **page**: Page number (default: 1)
- **size**: Items per page (default: 10)
- **search**: Search by tahun
- **status**: Filter by status (aktif/tutup)
- **is_locked**: Filter by lock status
- **tahun_from**: Start year filter
- **tahun_to**: End year filter
- **include_statistics**: Include statistics in response

### Business Rules:
- **Tahun uniqueness**: Each tahun can only have one periode
- **Auto-generated years**: tahun_pembanding_1 = tahun-2, tahun_pembanding_2 = tahun-1
- **Cascade operations**: Creating periode auto-generates penilaian risiko for all active perwadag
- **Lock mechanism**: Locked periode prevents editing of related penilaian risiko

---

## 9. Penilaian Risiko Endpoints
**Base Path**: `/penilaian-risiko`

| Method | Route | Request Schema | Response Schema | Auth Required | Description |
|--------|-------|---------------|----------------|---------------|-------------|
| GET | `/` | `PenilaianRisikoFilterParams` | `PenilaianRisikoListResponse` | Admin/Inspektorat | Get all penilaian risiko with filters |
| GET | `/{penilaian_id}` | None | `PenilaianRisikoResponse` | Admin/Inspektorat | Get penilaian risiko by ID |
| PUT | `/{penilaian_id}` | `PenilaianRisikoUpdate` | `PenilaianRisikoResponse` | Admin/Inspektorat | Update penilaian risiko with auto-calculate |
| GET | `/periode/{periode_id}/summary` | None | Dict | Admin/Inspektorat | Get periode summary statistics |

### Key Features:
- **Auto-calculate**: Automatically calculates total_nilai_risiko and profil_risiko when data is complete
- **Role-based filtering**: Admin sees all, Inspektorat sees only their jurisdiction
- **8 criteria evaluation**: Comprehensive risk assessment with weighted scoring
- **Risk profiling**: Automatic risk categorization (Rendah/Sedang/Tinggi)

### Request/Response Schemas:

#### **PenilaianRisikoUpdate**
```json
{
  "kriteria_data": {
    "tren_capaian": {
      "tahun_pembanding_1": "int",
      "capaian_tahun_1": "float?",
      "tahun_pembanding_2": "int", 
      "capaian_tahun_2": "float?",
      "tren": "float?",
      "pilihan": "string?",
      "nilai": "int?"
    },
    "realisasi_anggaran": {
      "tahun_pembanding": "int",
      "realisasi": "float?",
      "pagu": "float?",
      "persentase": "float?",
      "pilihan": "string?",
      "nilai": "int?"
    },
    "tren_ekspor": {
      "tahun_pembanding": "int",
      "deskripsi": "float?",
      "pilihan": "string?",
      "nilai": "int?"
    },
    "audit_itjen": {
      "tahun_pembanding": "int",
      "deskripsi": "string?",
      "pilihan": "string?",
      "nilai": "int?"
    },
    "perjanjian_perdagangan": {
      "tahun_pembanding": "int",
      "deskripsi": "string?",
      "pilihan": "string?",
      "nilai": "int?"
    },
    "peringkat_ekspor": {
      "tahun_pembanding": "int",
      "deskripsi": "int?",
      "pilihan": "string?",
      "nilai": "int?"
    },
    "persentase_ik": {
      "tahun_pembanding": "int",
      "ik_tidak_tercapai": "int?",
      "total_ik": "int?",
      "persentase": "float?",
      "pilihan": "string?",
      "nilai": "int?"
    },
    "realisasi_tei": {
      "tahun_pembanding": "int",
      "nilai_realisasi": "float?",
      "nilai_potensi": "float?",
      "deskripsi": "float?",
      "pilihan": "string?",
      "nilai": "int?"
    }
  },
  "catatan": "string? (max 1000 chars)",
  "auto_calculate": "bool (default: true)"
}
```

#### **PenilaianRisikoResponse**
```json
{
  "id": "string",
  "user_perwadag_id": "string",
  "periode_id": "string",
  "tahun": "int",
  "inspektorat": "string",
  "total_nilai_risiko": "decimal?",
  "skor_rata_rata": "decimal?",
  "profil_risiko_auditan": "string?",
  "catatan": "string?",
  "kriteria_data": {
    "tren_capaian": "TrenCapaianData",
    "realisasi_anggaran": "RealisasiAnggaranData",
    "tren_ekspor": "TrenEksporData",
    "audit_itjen": "AuditItjenData",
    "perjanjian_perdagangan": "PerjanjianPerdaganganData",
    "peringkat_ekspor": "PeringkatEksporData",
    "persentase_ik": "PersentaseIkData",
    "realisasi_tei": "RealisasiTeiData"
  },
  "is_calculation_complete": "bool",
  "has_calculation_result": "bool",
  "completion_percentage": "int (0-100)",
  "profil_risiko_color": "string",
  "perwadag_info": {
    "id": "string",
    "nama": "string",
    "inspektorat": "string",
    "email": "string?"
  },
  "periode_info": {
    "id": "string",
    "tahun": "int",
    "status": "string",
    "is_locked": "bool",
    "is_editable": "bool"
  },
  "nama_perwadag": "string",
  "periode_tahun": "int",
  "periode_status": "string",
  "calculation_performed": "bool",
  "calculation_details": {
    "formula_used": "string",
    "individual_scores": "dict",
    "weighted_total": "decimal",
    "risk_category": "string"
  },
  "created_at": "datetime",
  "updated_at": "datetime?",
  "created_by": "string?",
  "updated_by": "string?"
}
```

#### **PenilaianRisikoFilterParams** (Query Parameters)
- **page**: Page number (default: 1)
- **size**: Items per page (default: 10)
- **search**: Search in nama perwadag, inspektorat
- **periode_id**: Filter by periode
- **user_perwadag_id**: Filter by perwadag
- **inspektorat**: Filter by inspektorat
- **tahun**: Filter by tahun
- **is_complete**: Filter complete data (true/false)
- **sort_by**: Sort order (skor_tertinggi, skor_terendah, nama, created_at)

### Calculation Formula:
```
total_nilai_risiko = (
    (nilai1 * 15) + (nilai2 * 10) + (nilai3 * 15) + (nilai4 * 25) + 
    (nilai5 * 5) + (nilai6 * 10) + (nilai7 * 10) + (nilai8 * 10)
) / 5

skor_rata_rata = (nilai1 + nilai2 + ... + nilai8) / 8

profil_risiko_auditan:
- skor_rata_rata <= 2.0 → "Rendah"
- skor_rata_rata <= 3.5 → "Sedang"
- skor_rata_rata > 3.5 → "Tinggi"
```

### Access Control:
- **Admin**: Full access to all penilaian risiko
- **Inspektorat**: Access only to penilaian risiko in their jurisdiction
- **Perwadag**: No direct access (managed through other endpoints)

---

## 10. Meeting Endpoints
**Base Path**: `/meeting`

| Method | Route | Request Schema | Response Schema | Auth Required | Description |
|--------|-------|---------------|----------------|---------------|-------------|
| GET | `/` | `MeetingFilterParams` | `MeetingListResponse` | JWT + Role Scope | Get all meetings |
| GET | `/{meeting_id}` | None | `MeetingResponse` | JWT + Role Scope | Get meeting by ID |
| GET | `/surat-tugas/{surat_tugas_id}/type/{meeting_type}` | None | `MeetingResponse` | JWT + Role Scope | Get meeting by surat tugas and type |
| GET | `/surat-tugas/{surat_tugas_id}` | None | `List[MeetingResponse]` | JWT + Role Scope | Get all meetings for surat tugas |
| PUT | `/{meeting_id}` | `MeetingUpdate` | `MeetingResponse` | Admin/Inspektorat | Update meeting |
| POST | `/{meeting_id}/upload-files` | `List[UploadFile]` | `MeetingFileUploadResponse` | Admin/Inspektorat | Upload multiple files |
| DELETE | `/{meeting_id}/files/{filename}` | None | `MeetingFileDeleteResponse` | Admin/Inspektorat | Delete specific file |
| GET | `/{meeting_id}/files/{filename}/download` | None | `FileResponse` | JWT + Role Scope | Download specific file |
| GET | `/{meeting_id}/files/{filename}/view` | None | `FileResponse` | JWT + Role Scope | View specific file |
| GET | `/{meeting_id}/files/download-all` | None | `FileResponse` | JWT + Role Scope | Download all files as ZIP |

### Key Features:
- Three meeting types: ENTRY, KONFIRMASI, EXIT
- Multiple file support per meeting
- ZIP download for all files
- Meeting-specific file management

### Request/Response Schemas:

#### **MeetingCreate**
```json
{
  "surat_tugas_id": "string",
  "meeting_type": "enum (ENTRY/KONFIRMASI/EXIT)"
}
```

#### **MeetingUpdate**
```json
{
  "tanggal_meeting": "date?",
  "link_zoom": "string? (max 500 chars, must be valid URL)",
  "link_daftar_hadir": "string? (max 500 chars, must be valid URL)"
}
```

#### **MeetingFileUploadRequest**
```json
{
  "replace_existing": "bool (default: false)"
}
```

#### **MeetingResponse**
```json
{
  "id": "string",
  "surat_tugas_id": "string",
  "meeting_type": "enum",
  "tanggal_meeting": "date?",
  "link_zoom": "string?",
  "link_daftar_hadir": "string?",
  "files_info": {
    "files": [
      {
        "filename": "string",
        "original_filename": "string",
        "path": "string",
        "size": "int",
        "size_mb": "float",
        "content_type": "string",
        "uploaded_at": "datetime",
        "uploaded_by": "string?",
        "download_url": "string",
        "view_url": "string?",
        "is_viewable": "bool"
      }
    ],
    "total_files": "int",
    "total_size": "int",
    "total_size_mb": "float",
    "download_all_url": "string"
  },
  "is_completed": "bool",
  "has_files": "bool",
  "has_date": "bool",
  "has_links": "bool",
  "completion_percentage": "int (0-100)",
  "meeting_type_display": "string",
  "meeting_order": "int",
  "surat_tugas_info": {
    "id": "string",
    "no_surat": "string",
    "nama_perwadag": "string",
    "inspektorat": "string",
    "tanggal_evaluasi_mulai": "date",
    "tanggal_evaluasi_selesai": "date",
    "tahun_evaluasi": "int",
    "durasi_evaluasi": "int",
    "evaluation_status": "string",
    "is_evaluation_active": "bool"
  },
  "nama_perwadag": "string",
  "inspektorat": "string",
  "tanggal_evaluasi_mulai": "date",
  "tanggal_evaluasi_selesai": "date",
  "tahun_evaluasi": "int",
  "evaluation_status": "string",
  "created_at": "datetime",
  "updated_at": "datetime?",
  "created_by": "string?",
  "updated_by": "string?"
}
```

#### **MeetingListResponse**
```json
{
  "items": ["MeetingResponse"],
  "total": "int",
  "page": "int",
  "size": "int",
  "pages": "int",
  "statistics": {
    "total_records": "int",
    "completed_records": "int",
    "with_files": "int",
    "without_files": "int",
    "completion_rate": "float (0-100)",
    "last_updated": "datetime"
  }
}
```

#### **MeetingFileUploadResponse**
```json
{
  "success": "bool",
  "message": "string", 
  "data": "any",
  "meeting_id": "string",
  "uploaded_files": [
    {
      "filename": "string",
      "original_filename": "string",
      "path": "string",
      "size": "int",
      "size_mb": "float",
      "content_type": "string",
      "uploaded_at": "string",
      "uploaded_by": "string"
    }
  ],
  "total_files": "int",
  "total_size_mb": "float"
}
```

#### **MeetingFileDeleteResponse**
```json
{
  "success": "bool",
  "message": "string",
  "data": "any", 
  "meeting_id": "string",
  "deleted_file": "string",
  "remaining_files": "int"
}
```

---

## Authentication & Authorization

### Role-based Access Control:
1. **Admin**: Full access to all resources
2. **Inspektorat**: Access to evaluation data in their jurisdiction + surat tugas management
3. **Perwadag**: Access to their own evaluation data only

### Permission Decorators:
- `require_evaluasi_read_access()`: All roles with scope filtering
- `require_evaluasi_write_access()`: Admin + Inspektorat only
- `require_surat_tugas_create_access()`: Admin + Inspektorat only
- `require_format_kuisioner_access()`: Admin only
- `require_auto_generated_edit_access()`: Admin + Inspektorat only
- `admin_required`: Admin only
- `admin_or_inspektorat`: Admin + Inspektorat only

### JWT Token Structure:
```json
{
  "sub": "user_id",
  "nama": "user_name",
  "role": "enum_role",
  "inspektorat": "string_or_null",
  "exp": "expiration_timestamp"
}
```

---

## Common Response Patterns

### Success Response (MessageResponse):
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {...}
}
```

### Error Response:
```json
{
  "detail": "Error message describing what went wrong",
  "error_code": "string?"
}
```

### Paginated List Response:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "size": 10,
  "pages": 10
}
```

### File Response:
- **Content-Type**: Based on file type
- **Content-Disposition**: `attachment; filename="filename.ext"` for downloads
- **Content-Disposition**: `inline; filename="filename.ext"` for views

---

## Common Filter Parameters

Most list endpoints support these query parameters:
- `page`: Page number (default: 1)
- `size`: Items per page (default: 10)
- `search`: Search term for text fields
- `inspektorat`: Filter by inspektorat (for Admin role)
- `user_perwadag_id`: Filter by perwadag user (for Admin/Inspektorat roles)
- `has_file`: Filter by file presence (true/false)
- `is_completed`: Filter by completion status (true/false)
- Date range filters (varies by endpoint)

---

## File Upload Specifications

### Supported File Types:
- Documents: PDF, DOC, DOCX
- Images: JPG, JPEG, PNG, GIF
- Archives: ZIP, RAR

### File Size Limits:
- Single file: 10MB
- Multiple files: 50MB total

### Upload Process:
1. Files are stored using configurable storage backend
2. Metadata is saved in database
3. File access is controlled by user permissions
4. Temporary files are cleaned up automatically

---

## Error Codes

### Common HTTP Status Codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error

### Custom Error Messages:
- Authentication errors return specific messages about token validity
- Permission errors specify which role/access level is required
- Validation errors detail which fields are invalid
- File errors specify size/type restrictions

---

## Rate Limiting

Rate limiting is implemented on sensitive endpoints:
- Login attempts: 5 per minute per IP
- Password reset: 3 per hour per IP
- File uploads: 20 per minute per user
- API calls: 1000 per hour per user

---

## Development Notes

### Environment Variables:
- `DATABASE_URL`: Database connection string
- `JWT_SECRET`: Secret key for JWT tokens
- `REDIS_URL`: Redis connection for caching
- `STORAGE_TYPE`: Storage backend (local/s3/gcs)
- `EMAIL_*`: Email configuration for notifications

### Database:
- PostgreSQL with SQLAlchemy ORM
- Alembic for database migrations
- UUID primary keys for all entities
- Soft deletes for user data

### Caching:
- Redis for session management
- File URL caching for performance
- User permission caching

This documentation provides a complete reference for all API endpoints in the Perwadag Backend system. For additional implementation details, refer to the source code in the respective endpoint files.
"""JWT token handling with encryption support."""

import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from jose import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from src.core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT payload encryption (initialized once)
_fernet = None

def _get_fernet():
    """Get or create Fernet encryption instance."""
    global _fernet
    if _fernet is None and settings.ENABLE_JWT_ENCRYPTION:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=settings.JWT_ENCRYPTION_SALT.encode(),
            iterations=settings.JWT_ENCRYPTION_ITERATIONS,
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.JWT_SECRET_KEY.encode()))
        _fernet = Fernet(key)
    return _fernet

def _encrypt_sensitive_data(data: Dict[str, Any]) -> str:
    """Encrypt sensitive user data."""
    fernet = _get_fernet()
    if not fernet:
        return None
    
    json_data = json.dumps(data, separators=(',', ':'))
    encrypted_data = fernet.encrypt(json_data.encode())
    return base64.urlsafe_b64encode(encrypted_data).decode()

def _decrypt_sensitive_data(encrypted_data: str) -> Dict[str, Any]:
    """Decrypt sensitive user data."""
    fernet = _get_fernet()
    if not fernet:
        return {}
    
    try:
        decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted_data = fernet.decrypt(decoded_data)
        return json.loads(decrypted_data.decode())
    except Exception:
        return {}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token with optional payload encryption."""
    # Separate public and sensitive claims
    public_data = {
        "sub": data.get("sub", ""),
        "role": data.get("role", ""),
        "type": data.get("type", "access")
    }
    
    # Encrypt sensitive data if encryption is enabled
    if settings.ENABLE_JWT_ENCRYPTION:
        sensitive_data = {}
        for key in ["username", "nama", "email", "nip"]:
            if key in data:
                sensitive_data[key] = data[key]
        
        if sensitive_data:
            encrypted_payload = _encrypt_sensitive_data(sensitive_data)
            if encrypted_payload:
                public_data["enc"] = encrypted_payload
    else:
        # If encryption disabled, include all data as before
        public_data.update({k: v for k, v in data.items() if k not in ["sub", "role", "type"]})
    
    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    public_data["exp"] = expire
    
    encoded_jwt = jwt.encode(
        public_data, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token (minimal payload)."""
    # Refresh tokens only contain essential data
    to_encode = {
        "sub": data.get("sub", ""),
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    }
    
    encoded_jwt = jwt.encode(
        to_encode, 
        settings.JWT_SECRET_KEY, 
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token with decryption support."""
    try:
        # Decode JWT
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Decrypt sensitive data if present
        if "enc" in payload and settings.ENABLE_JWT_ENCRYPTION:
            sensitive_data = _decrypt_sensitive_data(payload["enc"])
            payload.update(sensitive_data)
            # Remove encrypted field from final payload
            del payload["enc"]
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise jwt.ExpiredSignatureError("Token has expired")
    except jwt.JWTError as e:
        raise jwt.JWTError(f"Token validation failed: {str(e)}")

def get_token_claims(token: str) -> Dict[str, Any]:
    """Get token claims without verification (for debugging)."""
    try:
        # Decode without verification
        payload = jwt.get_unverified_claims(token)
        
        # Don't decrypt for unverified claims (security measure)
        if "enc" in payload:
            payload["enc"] = "[ENCRYPTED_DATA]"
        
        return payload
    except Exception as e:
        return {"error": f"Failed to decode token: {str(e)}"}
"""Script untuk generate hash password yang benar."""

from passlib.context import CryptContext

# Setup password context sama seperti di aplikasi
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_correct_hash():
    """Generate hash yang benar untuk password @Kemendag123"""
    password = "@Kemendag123"
    
    # Generate hash baru
    correct_hash = pwd_context.hash(password)
    print(f"Password: {password}")
    print(f"Correct Hash: {correct_hash}")
    print(f"Hash Length: {len(correct_hash)}")
    
    # Test verify
    is_valid = pwd_context.verify(password, correct_hash)
    print(f"Verify Test: {is_valid}")
    
    # Test dengan hash lama dari database (yang error)
    old_hash = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPjiCz9zu"
    print(f"\nOld Hash: {old_hash}")
    print(f"Old Hash Length: {len(old_hash)}")
    
    try:
        is_old_valid = pwd_context.verify(password, old_hash)
        print(f"Old Hash Verify: {is_old_valid}")
    except Exception as e:
        print(f"Old Hash Error: {e}")
    
    return correct_hash

if __name__ == "__main__":
    new_hash = generate_correct_hash()
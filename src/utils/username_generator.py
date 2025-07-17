"""Username generator with specific format: nama_depan + ddmmyyyy."""

import re
import unicodedata
from datetime import date
from typing import List, Callable, Awaitable


def normalize_name(nama: str) -> str:
    """Normalize Indonesian name for username generation."""
    # Remove accents and normalize unicode
    nama = unicodedata.normalize('NFD', nama)
    nama = ''.join(c for c in nama if unicodedata.category(c) != 'Mn')
    
    # Convert to lowercase
    nama = nama.lower()
    
    # Remove titles and honorifics (Indonesian)
    titles = [
        'dr.', 'dr', 'prof.', 'prof', 'ir.', 'ir', 'drs.', 'drs', 'dra.', 'dra',
        'h.', 'hj.', 'kh.', 'nyai', 'ustadz', 'ustadzah', 's.pd', 's.kom', 's.si',
        's.t', 's.h', 's.e', 's.sos', 'm.pd', 'm.kom', 'm.si', 'm.t', 'm.h', 'm.e'
    ]
    
    words = nama.split()
    filtered_words = []
    
    for word in words:
        # Remove dots and check if it's a title
        clean_word = word.replace('.', '')
        if clean_word not in titles:
            filtered_words.append(clean_word)
    
    nama = ' '.join(filtered_words)
    
    # Remove special characters, keep only alphanumeric and spaces
    nama = re.sub(r'[^a-z0-9\s]', '', nama)
    
    # Remove extra spaces
    nama = re.sub(r'\s+', ' ', nama).strip()
    
    return nama

def generate_username_from_name_and_inspektorat(nama: str, inspektorat: str) -> str:
    """
    Generate username: nama_depan + _ir{nomor}
    
    Examples:
    - "Daffa Jatmiko" + "Inspektorat 1" = "daffa_ir1"
    - "Siti Rahayu" + "Inspektorat 2" = "siti_ir2"
    """
    # Normalize nama and get first word
    normalized = normalize_name(nama)
    words = normalized.split()
    
    if not words:
        first_name = "user"
    else:
        first_name = words[0]
    
    # Extract inspektorat number
    inspektorat_num = "1"  # default
    if "inspektorat" in inspektorat.lower():
        import re
        match = re.search(r'(\d+)', inspektorat)
        if match:
            inspektorat_num = match.group(1)
    
    # Combine: nama_depan + _ir + nomor
    username = f"{first_name}_ir{inspektorat_num}"
    
    return username

def generate_username_with_conflict_resolution(nama: str, inspektorat: str) -> str:
    """
    Generate username with conflict resolution using second name.
    
    Examples:
    - "Ayu Marin" + "Inspektorat 1" = "ayu_marin_ir1"
    - "Ayu Siti" + "Inspektorat 1" = "ayu_siti_ir1"
    """
    # Normalize nama and get words
    normalized = normalize_name(nama)
    words = normalized.split()
    
    if len(words) < 2:
        # If only one word, use original logic
        return generate_username_from_name_and_inspektorat(nama, inspektorat)
    
    first_name = words[0]
    second_name = words[1]
    
    # Extract inspektorat number
    inspektorat_num = "1"
    if "inspektorat" in inspektorat.lower():
        import re
        match = re.search(r'(\d+)', inspektorat)
        if match:
            inspektorat_num = match.group(1)
    
    # Combine: nama_depan + _nama_kedua + _ir + nomor
    username = f"{first_name}_{second_name}_ir{inspektorat_num}"
    
    return username


def generate_username_from_name_and_date(nama: str, tanggal_lahir: date) -> str:
    """
    Generate username from nama depan + ddmmyyyy (untuk admin & inspektorat).
    
    Format: {nama_depan}{dd}{mm}{yyyy}
    Example: "Daffa Jatmiko" + 01-08-2003 = "daffa01082003"
    """
    # Normalize nama and get first word
    normalized = normalize_name(nama)
    words = normalized.split()
    
    if not words:
        first_name = "user"
    else:
        first_name = words[0]
    
    # Format date as ddmmyyyy
    date_str = tanggal_lahir.strftime("%d%m%Y")
    
    # Combine first name + date
    username = f"{first_name}{date_str}"
    
    return username

def generate_perwadag_username(nama: str) -> str:
    """
    Generate username untuk perwadag dari nama.
    
    Examples:
    - "ITPC Lagos – Nigeria" → "itpc_lagos"
    - "Atdag Moscow – Rusia" → "atdag_moscow"
    - "KJRI Kuching" → "kjri_kuching"
    """
    # Remove unicode and normalize
    nama = unicodedata.normalize('NFD', nama)
    nama = ''.join(c for c in nama if unicodedata.category(c) != 'Mn')
    
    # Convert to lowercase
    nama = nama.lower()
    
    # Split by common separators and take first two meaningful parts
    parts = re.split(r'[–—\-\s]+', nama)
    meaningful_parts = [part.strip() for part in parts if part.strip() and len(part.strip()) > 1]
    
    if len(meaningful_parts) >= 2:
        username = f"{meaningful_parts[0]}_{meaningful_parts[1]}"
    else:
        username = meaningful_parts[0] if meaningful_parts else "perwadag"
    
    # Clean username - remove non-alphanumeric except underscore
    username = re.sub(r'[^a-z0-9_]', '', username)
    
    # Limit length
    return username[:50]

def generate_username_alternatives(base_username: str, count: int = 5) -> List[str]:
    """Generate alternative usernames by adding suffix numbers."""
    alternatives = []
    
    # Add single digit suffixes
    for i in range(1, count + 1):
        alternatives.append(f"{base_username}{i}")
    
    # Add alphabet suffixes
    for letter in ['a', 'b', 'c', 'd', 'e']:
        if len(alternatives) < count:
            alternatives.append(f"{base_username}{letter}")
    
    return alternatives[:count]


async def generate_available_username(
    nama: str, 
    inspektorat: str,
    role: 'UserRole',
    check_availability: Callable[[str], Awaitable[bool]]
) -> dict:
    """
    Generate available username with conflict resolution.
    """
    if role.value == "PERWADAG":
        # Use existing perwadag logic
        base_username = generate_perwadag_username(nama)
    else:
        # Use new inspektorat logic
        base_username = generate_username_from_name_and_inspektorat(nama, inspektorat)
    
    # Check if base username is available
    is_available = await check_availability(base_username)
    
    if is_available:
        return {
            "username": base_username,
            "is_base_available": True,
            "alternatives_used": False,
            "alternatives": []
        }
    
    # Try with second name for conflict resolution
    if role.value != "PERWADAG":
        conflict_username = generate_username_with_conflict_resolution(nama, inspektorat)
        is_conflict_available = await check_availability(conflict_username)
        
        if is_conflict_available:
            return {
                "username": conflict_username,
                "is_base_available": False,
                "alternatives_used": True,
                "base_username": base_username,
                "alternatives": [conflict_username]
            }
    
    # Generate alternatives with numbers
    alternatives = generate_username_alternatives(base_username)
    
    for alt_username in alternatives:
        is_alt_available = await check_availability(alt_username)
        if is_alt_available:
            return {
                "username": alt_username,
                "is_base_available": False,
                "alternatives_used": True,
                "base_username": base_username,
                "alternatives": alternatives[:5]
            }
    
    # Fallback with timestamp
    import time
    timestamp_username = f"{base_username}{int(time.time()) % 1000}"
    
    return {
        "username": timestamp_username,
        "is_base_available": False,
        "alternatives_used": True,
        "base_username": base_username,
        "alternatives": alternatives,
        "fallback_used": True
    }


# Test examples
def test_username_generation():
    """Test username generation with Indonesian names and dates."""
    test_cases = [
        {"nama": "Daffa Jatmiko", "tanggal_lahir": date(2003, 8, 1)},  # daffa01082003
        {"nama": "Siti Rahayu Ningrum", "tanggal_lahir": date(1990, 12, 25)},  # siti25121990
        {"nama": "Dr. Ahmad Wijaya S.Kom", "tanggal_lahir": date(1985, 3, 15)},  # ahmad15031985
        {"nama": "Budi Santoso", "tanggal_lahir": date(1988, 7, 8)},  # budi08071988
        {"nama": "Muhammad Rizki Pratama", "tanggal_lahir": date(1995, 11, 30)},  # muhammad30111995
    ]
    
    print("Username Generation Test:")
    print("=" * 60)
    
    for case in test_cases:
        username = generate_username_from_name_and_date(case["nama"], case["tanggal_lahir"])
        alternatives = generate_username_alternatives(username, 3)
        
        print(f"Nama: {case['nama']}")
        print(f"Tanggal Lahir: {case['tanggal_lahir'].strftime('%d-%m-%Y')}")
        print(f"Username: {username}")
        print(f"Alternatives: {', '.join(alternatives)}")
        print("-" * 40)


if __name__ == "__main__":
    test_username_generation()
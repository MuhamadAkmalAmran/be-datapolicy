import requests
import re

def normalize_name(name: str) -> str:
    """Hilangkan spasi dan tanda baca untuk mencocokkan nama provinsi."""
    return re.sub(r'[^a-z]', '', name.lower())

# API provinsi DJPK
prov_url = "https://djpk.kemenkeu.go.id/portal/provinsi/2025"
provinces = requests.get(prov_url).json()

# Data lokal (dari tabel provinces di DB kamu)
local_provinces = [
    "ACEH", "SUMATERA UTARA", "SUMATERA BARAT", "RIAU", "JAMBI", "SUMATERA SELATAN",
    "BENGKULU", "LAMPUNG", "DKI JAKARTA", "JAWA BARAT", "JAWA TENGAH",
    "D I YOGYAKARTA", "JAWA TIMUR", "KALIMANTAN BARAT", "KALIMANTAN TENGAH",
    "KALIMANTAN SELATAN", "KALIMANTAN TIMUR", "SULAWESI UTARA", "SULAWESI TENGAH",
    "SULAWESI SELATAN", "SULAWESI TENGGARA", "BALI", "NUSA TENGGARA BARAT",
    "NUSA TENGGARA TIMUR", "MALUKU", "PAPUA", "MALUKU UTARA", "BANTEN",
    "KEP. BANGKA BELITUNG", "GORONTALO", "KEPULAUAN RIAU", "PAPUA BARAT",
    "SULAWESI BARAT", "KALIMANTAN UTARA", "PAPUA SELATAN", "PAPUA TENGAH",
    "PAPUA PEGUNUNGAN", "PAPUA BARAT DAYA", "PAPUA"
]

# Cocokkan nama dari API dan lokal
matched = {}
for code, api_name in provinces.items():
    norm_api = normalize_name(api_name.replace("Provinsi", "").strip())
    for local_name in local_provinces:
        if norm_api in normalize_name(local_name.strip()):
            matched[local_name] = code
            break

print("-- UPDATE provinces SET kemenkeu_code ...")
for name, code in matched.items():
    print(f"UPDATE provinces SET kemenkeu_code = '{code}' WHERE LOWER(name) = '{name.lower()}';")

print("\n-- UPDATE regencies SET province_kemenkeu_code ...")

# Ambil kabupaten/kota berdasarkan setiap provinsi
for prov_name, prov_code in matched.items():
    kab_url = f"https://djpk.kemenkeu.go.id/portal/pemda/{prov_code}/2025"
    kab_response = requests.get(kab_url)
    kabupaten = kab_response.json()

    # Loop kabupaten/kota, skip "00" (nama provinsi) dan "--"
    for kab_code, kab_name in kabupaten.items():
        if kab_code in ["00", "--"]:
            continue
        print(
            f"UPDATE regencies SET province_kemenkeu_code = '{kab_code}' "
            f"WHERE LOWER(name) = '{kab_name.lower().replace('kab. ', '').replace('kota ', '').strip()}';"
        )

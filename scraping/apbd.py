import requests
import pandas as pd
from rapidfuzz import fuzz

def scrape_apbd(periode, tahun, provinsi, pemda_code, pemda_name, keyword_row=None):
    url = "https://djpk.kemenkeu.go.id/portal/data/apbd"
    params = {"periode": periode, "tahun": tahun, "provinsi": provinsi, "pemda": pemda_code}
    resp = requests.get(url, params=params)
    resp.raise_for_status()

    tables = pd.read_html(resp.text)
    all_cleaned = []

    for df in tables:
        df.columns = df.columns.str.strip().str.lower()

        # Filter kolom akun & anggaran
        wanted_cols = [col for col in df.columns if "akun" in col or "anggaran" in col]
        if not wanted_cols:
            continue

        df_clean = df[wanted_cols].copy()

        # Filter baris berdasarkan keyword_row
        if keyword_row and "akun" in df_clean.columns:
            def normalize_text(text):
                return (
                    str(text)
                    .lower()
                    .strip()
                    .replace("\u00a0", " ")  # hapus non-breaking space
                    .strip(" -:/\\|")         # hapus simbol di awal/akhir
                    .replace("  ", " ")       # hapus spasi ganda
                )

            keyword_norm = normalize_text(keyword_row)
            df_clean["akun_norm"] = df_clean["akun"].apply(normalize_text)

            # --- Langkah 1: Exact match dulu ---
            hasil = df_clean[df_clean["akun_norm"] == keyword_norm]

            # --- Langkah 2: Kalau kosong, coba regex full-word match ---
            if hasil.empty:
                hasil = df_clean[
                    df_clean["akun_norm"].str.contains(fr"\b{keyword_norm}\b", regex=True, na=False)
                ]

            # --- Langkah 3: Kalau masih kosong, fallback fuzzy ---
            if hasil.empty:
                hasil = df_clean[
                    df_clean["akun_norm"].apply(lambda x: fuzz.ratio(x, keyword_norm)) >= 90
                ]

            df_clean = hasil.drop(columns=["akun_norm"])
            
        if df_clean.empty:
            continue
          # Normalisasi kolom anggaran jadi float
        if 'anggaran' in df_clean.columns and df_clean['anggaran'].notna().any():
            # Konversi string ke float
            df_clean['anggaran'] = (
                df_clean['anggaran'].astype(str)             # pastikan string
                .str.replace(r"[^\d.]", "", regex=True)      # hapus simbol & huruf
                .replace("", "0")                            # ganti string kosong ke 0
                .astype(float)                               # convert ke float
            )
        elif 'amount' in df_clean.columns:
            # langsung ambil dari amount jika anggaran tidak ada
            df_clean['anggaran'] = df_clean['amount'].astype(float)
        else:
            df_clean['anggaran'] = 0.0 

        # Tambahkan metadata
        df_clean["tahun"] = tahun
        df_clean["periode"] = periode
        df_clean["provinsi"] = provinsi
        df_clean["pemda"] = pemda_code
        df_clean["pemda_name"] = pemda_name

        all_cleaned.append(df_clean)

    if all_cleaned:
        df_final = pd.concat(all_cleaned, ignore_index=True)
        return df_final.to_dict(orient="records")  # ✅ JSON-friendly
    return all_cleaned


def scrape_multiple_years_single_pemda(
    start_year: int, end_year: int, periode: int,
    provinsi: str, pemda_code: str, pemda_name: str,
    keyword_table: str = None, keyword_row: str = None
):
    all_data = []

    for tahun in range(start_year, end_year + 1):
        try:
            print(f"📊 Scraping {pemda_name} ({provinsi}) Tahun {tahun}...")
            data = scrape_apbd(
                periode, tahun, provinsi, pemda_code, pemda_name,
                keyword_table=keyword_table, keyword_row=keyword_row
            )
            if data:
                all_data.extend(data)
        except Exception as e:
            print(f"⚠️ Gagal {pemda_name} Tahun {tahun}: {e}")

    return all_data  # ✅ list besar, bukan DataFrame

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.service import Service
import time

# =====================================================================================
# BEST PRACTICE 1: FUNGSI GENERIK UNTUK AKSES API BPS
# =====================================================================================
# Membuat satu fungsi utama untuk mengambil data dari berbagai endpoint API BPS.
# Parameter seperti 'domain', 'var', 'vervar', 'turvar', dan 'key' dibuat dinamis.
# Ini menghilangkan duplikasi kode yang ada di file pdrb.py, tingkat_partisipasi.py, dll.
# =====================================================================================


def get_bps_data(
    domain,
    var,
    tahun,
    key="020c95b2c238d613941e86cc42d5e6dd",
    vervar_label=None,
    turvar=None,
):
    """
    Fungsi generik untuk mengambil data dari Web API BPS.

    Args:
        domain (str): Kode domain wilayah (misal: '3400' untuk DIY, '3471' untuk Kota Yogyakarta).
        var (str): Kode variabel data yang ingin diambil.
        tahun (str): Tahun data, bisa satu tahun ('2023') atau rentang ('2021:2023').
        key (str): Kunci API untuk akses.
        vervar_label (str, optional): Label wilayah spesifik (misal: 'Sleman'). Jika None, akan mengambil semua wilayah.
        turvar (str, optional): Kode turunan variabel.

    Returns:
        list: Daftar (list) berisi kamus (dictionary) data yang berhasil diambil, atau list kosong jika gagal.
    """
    # Membangun URL secara dinamis berdasarkan parameter
    base_url = f"https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/{domain}/var/{var}/th/{tahun}/key/{key}/"
    if turvar:
        base_url += f"turvar/{turvar}/"

    response = requests.get(base_url)
    if response.status_code != 200:
        print(f"Gagal mengambil data dari API. Status: {response.status_code}")
        return []

    data = response.json()
    if data.get("status") != "OK" or "datacontent" not in data:
        print(f"Error dari API: {data.get('message', 'Tidak ada data konten.')}")
        return []

    # Mapping untuk mempermudah pencarian ID
    vervar_map = {item["label"]: item["val"] for item in data.get("vervar", [])}
    tahun_map = {item["label"]: item["val"] for item in data.get("tahun", [])}
    var_label = next(
        (item["label"] for item in data.get("var", []) if str(item["val"]) == str(var)),
        "Label Tidak Ditemukan",
    )

    # Menentukan ID wilayah (vervar_id)
    vervar_ids = {}
    if vervar_label:
        vervar_id = vervar_map.get(vervar_label)
        if not vervar_id:
            print(f"Wilayah '{vervar_label}' tidak ditemukan.")
            return []
        vervar_ids[vervar_label] = vervar_id
    else:  # Jika tidak ada label spesifik, ambil semua wilayah
        vervar_ids = vervar_map

    # Menentukan rentang tahun
    tahun_list = []
    if ":" in tahun:
        start, end = map(int, tahun.split(":"))
        tahun_list = [str(y) for y in range(start, end + 1) if str(y) in tahun_map]
    elif tahun in tahun_map:
        tahun_list = [tahun]

    if not tahun_list:
        print(f"Tahun '{tahun}' tidak ditemukan dalam data API.")
        return []

    # Ekstraksi data
    result_data = []
    datacontent = data.get("datacontent", {})

    for wilayah_label, wilayah_id in vervar_ids.items():
        for th in tahun_list:
            tahun_id = tahun_map[th]
            # Kunci data content bisa memiliki format berbeda, perlu penyesuaian jika ada turvar
            data_key = f"{wilayah_id}{var}0{tahun_id}0"
            if turvar:
                # Format key bisa berbeda jika ada turvar, sesuaikan jika perlu
                pass  # Contoh: data_key = f"{wilayah_id}{var}{turvar}{tahun_id}0"

            value = datacontent.get(data_key)
            if value is not None:
                result_data.append(
                    {
                        "jenis_data": var_label,
                        "wilayah": wilayah_label,
                        "tahun": th,
                        "data": float(value),
                    }
                )

    return result_data


# =====================================================================================
# BEST PRACTICE 2: FUNGSI PEMBUNGKUS (WRAPPER)
# =====================================================================================
# Membuat fungsi spesifik untuk setiap jenis data.
# Fungsi ini menyembunyikan kompleksitas parameter seperti 'domain' dan 'var'.
# Pengguna cukup memanggil fungsi sesuai kebutuhan data tanpa harus tahu detail teknis API.
# =====================================================================================


def get_pdrb(tahun, kota="KOTA YOGYAKARTA"):
    """Mengambil data PDRB per kapita ADH Konstan."""
    # 'vervar' untuk PDRB tidak menggunakan label, melainkan mengambil dari 'vervar' di JSON.
    # Kode 'pdrb.py' asli memiliki logika yang sedikit berbeda.
    # Refactoring ini menyederhanakannya.
    # Asumsi 'var' 73 adalah PDRB per kapita ADH Konstan.
    # 'vervar' 1-5 untuk masing-masing Kab/Kota di DIY.
    # Untuk simplifikasi, kita sesuaikan dengan pola generik.
    return get_bps_data(domain="3471", var="73", tahun=tahun, vervar_label=kota)


def get_gini_ratio(tahun, kabupaten_kota):
    """Mengambil data Gini Ratio untuk kabupaten/kota di DIY."""
    return get_bps_data(
        domain="3400", var="333", tahun=tahun, vervar_label=kabupaten_kota
    )


def get_tingkat_partisipasi_angkatan_kerja(tahun, kabupaten_kota):
    """Mengambil data Tingkat Partisipasi Angkatan Kerja."""
    return get_bps_data(
        domain="3471", var="152", tahun=tahun, vervar_label=kabupaten_kota
    )


def get_jumlah_angkatan_bekerja(tahun, kabupaten_kota):
    """Mengambil data Jumlah Angkatan Kerja yang Bekerja."""
    # turvar '343' artinya 'Bekerja'
    return get_bps_data(
        domain="3400", var="368", tahun=tahun, vervar_label=kabupaten_kota, turvar="343"
    )


# =====================================================================================
# BEST PRACTICE 3: FUNGSI UNTUK TUGAS YANG BERBEDA (WEB SCRAPING)
# =====================================================================================
# Kode untuk scraping data stunting (stunting.py) menggunakan library dan metode
# yang berbeda (Selenium), sehingga logikanya dipisahkan menjadi fungsi sendiri.
# Ini menjaga agar kode tetap terorganisir berdasarkan fungsinya.
# =====================================================================================


def scrape_stunting_data(year, provinsi, kab_kota):
    """
    Mengambil data stunting dari situs Kemendagri menggunakan Selenium.
    """
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Berjalan tanpa membuka browser
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    data = []
    # Inisialisasi driver di dalam 'with' statement memastikan driver ditutup otomatis
    try:
        with webdriver.Chrome(options=options) as driver:
            url = "https://aksi.bangda.kemendagri.go.id/emonev/DashPrev"
            driver.get(url)

            # Memilih tahun
            year_select = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "_inp_sel_per"))
            )
            Select(year_select).select_by_visible_text(str(year))

            # Memberi jeda agar UI sempat update setelah memilih tahun
            time.sleep(2)

            # Mengklik provinsi
            prov_select = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//td[contains(text(), '{provinsi}')]")
                )
            )
            driver.execute_script("arguments[0].click();", prov_select)

            # Menunggu tabel kabupaten/kota muncul
            table_body = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='slimScrollDiv']//tbody")
                )
            )

            # Mencari baris yang sesuai dengan kab/kota
            rows = table_body.find_elements(By.TAG_NAME, "tr")
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) > 5 and kab_kota.upper() in cols[1].text.strip().upper():
                    data.append(
                        {
                            "year": year,
                            "city": cols[1].text.strip(),
                            "amount": float(cols[5].text.strip()),
                        }
                    )
                    break  # Hentikan pencarian jika data sudah ditemukan
    except Exception as e:
        print(f"Error saat scraping data stunting untuk {kab_kota} tahun {year}: {e}")

    return data


# =====================================================================================
# CONTOH PENGGUNAAN
# =====================================================================================
# if __name__ == "__main__":
#     print("--- Contoh Pengambilan Data API BPS ---")

#     # Contoh 1: Gini Ratio Sleman tahun 2023
#     data_gini = get_gini_ratio(tahun="2023", kabupaten_kota="Sleman")
#     if data_gini:
#         print("\nData Gini Ratio:")
#         print(data_gini)

#     # Contoh 2: PDRB Kota Yogyakarta tahun 2022-2023
#     data_pdrb = get_pdrb(tahun="2022:2023", kota="KOTA YOGYAKARTA")
#     if data_pdrb:
#         print("\nData PDRB:")
#         print(data_pdrb)

#     print("\n--- Contoh Pengambilan Data Stunting (Web Scraping) ---")
#     # Contoh 3: Data Stunting Kota Yogyakarta tahun 2024
#     data_stunting = scrape_stunting_data(
#         year=2024, provinsi="DAERAH ISTIMEWA YOGYAKARTA", kab_kota="KOTA YOGYAKARTA"
#     )
#     if data_stunting:
#         print("\nData Stunting:")
#         print(data_stunting)

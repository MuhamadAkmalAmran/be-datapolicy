import requests

def fetch_data(vervar, var, th):
    url = f"https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/0000/var/{var}/vervar/{vervar}/th/{th}/key/020c95b2c238d613941e86cc42d5e6dd"
    """Mengambil data dari API dan mengembalikan data yang sudah diolah."""
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Gagal mengambil data dari API pada URL {url}")
        return []

    data = response.json()
    if data.get("status") != "OK":
        print(f"Data tidak tersedia atau status tidak OK pada URL {url}")
        return []

    vervar_list = data.get("vervar", [])
    var_list = data.get("var", [])
    turvar_list = data.get("turvar", [])
    turtahun_list = data.get("turtahun", [])
    tahun_list = data.get("tahun", [])
    datacontent = data.get("datacontent", {})

    # Mendapatkan nilai `var`, `turvar`, dan `turtahun` yang pertama sebagai asumsi
    var = var_list[0]["val"] if var_list else ""
    varlab = var_list[0]["label"] if var_list else ""
    turvar = turvar_list[0]["val"] if turvar_list else ""
    turtahun = turtahun_list[0]["val"] if turtahun_list else ""

    # Membuat list untuk data akhir
    result_data = []

    # Iterasi data vervar dan tahun, serta datacontent
    for vervar in vervar_list:
        wilayah = vervar["label"]  # Nama wilayah
        kab_kota = vervar["val"]

        for tahun in tahun_list:
            tahun_val = tahun["label"]  # Tahun
            data_key = f"{kab_kota}{var}{turvar}{tahun['val']}{turtahun}"
            jumlah_penduduk = datacontent.get(data_key, None)

            if jumlah_penduduk is not None:
                result_data.append(
                    {
                        "jenis_data": varlab,
                        "wilayah": wilayah,
                        "tahun": tahun_val,
                        "data": jumlah_penduduk,
                    }
                )
    return result_data
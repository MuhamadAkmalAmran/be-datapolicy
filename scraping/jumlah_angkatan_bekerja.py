import requests

def get_jumlah_angkatan_bekerja(var, tahun, vervar_label):
    BASE_URL = f"https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/3400/var/{var}/turvar/343/th/{tahun}/key/020c95b2c238d613941e86cc42d5e6dd/"

    print(BASE_URL)
    response = requests.get(BASE_URL)
    if response.status_code != 200:
        print(f"Gagal mengambil data dari API pada URL {BASE_URL}")
        return None
    
    data = response.json()
    if data.get("status") == "Error":
        print(f"Error dari API: {data.get('message', 'Tidak ada pesan error')}")
        return None
    
    # Ambil daftar vervar berdasarkan label yang diberikan
    vervar_map = {item["label"]: item["val"] for item in data.get("vervar", [])}
    vervar_id = vervar_map.get(vervar_label)
    print(vervar_map)

    if vervar_id is None:
        print(f"Wilayah '{vervar_label}' tidak ditemukan dalam data API")
        return None

    # Ambil daftar tahun berdasarkan parameter tahun
    tahun_map = {str(item["val"]) : str(item["label"])  for item in data.get("tahun", [])}
    print(tahun_map)

    if ":" in tahun:
        tahun_range = tahun.split(":")
        tahun_list = [str(year) for year in range(int(tahun_range[0]), int(tahun_range[1]) + 1) if str(year) in tahun_map]
    else:
        tahun_list = [tahun] if tahun in tahun_map else []
        
    if not tahun_list:
        print(f"Tahun '{tahun}' tidak ditemukan dalam data API")
        return None
    print(tahun_list)
    # Ambil nilai var
    var_data = data.get("var", [])
    var_label = next((item["label"] for item in var_data if str(item["val"]) == str(var)), "")

    # Ambil data sesuai vervar dan tahun
    datacontent = data.get("datacontent", {})
    result_data = []

    for tahun_label in tahun_list:
        tahun_id = tahun_label
        print(tahun_id)
        datakey = f"{vervar_id}{var}343{tahun_id}0"
        print(datakey)
        value = datacontent.get(datakey, None)

        result_data.append({
            "jenis_data": var_label,
            "wilayah": vervar_label,
            "tahun": tahun_map[tahun_label],
            "data": value
        })

    return result_data

# def get_jumlah_angkatan_pengangguran(var, tahun, vervar_label):
#     BASE_URL = f"https://webapi.bps.go.id/v1/api/list/model/data/lang/ind/domain/3400/var/{var}/turvar/342/key/020c95b2c238d613941e86cc42d5e6dd/"

#     response = requests.get(BASE_URL)
#     if response.status_code != 200:
#         print(f"Gagal mengambil data dari API pada URL {BASE_URL}")
#         return None

#     data = response.json()
    
#     # Ambil daftar vervar berdasarkan label yang diberikan
#     vervar_map = {item["label"]: item["val"] for item in data.get("vervar", [])}
#     vervar_id = vervar_map.get(vervar_label)

#     if vervar_id is None:
#         print(f"Wilayah '{vervar_label}' tidak ditemukan dalam data API")
#         return None

#     # Ambil daftar tahun berdasarkan parameter tahun
#     tahun_map = {str(item["label"]): item["val"] for item in data.get("tahun", [])}

#     if ":" in tahun:
#         tahun_range = tahun.split(":")
#         tahun_list = [str(year) for year in range(int(tahun_range[0]), int(tahun_range[1]) + 1) if str(year) in tahun_map]
#     else:
#         tahun_list = [tahun] if tahun in tahun_map else []

#     if not tahun_list:
#         print(f"Tahun '{tahun}' tidak ditemukan dalam data API")
#         return None

#     # Ambil nilai var
#     var_data = data.get("var", [])
#     var_label = next((item["label"] for item in var_data if str(item["val"]) == str(var)), "")

#     # Ambil data sesuai vervar dan tahun
#     datacontent = data.get("datacontent", {})
#     result_data = []

#     for tahun_label in tahun_list:
#         tahun_id = tahun_map[tahun_label]
#         datakey = f"{vervar_id}{var}0{tahun_id}0"
#         value = datacontent.get(datakey, None)

#         result_data.append({
#             "jenis_data": var_label,
#             "wilayah": vervar_label,
#             "tahun": tahun_label,
#             "data": value
#         })

#     return result_data

# Contoh penggunaan
# data = get_jumlah_angkatan_bekerja(var="368", tahun="121", vervar_label="Sleman")

# if data:
#     print(data)

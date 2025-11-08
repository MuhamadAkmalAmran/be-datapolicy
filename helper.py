from models import Category

def parse_amount(value: str) -> float:
    """
    Convert string like '1.885,42 M' or 'Rp 1.000.000' to float
    """
    if not value:
        return 0.0

    value = str(value).upper().strip()

    multiplier = 1
    if "M" in value:
        multiplier = 1_000_000
        value = value.replace("M", "")
    elif "T" in value:
        multiplier = 1_000_000_000_000
        value = value.replace("T", "")

    # Hapus simbol selain angka dan desimal
    value = value.replace("RP", "").replace(" ", "").replace(".", "").replace(",", ".")
    
    try:
        return float(value) * multiplier
    except:
        return 0.0

# Define the dictionary as a constant outside the function
CATEGORY_KEYWORDS = {
    28: "Pendapatan Daerah",
    29: "PAD",
    30: "TKDD",
    31: "Pendapatan Lainnya",
    32: "Pajak Daerah",
    33: "Retribusi Daerah",
    34: "Hasil Pengelolaan Kekayaan Daerah yang Dipisahkan",
    35: "Lain-Lain PAD yang Sah",
    36: "Pendapatan Transfer Pemerintah Pusat",
    37: "Pendapatan Transfer Antar Daerah",
    38: "Pendapatan Hibah",
    39: "Dana Darurat",
    40: "Lain-lain Pendapatan Sesuai dengan Ketentuan Peraturan Perundang-Undangan",
    41: "Belanja Daerah",
    42: "Belanja Pegawai",
    43: "Belanja Barang dan Jasa",
    44: "Belanja Modal",
    45: "Belanja Lainnya",
    46: "Belanja Bantuan Keuangan",
    47: "Belanja Subsidi",
    48: "Belanja Hibah",
    49: "Belanja Bantuan Sosial",
    50: "Belanja Tidak Terduga",
    60: "Pembiayaan Daerah",
    61: "Penerimaan Pembiayaan Daerah",
    62: "Sisa Lebih Perhitungan Anggaran Tahun Sebelumnya",
    63: "Penerimaan Kembali Pemberian Pinjaman Daerah",
    64: "Pengeluaran Pembiayaan Daerah",
    65: "Penyertaan Modal Daerah",
}

# The helper function can simply return the constant
def get_category_keywords():
    return CATEGORY_KEYWORDS

PEMDA_NAMES = {
    "05": "Kota Yogyakarta",
    "17": "Kota Bandung",
    "03": "Kulon Progo",
    "37": "Kota Surabaya",
    "02": "Banyuwangi",
}

def get_pemda_names():
    return PEMDA_NAMES


# Additional helper functions to add to your API file

def _get_category_display_names(variables):
    """Get display names for categories"""
    category_names = {}
    try:
        categories = Category.query.all()
        for cat in categories:
            if cat.name in variables:
                category_names[cat.name] = cat.display_name or cat.name
    except:
        # Fallback to variable names if database query fails
        for var in variables:
            category_names[var] = var
    return category_names

def _calculate_correlations(df, variables):
    """Calculate correlation matrix for variables"""
    try:
        corr_matrix = df[variables].corr()
        return corr_matrix.to_dict()
    except:
        return {}

def _generate_linear_interpretation(model, variables, category_names, analysis_type):
    """Generate contextual interpretation for linear regression"""
    independent_vars = variables[:-1]
    dependent_var = variables[-1]
    
    dep_name = category_names.get(dependent_var, dependent_var)
    
    interpretation = f"ANALISIS REGRESI LINEAR - {dep_name.upper()}\n\n"
    
    # Model significance
    if model.f_pvalue < 0.001:
        significance = "sangat signifikan (p < 0.001)"
    elif model.f_pvalue < 0.01:
        significance = "signifikan (p < 0.01)"
    elif model.f_pvalue < 0.05:
        significance = "cukup signifikan (p < 0.05)"
    else:
        significance = "tidak signifikan (p ≥ 0.05)"
    
    interpretation += f"🔍 SIGNIFIKANSI MODEL: Model secara keseluruhan {significance}\n\n"
    
    # R-squared interpretation
    r_sq_pct = model.rsquared * 100
    if r_sq_pct >= 80:
        r_sq_desc = "sangat kuat"
    elif r_sq_pct >= 60:
        r_sq_desc = "kuat"
    elif r_sq_pct >= 40:
        r_sq_desc = "sedang"
    elif r_sq_pct >= 20:
        r_sq_desc = "lemah"
    else:
        r_sq_desc = "sangat lemah"
    
    interpretation += f"📊 KEKUATAN MODEL: R² = {r_sq_pct:.1f}% - Hubungan {r_sq_desc}\n"
    interpretation += f"   Model dapat menjelaskan {r_sq_pct:.1f}% variasi dalam {dep_name}\n\n"
    
    # Coefficients interpretation
    interpretation += "📈 PENGARUH VARIABEL:\n"
    
    for i, var in enumerate(independent_vars):
        coef = model.params[i + 1]  # Skip intercept
        p_val = model.pvalues[i + 1]
        var_name = category_names.get(var, var)
        
        # Significance of individual coefficient
        if p_val < 0.05:
            sig_text = "signifikan"
            sig_symbol = "✓"
        else:
            sig_text = "tidak signifikan"
            sig_symbol = "✗"
        
        # Direction and magnitude
        if coef > 0:
            direction = "positif"
            effect = "meningkat"
        else:
            direction = "negatif" 
            effect = "menurun"
        
        interpretation += f"   {sig_symbol} {var_name}: Pengaruh {direction} ({sig_text})\n"
        interpretation += f"     → Setiap kenaikan 1 unit {var_name}, {dep_name} {effect} sebesar {abs(coef):.3f} unit\n"
    
    return interpretation

def _generate_polynomial_interpretation(model, variables, category_names, analysis_type, r_squared):
    """Generate contextual interpretation for polynomial regression"""
    independent_vars = variables[:-1]
    dependent_var = variables[-1]
    
    dep_name = category_names.get(dependent_var, dependent_var)
    
    interpretation = f"ANALISIS REGRESI NON-LINEAR (POLYNOMIAL) - {dep_name.upper()}\n\n"
    
    # R-squared interpretation
    r_sq_pct = r_squared * 100
    if r_sq_pct >= 80:
        r_sq_desc = "sangat kuat"
    elif r_sq_pct >= 60:
        r_sq_desc = "kuat"
    elif r_sq_pct >= 40:
        r_sq_desc = "sedang"
    elif r_sq_pct >= 20:
        r_sq_desc = "lemah"
    else:
        r_sq_desc = "sangat lemah"
    
    interpretation += f"📊 KEKUATAN MODEL: R² = {r_sq_pct:.1f}% - Hubungan non-linear {r_sq_desc}\n"
    interpretation += f"   Model polynomial dapat menjelaskan {r_sq_pct:.1f}% variasi dalam {dep_name}\n\n"
    
    interpretation += "🔄 KARAKTERISTIK NON-LINEAR:\n"
    interpretation += f"   Model menangkap hubungan yang tidak linear antara variabel independen dan {dep_name}\n"
    interpretation += "   Hubungan ini menunjukkan adanya akselerasi atau deselerasi dalam pengaruh variabel\n\n"
    
    # Coefficient information
    interpretation += f"📈 KOEFISIEN MODEL:\n"
    interpretation += f"   Intercept: {model.intercept_:.3f}\n"
    for i, coef in enumerate(model.coef_):
        interpretation += f"   Koefisien {i+1}: {coef:.3f}\n"
    
    return interpretation

def _generate_enhanced_summary(model, variables, category_names, analysis_type, regression_type, r_squared, city):
    """Generate enhanced contextual summary"""
    independent_vars = variables[:-1]
    dependent_var = variables[-1]
    
    dep_name = category_names.get(dependent_var, dependent_var)
    city_context = city.replace("Kota ", "").replace("Kabupaten ", "")
    
    summary = f"RINGKASAN ANALISIS REGRESI - {city_context.upper()}\n"
    summary += "=" * 50 + "\n\n"
    
    # Analysis context
    if analysis_type == "single":
        indep_name = category_names.get(independent_vars[0], independent_vars[0])
        summary += f"🎯 FOKUS ANALISIS: Hubungan {indep_name} terhadap {dep_name}\n"
    else:
        summary += f"🎯 FOKUS ANALISIS: Pengaruh multivariabel terhadap {dep_name}\n"
        summary += f"   Variabel independen: {', '.join([category_names.get(v, v) for v in independent_vars])}\n"
    
    summary += f"📍 WILAYAH STUDI: {city}\n"
    summary += f"📊 METODE: Regresi {'Linear' if regression_type == 'linear' else 'Non-Linear (Polynomial)'}\n\n"
    
    # Key findings
    r_sq_pct = r_squared * 100
    summary += "🔍 TEMUAN UTAMA:\n"
    
    if r_sq_pct >= 70:
        summary += f"   ✅ Model menunjukkan hubungan yang SANGAT KUAT (R² = {r_sq_pct:.1f}%)\n"
        summary += f"   ✅ {dep_name} dapat diprediksi dengan baik menggunakan variabel independen\n"
    elif r_sq_pct >= 50:
        summary += f"   ✅ Model menunjukkan hubungan yang KUAT (R² = {r_sq_pct:.1f}%)\n"
        summary += f"   ✅ Variabel independen memiliki pengaruh substansial terhadap {dep_name}\n"
    elif r_sq_pct >= 30:
        summary += f"   ⚠️ Model menunjukkan hubungan yang SEDANG (R² = {r_sq_pct:.1f}%)\n"
        summary += f"   ⚠️ Ada faktor lain yang juga mempengaruhi {dep_name}\n"
    else:
        summary += f"   ❌ Model menunjukkan hubungan yang LEMAH (R² = {r_sq_pct:.1f}%)\n"
        summary += f"   ❌ Variabel independen kurang dapat menjelaskan variasi {dep_name}\n"
    
    # Model significance for linear regression
    if regression_type == "linear" and hasattr(model, 'f_pvalue'):
        if model.f_pvalue < 0.05:
            summary += f"   ✅ Model secara statistik signifikan (p = {model.f_pvalue:.4f})\n"
        else:
            summary += f"   ❌ Model secara statistik tidak signifikan (p = {model.f_pvalue:.4f})\n"
    
    summary += "\n"
    
    # Recommendations
    summary += "💡 REKOMENDASI:\n"
    if r_sq_pct >= 60:
        summary += f"   → Model dapat digunakan untuk prediksi {dep_name} di {city_context}\n"
        summary += "   → Variabel independen terbukti berpengaruh signifikan\n"
    elif r_sq_pct >= 30:
        summary += "   → Model memerlukan variabel tambahan untuk meningkatkan akurasi\n"
        summary += f"   → Perlu kajian faktor lain yang mempengaruhi {dep_name}\n"
    else:
        summary += "   → Model tidak cocok untuk prediksi yang akurat\n"
        summary += f"   → Perlu identifikasi variabel yang lebih relevan untuk {dep_name}\n"
    
    if analysis_type == "multi" and len(independent_vars) > 3:
        summary += "   → Pertimbangkan seleksi variabel untuk mengurangi kompleksitas model\n"
    
    return summary
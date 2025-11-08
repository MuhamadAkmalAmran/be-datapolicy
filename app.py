from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
import numpy as np
import pandas as pd
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload
import pymysql
import os
from io import BytesIO
import logging
from flask_migrate import Migrate
import statsmodels.api as sm
from models import db, Data, Category, APBD, Stunting, Province, Regency
import datetime
import openpyxl
from scipy import stats
from scraping import data_fetcher, jumlah_angkatan_bekerja, pdrb, scraping_bps, stunting, indeks_gini, tingkat_partisipasi, apbd
from scraping.provinces_regencies_fixed import get_latest_provinces_regencies_data
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import io
import requests
import helper
from flask_seeder import FlaskSeeder


load_dotenv()

app = Flask(__name__)
CORS(app)

# app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://admin:admin@localhost:3304/data_policy"
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv('DATABASE_URL')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["FILE_FOLDER"] = "files/"  # Direktori penyimpanan file
os.makedirs(app.config["FILE_FOLDER"],exist_ok=True)  # Buat direktori jika belum ada
logging.basicConfig(level=logging.DEBUG)

db.init_app(app)
migrate = Migrate(app, db)
seeder = FlaskSeeder()
seeder.init_app(app, db)

@app.route("/api/fetch_data", methods=["POST"])
def fetch_data_api():
    try:
        body = request.get_json()
        if not body:
            return jsonify({"error": "No JSON data provided"}), 400

        vervar = body.get("wilayah")
        var = body.get("jenis_data")
        th = body.get("tahun")
        province_id = body.get("provinsi")

        print(f"Received data: wilayah={vervar}, jenis_data={var}, tahun={th}")

        # Fetch new data using scraping function
        data = scraping_bps.fetch_data(vervar, var, th)
        print(f"Fetched data: {data}")

        if not data:
            return jsonify({"error": "No data found or failed to fetch data"}), 404

        # Determine category based on var
        category_mapping = {
            "413": 1,
            "619": 2,
            "621": 5,
            "414": 6
        }
        category = category_mapping.get(var)
        if not category:
            return jsonify({"error": f"Invalid jenis_data value: {var}"}), 400

        updated_entries = []
        inserted_entries = []

        for new_data in data:
            year = new_data['tahun']
            amount = new_data['data']

            # Check if the record already exists
            existing_entry = Data.query.filter_by(
                regency_id=vervar,
                year=year,
                category_id=category
            ).first()

            if existing_entry:
                # Update if amount is different
                if existing_entry.amount != amount:
                    print(f"Updating existing record (year={year}) from {existing_entry.amount} to {amount}")
                    existing_entry.amount = amount
                    existing_entry.province_id = province_id  # optional update
                    updated_entries.append(existing_entry.json())
            else:
                # Insert new record
                print(f"Inserting new record for year={year}")
                entry = Data(
                    amount=amount,
                    regency_id=vervar,
                    year=year,
                    category_id=category,
                    province_id=province_id
                )
                db.session.add(entry)
                inserted_entries.append(entry)

        db.session.commit()
        print("Database successfully updated.")

        return jsonify({
            "message": "Data successfully synchronized",
            "data": data,
            "inserted_count": len(inserted_entries),
            "updated_count": len(updated_entries)
        }), 200

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "An internal error occurred", "details": str(e)}), 500


@app.route('/api/indeks-gini', methods=['POST'])
def fetch_and_save_bps_data():
    try:
        # Ambil parameter dari query string
        body = request.get_json()
        var = body.get("jenis_data")
        tahun = body.get("tahun")
        vervar_label = body.get("wilayah")
        province_id = body.get("provinsi") 

        if not var or not tahun or not vervar_label:
            return jsonify({"error": "Parameter jenis_dataa, tahun, dan wilayah diperlukan"}), 400

        # Ambil data dari API BPS
        bps_data = indeks_gini.get_bps_data(var, tahun, vervar_label)

        if bps_data is None:
            return jsonify({"error": "Data tidak tersedia data dari API BPS"}), 404

        # Simpan data ke database
        for item in bps_data:
            # Cek apakah data sudah ada di database
            existing_data = Data.query.filter_by(
                year=item["tahun"],
                city=item["wilayah"],
                category_id=10  # Gunakan category_id jika ini adalah foreign key
            ).first()

            if existing_data:
                # Jika data sudah ada, perbarui nilainya
                return jsonify({
                    "messsage": "Data Already exist"
                }), 400
            else:
                # Jika data belum ada, buat entri baru
                new_data = Data(
                    amount=item["data"],
                    year=item["tahun"],
                    city=item["wilayah"],
                    category_id=10,
                    
                )
                db.session.add(new_data)

        db.session.commit()

        return jsonify({
            "message": "Data berhasil diambil dan disimpan", 
            "data": new_data.json()}), 200

    except Exception as e:
        # Tangani kesalahan yang terjadi
        db.session.rollback()  # Rollback perubahan jika terjadi kesalahan
        return jsonify({"error": f"Terjadi kesalahan: {str(e)}"}), 500

@app.route('/api/tingkat-partisipasi', methods=['POST'])
def fetch_tingkat_partisipasi():
    try:
        # Ambil parameter dari query string
        body = request.get_json()
        var = body.get("jenis_data")
        tahun = body.get("tahun")
        vervar_label = body.get("wilayah")

        if not var or not tahun or not vervar_label:
            return jsonify({"error": "Parameter jenis_dataa, tahun, dan wilayah diperlukan"}), 400

        # Ambil data dari API BPS
        bps_data = tingkat_partisipasi.get_bps_data(var, tahun, vervar_label)

        if bps_data is None:
            return jsonify({"error": "Data tidak tersedia data dari API BPS"}), 404

        # Simpan data ke database
        for item in bps_data:
            # Cek apakah data sudah ada di database
            existing_data = Data.query.filter_by(
                year=item["tahun"],
                city=item["wilayah"],
                category_id=7  # Gunakan category_id jika ini adalah foreign key
            ).first()

            if existing_data:
                # Jika data sudah ada, perbarui nilainya
                return jsonify({
                    "messsage": "Data Already exist"
                }), 400
            else:
                # Jika data belum ada, buat entri baru
                new_data = Data(
                    amount=item["data"],
                    year=item["tahun"],
                    city=item["wilayah"],
                    category_id=7  # Sesuaikan dengan kategori yang sesuai
                )
                db.session.add(new_data)

        db.session.commit()

        return jsonify({
            "message": "Data berhasil diambil dan disimpan", 
            "data": new_data.json()}), 200

    except Exception as e:
        # Tangani kesalahan yang terjadi
        db.session.rollback()  # Rollback perubahan jika terjadi kesalahan
        return jsonify({"error": f"Terjadi kesalahan: {str(e)}"}), 500

@app.route('/api/jumlah-angkatan-bekerja', methods=['POST'])
def fetch_jumlah_angkatan_bekerja():
    try:
        # Ambil parameter dari query string
        body = request.get_json()
        var = body.get("jenis_data")
        tahun = body.get("tahun")
        vervar_label = body.get("wilayah")

        if not var or not tahun or not vervar_label:
            return jsonify({"error": "Parameter jenis_dataa, tahun, dan wilayah diperlukan"}), 400

        # Ambil data dari API BPS
        bps_data = jumlah_angkatan_bekerja.get_jumlah_angkatan_bekerja(var, tahun, vervar_label)

        if bps_data is None:
            return jsonify({"error": "Data tidak tersedia data dari API BPS"}), 404

        updated_data = []
        for item in bps_data:
            # Cek apakah data sudah ada di database
            existing_data = Data.query.filter_by(
                year=item["tahun"],
                city=item["wilayah"],
                category_id=8
            ).first()

            if existing_data:
                if existing_data.amount != item["data"]:
                    existing_data.amount = item["data"]
                    db.session.add(existing_data)
                    updated_data.append(existing_data.json())
            else:
                new_data = Data(
                    amount=item["data"],
                    year=item["tahun"],
                    city=item["wilayah"],
                    category_id=8
                )
                db.session.add(new_data)
                updated_data.append(new_data.json())

        db.session.commit()

        return jsonify({"message": "Data berhasil diambil dan disimpan", "data": new_data.json()}), 200

    except Exception as e:
        # Tangani kesalahan yang terjadi
        db.session.rollback()  # Rollback perubahan jika terjadi kesalahan
        return jsonify({"error": f"Terjadi kesalahan: {str(e)}"}), 500

@app.route('/api/pdrb', methods=['POST'])
def fetch_pdrb():
    try:
        # Ambil parameter dari query string
        body = request.get_json()
        var = body.get("jenis_data")
        tahun = body.get("tahun")
        wilayah = body.get("wilayah")

        if not var or not tahun:
            return jsonify({"error": "Parameter jenis_dataa, tahun, dan wilayah diperlukan"}), 400

        # Ambil data dari API BPS
        bps_data = pdrb.get_bps_data(var, tahun)

        if bps_data is None:
            return jsonify({"error": "Data tidak tersedia data dari API BPS"}), 404

        # Simpan data ke database
        for item in bps_data:
            # Cek apakah data sudah ada di database
            existing_data = Data.query.filter_by(
                year=item["tahun"],
                city=wilayah,
                category_id=9  # Gunakan category_id jika ini adalah foreign key
            ).first()

            if existing_data:
                # Jika data sudah ada, perbarui nilainya
                return jsonify({
                    "messsage": "Data Already exist"
                }), 400
            else:
                # Jika data belum ada, buat entri baru
                new_data = Data(
                    amount=item["data"],
                    year=item["tahun"],
                    city=wilayah,
                    category_id=9  # Sesuaikan dengan kategori yang sesuai
                )
                db.session.add(new_data)
            

        db.session.commit()

        return jsonify({"message": "Data berhasil diambil dan disimpan", "data": new_data.json()}), 200

    except Exception as e:
        # Tangani kesalahan yang terjadi
        db.session.rollback()  # Rollback perubahan jika terjadi kesalahan
        return jsonify({"error": f"Terjadi kesalahan: {str(e)}"}), 500

@app.route("/stunting", methods=["GET"])
def list_stunting():
    year = request.args.get("year")
    city = request.args.get("city")

    query = Stunting.query

    if year:
        query = query.filter_by(year=year)
    if city:
        query = query.filter_by(city=city)

    data = query.all()
    return jsonify([item.json() for item in data]), 200


@app.route('/api/data', methods=['GET'])
def get_data():
    """
    Get data with optional filters for visualization
    Query params:
    - category_id: Filter by category (required)
    - province_id: Filter by province (shows all regencies in province)
    - regency_id: Filter by specific regency
    """
    try:
        category_id = request.args.get('category_id', type=int)
        province_id = request.args.get('province_id', type=int)
        regency_id = request.args.get('regency_id', type=int)

        if not category_id:
            return jsonify({"error": "category_id is required"}), 400

        # Build query - HANYA query tabel Data
        query = Data.query.filter(Data.category_id == category_id)

        # Apply location filters berdasarkan indeks
        if regency_id:
            query = query.filter(Data.regency_id == regency_id)
        elif province_id:
            query = query.filter(Data.province_id == province_id)

        # Execute query
        data_list = query.order_by(Data.year.asc()).all()

        # Kumpulkan unique IDs untuk lookup
        regency_ids = list(set([d.regency_id for d in data_list if d.regency_id]))
        province_ids = list(set([d.province_id for d in data_list if d.province_id]))
        
        # Query Province dan Regency secara terpisah (bukan relationship)
        regencies_dict = {}
        provinces_dict = {}
        
        if regency_ids:
            regencies = Regency.query.filter(Regency.id.in_(regency_ids)).all()
            regencies_dict = {r.id: {'id': r.id, 'name': r.name} for r in regencies}
        
        if province_ids:
            provinces = Province.query.filter(Province.id.in_(province_ids)).all()
            provinces_dict = {p.id: {'id': p.id, 'name': p.name} for p in provinces}

        # Format response dengan lookup manual
        result = []
        for d in data_list:
            item = {
                'id': d.id,
                'year': d.year,
                'amount': float(d.amount) if d.amount is not None else 0,
                'regency_id': d.regency_id,
                'province_id': d.province_id,
                'category_id': d.category_id,
                'category': d.category.to_dict() if d.category else None,
                # Lookup regency name dari dictionary
                'regency': regencies_dict.get(d.regency_id) if d.regency_id else None,
                # Lookup province name dari dictionary
                'province': provinces_dict.get(d.province_id) if d.province_id else None,
            }
            result.append(item)

        return jsonify(result), 200

    except Exception as e:
        app.logger.error(f"Error fetching data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Failed to fetch data", 
            "details": str(e)
        }), 500

# Create new data
@app.route("/api/data", methods=["POST"])
def create_data():
    try:
        data = request.get_json()
        new_data = Data(
            amount=data["amount"],
            year=data["year"],
            city=data["city"],
            category_id=data["category_id"],
            regency_id=data.get("regency_id"),
            province_id=data.get("province_id")
        )

        existing_data = Data.query.filter_by(
            year=new_data.year,
            city=new_data.city,
            category_id=new_data.category_id,
            regency_id=new_data.regency_id,
            province_id=new_data.province_id
        ).first()

        if existing_data:
            return (
                jsonify(
                    {
                        "message": "Data already exists",
                    }
                ),
                400,
            )
        db.session.add(new_data)
        db.session.commit()
        return jsonify(new_data.json()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


# Update data
@app.route("/api/data/<int:id>", methods=["PUT"])
def update_data(id):
    try:
        data = Data.query.get_or_404(id)
        update_data = request.get_json()

        data.amount = update_data.get("amount", data.amount)
        data.year = update_data.get("year", data.year)
        data.city = update_data.get("city", data.city)
        data.category_id = update_data.get("category_id", data.category_id)
        data.regency_id = update_data.get("regency_id", data.regency_id)
        data.province_id = update_data.get("province_id", data.province_id)

        db.session.commit()
        return jsonify(data.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


# Delete data
@app.route("/api/data/<int:id>", methods=["DELETE"])
def delete_data(id):
    try:
        data = Data.query.get_or_404(id)
        db.session.delete(data)
        db.session.commit()
        return jsonify({"message": "Data deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400


# Get all categories
@app.route('/api/categories', methods=['GET'])
def get_categories():
    search = request.args.get('search', '')  # ambil dari query param

    query = Category.query

    if search:
        query = query.filter(Category.name.ilike(f"%{search}%"))

    categories = query.order_by(Category.name.asc()).all()
    return jsonify([category.to_dict() for category in categories])

@app.route('/api/categories/<int:id>', methods=['GET'])
def get_category(id):
    category = Category.query.get_or_404(id)
    return jsonify(category.to_dict())

@app.route('/api/categories', methods=['POST'])
def create_category():
    data = request.get_json()
    new_category = Category(name=data.get('name'))
    db.session.add(new_category)
    db.session.commit()
    return jsonify(new_category.to_dict()), 201

@app.route('/api/categories/<int:id>', methods=['PUT'])
def update_category(id):
    category = Category.query.get_or_404(id)
    data = request.get_json()
    category.name = data.get('name', category.name)
    db.session.commit()
    return jsonify(category.to_dict())

@app.route('/api/categories/<int:id>', methods=['DELETE'])
def delete_category(id):
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    return jsonify({"message": "Category deleted successfully"})


@app.route("/stunting", methods=["POST"])
def scrape_endpoint():
    data = request.get_json()
    kab_kota = data.get("kab_kota")
    year = data.get("year")

    if not all([year, kab_kota]):
        return (
            jsonify({"error": "Please provide year and kabupaten_kota parameters."}),
            400,
        )

    # Determine provinsi based on kabupaten_kota
    if kab_kota in ["Kota Yogyakarta", "Kulon Progo"]:
        provinsi = "DI YOGYAKARTA"
    elif kab_kota in ["Kota Surabaya", "Banyuwangi"]:
        provinsi = "JAWA TIMUR"
    elif kab_kota == "Kota Bandung":
        provinsi = "JAWA BARAT"
    else:
        return (
            jsonify(
                {
                    "error": "Unable to determine provinsi for the provided kabupaten_kota."
                }
            ),
            400,
        )

    existing_data = Data.query.filter_by(
        year=year, city=kab_kota, category_id=3
    ).first()

    if existing_data:
        return (
            jsonify(
                {
                    "message": "Data already exists",
                }
            ),
            400,
        )

    # driver = stunting.init_driver()
    scraped_data = stunting.scrape_data(year, provinsi, kab_kota)

    # Save data to database
    for record in scraped_data:
        entry = Data(
            year=record["year"],
            city=record["city"],
            amount=record["amount"],
            category_id=3,
        )
        db.session.add(entry)
    db.session.commit()

    return jsonify(entry.json())


@app.route("/apbd", methods=["POST"])
def create_apbd():
    data = request.form  # Gunakan request.form untuk mengambil data teks
    file = request.files.get("file")  # Ambil file dari request

    # Simpan file jika ada
    file_path = None
    if file:
        file_name = file.filename
        file_path = os.path.join(app.config["FILE_FOLDER"], file_name)
        file.save(file_path)  # Simpan file ke direktori

    # Buat objek APBD baru
    new_apbd = APBD(
        city=data.get("city"),
        type=data.get("type"),
        year=data.get("year"),
        amount=data.get("amount"),
        file_path=file_path,  # Simpan jalur file ke database
    )

    # Tambahkan ke database
    db.session.add(new_apbd)
    db.session.commit()

    return jsonify({"message": "APBD created", "data": new_apbd.to_dict()}), 201


# def _validate_request(data):
#     """Validates the presence and format of required request parameters."""
#     required_params = ["regression_type", "city", "analysis_type"]
#     if not all(param in data for param in required_params):
#         return "Missing required parameters: regression_type, city, and analysis_type", None

#     if data["regression_type"] not in ["linear", "non_linear"]:
#         return "Invalid regression type. Must be 'linear' or 'non_linear'", None
    
#     if data["analysis_type"] not in ["single", "multi"]:
#         return "Invalid analysis type. Must be 'single' or 'multi'", None

#     if data["analysis_type"] == "single":
#         if not all(k in data for k in ["independent_variable", "dependent_variable"]):
#             return "For single analysis, both independent_variable and dependent_variable are required", None
#         variables = [data["independent_variable"], data["dependent_variable"]]
#     else: # multi
#         variables = data.get("variables", [])
#         if len(variables) < 2:
#             return "For multi analysis, at least 2 variables are required", None
    
#     return None, variables


def _fetch_and_prepare_data(variables, city):
    """Fetches data from the database and merges it into a single DataFrame."""
    data_frames = []
    for var in variables:
        var_data = (
            db.session.query(Data.amount, Data.year, Data.city)
            .join(Category)
            .filter(Category.name == var, Data.city == city)
            .order_by(Data.year)
            .all()
        )
        if not var_data:
            return None # Return None if any variable has no data
            
        df = pd.DataFrame(var_data, columns=["amount", "year", "city"])
        df = df.rename(columns={"amount": var})
        data_frames.append(df)

    if not data_frames:
        return None

    # Merge data frames on year and city
    merged_df = data_frames[0]
    for df in data_frames[1:]:
        merged_df = pd.merge(merged_df, df, on=["year", "city"], how="inner")

    return merged_df


def _fetch_and_prepare_data(variables, city):
    """Fetches data from the database and merges it into a single DataFrame."""
    data_frames = []
    for var in variables:
        var_data = (
            db.session.query(Data.amount, Data.year, Data.city)
            .join(Category)
            .filter(Category.name == var, Data.city == city)
            .order_by(Data.year)
            .all()
        )
        if not var_data:
            return None # Return None if any variable has no data
            
        df = pd.DataFrame(var_data, columns=["amount", "year", "city"])
        df = df.rename(columns={"amount": var})
        data_frames.append(df)

    if not data_frames:
        return None

    # Merge data frames on year and city
    merged_df = data_frames[0]
    for df in data_frames[1:]:
        merged_df = pd.merge(merged_df, df, on=["year", "city"], how="inner")

    return merged_df


# Additional robust helper functions to handle numpy arrays properly

def _safe_to_list(data):
    """Safely convert various data types to list"""
    if hasattr(data, 'tolist'):  # numpy array or pandas series
        return data.tolist()
    elif hasattr(data, 'values'):  # pandas dataframe/series
        return data.values.tolist()
    elif isinstance(data, (list, tuple)):
        return list(data)
    else:
        return [data]

def _safe_conf_int_to_list(conf_int):
    """Safely convert confidence intervals to list"""
    try:
        if hasattr(conf_int, 'values'):
            return conf_int.values.tolist()
        elif hasattr(conf_int, 'to_numpy'):
            return conf_int.to_numpy().tolist()
        elif hasattr(conf_int, 'tolist'):
            return conf_int.tolist()
        else:
            return conf_int
    except:
        return []

def _get_category_display_names(variables):
    """Get display names for categories"""
    category_names = {}
    try:
        # Assuming you have a Category model - adjust based on your actual model
        categories = Category.query.all()
        for cat in categories:
            if cat.name in variables:
                category_names[cat.name] = cat.display_name or cat.name
    except Exception as e:
        print(f"Warning: Could not fetch category names: {e}")
        # Fallback to variable names if database query fails
        for var in variables:
            category_names[var] = var.replace('_', ' ').title()
    return category_names

def _calculate_correlations(df, variables):
    """Calculate correlation matrix for variables"""
    try:
        # Ensure we only use numeric columns
        numeric_vars = []
        for var in variables:
            if var in df.columns and pd.api.types.is_numeric_dtype(df[var]):
                numeric_vars.append(var)
        
        if len(numeric_vars) < 2:
            return {}
            
        corr_matrix = df[numeric_vars].corr()
        return corr_matrix.to_dict()
    except Exception as e:
        print(f"Warning: Could not calculate correlations: {e}")
        return {}

def _generate_linear_interpretation(model, variables, category_names, analysis_type):
    """Generate contextual interpretation for linear regression"""
    independent_vars = variables[:-1]
    dependent_var = variables[-1]
    
    dep_name = category_names.get(dependent_var, dependent_var.replace('_', ' ').title())
    
    interpretation = f"ANALISIS REGRESI LINEAR - {dep_name.upper()}\n\n"
    
    # Model significance
    try:
        f_pvalue = float(model.f_pvalue)
        if f_pvalue < 0.001:
            significance = "sangat signifikan (p < 0.001)"
        elif f_pvalue < 0.01:
            significance = "signifikan (p < 0.01)"
        elif f_pvalue < 0.05:
            significance = "cukup signifikan (p < 0.05)"
        else:
            significance = "tidak signifikan (p ≥ 0.05)"
        
        interpretation += f"🔍 SIGNIFIKANSI MODEL: Model secara keseluruhan {significance}\n\n"
    except:
        interpretation += f"🔍 SIGNIFIKANSI MODEL: Informasi signifikansi tidak tersedia\n\n"
    
    # R-squared interpretation
    try:
        r_sq_pct = float(model.rsquared) * 100
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
    except:
        interpretation += f"📊 KEKUATAN MODEL: Informasi R² tidak tersedia\n\n"
    
    # Coefficients interpretation
    interpretation += "📈 PENGARUH VARIABEL:\n"
    
    try:
        for i, var in enumerate(independent_vars):
            coef = float(model.params[i + 1])  # Skip intercept
            try:
                p_val = float(model.pvalues[i + 1])
                sig_available = True
            except:
                sig_available = False
            
            var_name = category_names.get(var, var.replace('_', ' ').title())
            
            # Significance of individual coefficient
            if sig_available and p_val < 0.05:
                sig_text = "signifikan"
                sig_symbol = "✓"
            elif sig_available:
                sig_text = "tidak signifikan"
                sig_symbol = "✗"
            else:
                sig_text = "signifikansi tidak diketahui"
                sig_symbol = "?"
            
            # Direction and magnitude
            if coef > 0:
                direction = "positif"
                effect = "meningkat"
            else:
                direction = "negatif" 
                effect = "menurun"
            
            interpretation += f"   {sig_symbol} {var_name}: Pengaruh {direction}"
            if sig_available:
                interpretation += f" ({sig_text})\n"
            else:
                interpretation += f"\n"
            interpretation += f"     → Setiap kenaikan 1 unit {var_name}, {dep_name} {effect} sebesar {abs(coef):.3f} unit\n"
    except Exception as e:
        interpretation += f"   Informasi koefisien tidak dapat diproses: {str(e)}\n"
    
    return interpretation

def _generate_polynomial_interpretation(model, variables, category_names, analysis_type, r_squared):
    """Generate contextual interpretation for polynomial regression"""
    independent_vars = variables[:-1]
    dependent_var = variables[-1]
    
    dep_name = category_names.get(dependent_var, dependent_var.replace('_', ' ').title())
    
    interpretation = f"ANALISIS REGRESI NON-LINEAR (POLYNOMIAL) - {dep_name.upper()}\n\n"
    
    # R-squared interpretation
    try:
        r_sq_pct = float(r_squared) * 100
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
    except:
        interpretation += f"📊 KEKUATAN MODEL: Informasi R² tidak tersedia\n\n"
    
    interpretation += "🔄 KARAKTERISTIK NON-LINEAR:\n"
    interpretation += f"   Model menangkap hubungan yang tidak linear antara variabel independen dan {dep_name}\n"
    interpretation += "   Hubungan ini menunjukkan adanya akselerasi atau deselerasi dalam pengaruh variabel\n\n"
    
    # Coefficient information
    try:
        interpretation += f"📈 KOEFISIEN MODEL:\n"
        interpretation += f"   Intercept: {float(model.intercept_):.3f}\n"
        for i, coef in enumerate(model.coef_):
            interpretation += f"   Koefisien {i+1}: {float(coef):.3f}\n"
    except Exception as e:
        interpretation += f"📈 KOEFISIEN MODEL: Informasi tidak dapat diproses: {str(e)}\n"
    
    return interpretation

def _generate_enhanced_summary(model, variables, category_names, analysis_type, regression_type, r_squared, cities):
    """Generate enhanced contextual summary"""
    independent_vars = variables[:-1]
    dependent_var = variables[-1]
    
    dep_name = category_names.get(dependent_var, dependent_var.replace('_', ' ').title())
    
    # Format city context based on single or multiple cities
    if len(cities) == 1:
        city_context = cities[0].replace("Kota ", "").replace("Kabupaten ", "")
        region_text = f"WILAYAH STUDI: {cities[0]}"
    else:
        city_context = f"{len(cities)} Wilayah"
        region_text = f"WILAYAH STUDI: {', '.join(cities)}"
    
    summary = f"RINGKASAN ANALISIS REGRESI - {city_context.upper()}\n"
    summary += "=" * 50 + "\n\n"
    
    # Analysis context
    if analysis_type == "single":
        indep_name = category_names.get(independent_vars[0], independent_vars[0].replace('_', ' ').title())
        summary += f"🎯 FOKUS ANALISIS: Hubungan {indep_name} terhadap {dep_name}\n"
    else:
        summary += f"🎯 FOKUS ANALISIS: Pengaruh multivariabel terhadap {dep_name}\n"
        indep_names = [category_names.get(v, v.replace('_', ' ').title()) for v in independent_vars]
        summary += f"   Variabel independen: {', '.join(indep_names)}\n"
    
    summary += f"📍 {region_text}\n"
    summary += f"📊 METODE: Regresi {'Linear' if regression_type == 'linear' else 'Non-Linear (Polynomial)'}\n\n"
    
    # Key findings
    try:
        r_sq_pct = float(r_squared) * 100
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
            try:
                f_pvalue = float(model.f_pvalue)
                if f_pvalue < 0.05:
                    summary += f"   ✅ Model secara statistik signifikan (p = {f_pvalue:.4f})\n"
                else:
                    summary += f"   ❌ Model secara statistik tidak signifikan (p = {f_pvalue:.4f})\n"
            except:
                pass
        
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
            
    except Exception as e:
        summary += f"🔍 TEMUAN UTAMA: Error dalam pemrosesan hasil: {str(e)}\n"
    
    return summary

def _prepare_multi_region_data(combined_df, variables, model, is_multi_region, y_pred=None):
    """Prepare data structure for multi-region analysis"""
    data = {
        "years": _safe_to_list(combined_df["year"]),
        "independent_values": {var: _safe_to_list(combined_df[var]) for var in variables[:-1]},
        "dependent_values": _safe_to_list(combined_df[variables[-1]]),
        "fitted_values": _safe_to_list(y_pred if y_pred is not None else model.fittedvalues),
    }
    
    if is_multi_region:
        data["regions"] = _safe_to_list(combined_df["region"])
        # Add residuals for linear regression
        if hasattr(model, 'resid'):
            data["residuals"] = _safe_to_list(model.resid)
    else:
        if hasattr(model, 'resid'):
            data["residuals"] = _safe_to_list(model.resid)
    
    return data

def _calculate_region_statistics(all_region_data, variables):
    """Calculate statistics for each region"""
    region_stats = {}
    
    for region, df in all_region_data.items():
        stats = {
            "data_points": len(df),
            "year_range": {
                "start": int(df["year"].min()) if not df["year"].empty else None,
                "end": int(df["year"].max()) if not df["year"].empty else None
            },
            "variable_means": {},
            "variable_std": {}
        }
        
        for var in variables:
            if var in df.columns:
                stats["variable_means"][var] = float(df[var].mean())
                stats["variable_std"][var] = float(df[var].std())
        
        region_stats[region] = stats
    
    return region_stats

def _generate_multi_region_linear_interpretation(model, variables, category_names, analysis_type, cities, all_region_data):
    """Generate interpretation for multi-region linear regression"""
    interpretation = []
    interpretation.append(f"ANALISIS REGRESI LINEAR MULTI-WILAYAH")
    interpretation.append(f"Wilayah yang dianalisis: {', '.join(cities)}")
    interpretation.append(f"Total data points: {sum(len(df) for df in all_region_data.values())}")
    interpretation.append("")
    
    # Model fit quality
    r_squared = float(model.rsquared)
    interpretation.append(f"Model Fit:")
    interpretation.append(f"- R-squared: {r_squared:.4f} ({r_squared*100:.1f}% variasi dijelaskan)")
    if r_squared >= 0.7:
        interpretation.append("- Model memiliki kemampuan prediksi yang baik")
    elif r_squared >= 0.5:
        interpretation.append("- Model memiliki kemampuan prediksi yang moderat")
    else:
        interpretation.append("- Model memiliki kemampuan prediksi yang terbatas")
    interpretation.append("")
    
    # Coefficients interpretation
    interpretation.append("Pengaruh Variabel:")
    coeffs = model.params
    p_values = model.pvalues
    
    for i, var in enumerate(variables[:-1]):
        var_name = category_names.get(var, var)
        coeff = coeffs[i+1]  # Skip intercept
        p_val = p_values[i+1]
        
        significance = "signifikan" if p_val < 0.05 else "tidak signifikan"
        direction = "positif" if coeff > 0 else "negatif"
        
        interpretation.append(f"- {var_name}: koefisien {coeff:.4f} ({direction}, {significance})")
        if p_val < 0.05:
            if analysis_type == "single":
                interpretation.append(f"  Setiap peningkatan 1 unit {var_name} meningkatkan {category_names.get(variables[-1], variables[-1])} sebesar {coeff:.4f}")
            else:
                interpretation.append(f"  Berkontribusi {direction} terhadap {category_names.get(variables[-1], variables[-1])}")
    
    interpretation.append("")
    interpretation.append("Perbandingan antar wilayah:")
    for region, df in all_region_data.items():
        mean_dep = df[variables[-1]].mean()
        interpretation.append(f"- {region}: rata-rata {category_names.get(variables[-1], variables[-1])} = {mean_dep:.2f}")
    
    return "\n".join(interpretation)

def _generate_multi_region_polynomial_interpretation(model, variables, category_names, analysis_type, r_squared, cities, all_region_data):
    """Generate interpretation for multi-region polynomial regression"""
    interpretation = []
    interpretation.append(f"ANALISIS REGRESI NON-LINEAR MULTI-WILAYAH")
    interpretation.append(f"Wilayah yang dianalisis: {', '.join(cities)}")
    interpretation.append(f"Total data points: {sum(len(df) for df in all_region_data.values())}")
    interpretation.append("")
    
    interpretation.append(f"Model Fit:")
    interpretation.append(f"- R-squared: {r_squared:.4f} ({r_squared*100:.1f}% variasi dijelaskan)")
    if r_squared >= 0.7:
        interpretation.append("- Model polynomial menunjukkan fit yang baik")
    elif r_squared >= 0.5:
        interpretation.append("- Model polynomial menunjukkan fit yang moderat")
    else:
        interpretation.append("- Model polynomial memiliki kemampuan prediksi terbatas")
    
    interpretation.append("")
    interpretation.append("Karakteristik hubungan non-linear:")
    interpretation.append("- Model mendeteksi pola kurvatur dalam hubungan antar variabel")
    interpretation.append("- Hubungan tidak mengikuti garis lurus sederhana")
    
    interpretation.append("")
    interpretation.append("Perbandingan antar wilayah:")
    for region, df in all_region_data.items():
        mean_dep = df[variables[-1]].mean()
        interpretation.append(f"- {region}: rata-rata {category_names.get(variables[-1], variables[-1])} = {mean_dep:.2f}")
    
    return "\n".join(interpretation)

def _generate_multi_region_summary(model, variables, category_names, analysis_type, regression_type, r_squared, cities, all_region_data):
    """Generate enhanced summary for multi-region analysis"""
    summary = []
    summary.append(f"RINGKASAN ANALISIS {regression_type.upper()} MULTI-WILAYAH")
    summary.append("="*60)
    summary.append("")
    
    summary.append(f"Wilayah: {', '.join(cities)}")
    summary.append(f"Jenis Analisis: {'Single Variable' if analysis_type == 'single' else 'Multi Variable'}")
    summary.append(f"Total Data Points: {sum(len(df) for df in all_region_data.values())}")
    summary.append("")
    
    summary.append("VARIABEL YANG DIANALISIS:")
    summary.append(f"Independen: {', '.join([category_names.get(v, v) for v in variables[:-1]])}")
    summary.append(f"Dependen: {category_names.get(variables[-1], variables[-1])}")
    summary.append("")
    
    summary.append("HASIL UTAMA:")
    summary.append(f"- R-squared: {r_squared:.4f} ({r_squared*100:.1f}%)")
    
    if hasattr(model, 'f_pvalue'):
        f_pval = float(model.f_pvalue)
        summary.append(f"- P-value model: {f_pval:.4f} ({'Signifikan' if f_pval < 0.05 else 'Tidak Signifikan'})")
    
    summary.append("")
    summary.append("PERBANDINGAN WILAYAH:")
    for region, df in all_region_data.items():
        summary.append(f"{region}:")
        summary.append(f"  - Data points: {len(df)}")
        summary.append(f"  - Periode: {int(df['year'].min())}-{int(df['year'].max())}")
        for var in variables:
            if var in df.columns:
                mean_val = df[var].mean()
                summary.append(f"  - Rata-rata {category_names.get(var, var)}: {mean_val:.2f}")
        summary.append("")
    
    return "\n".join(summary)

# Updated main regression analysis function with cities-only parameter
@app.route("/api/analysis", methods=["POST"])
def regression_analysis():
    try:
        data = request.get_json()
        
        # 1. Validate Input
        error_message, variables = _validate_request(data)
        if error_message:
            return jsonify({"error": error_message}), 400

        regression_type = data["regression_type"]
        analysis_type = data["analysis_type"]
        
        # Get cities parameter (required)
        cities = data.get("cities", [])
        
        if not cities or len(cities) == 0:
            return jsonify({"error": "Parameter 'cities' is required and must contain at least one city."}), 400
        
        # Determine if this is multi-region analysis based on cities count
        is_multi_region = len(cities) > 1
        
        # 2. Fetch and Prepare Data for all regions
        all_region_data = {}
        merged_dfs = []
        
        for region in cities:
            merged_df = _fetch_and_prepare_data(variables, region)
            if merged_df is None or merged_df.empty:
                continue
            
            # Add region column for multi-region analysis
            merged_df = merged_df.copy()
            merged_df['region'] = region
            all_region_data[region] = merged_df
            merged_dfs.append(merged_df)
        
        if not merged_dfs:
            return jsonify({"error": "No matching data found for any selected region."}), 404
        
        # Combine all region data for multi-region analysis
        if is_multi_region:
            combined_df = pd.concat(merged_dfs, ignore_index=True)
            if len(combined_df) < 2:
                return jsonify({"error": "Insufficient combined data for multi-region analysis."}), 404
        else:
            combined_df = merged_dfs[0]
        
        # 3. Prepare X and y variables
        X = combined_df[variables[:-1]].values
        y = combined_df[variables[-1]].values
        if analysis_type == "single" and not is_multi_region:
            X = X.reshape(-1, 1)

        # 4. Get category display names for better context
        category_names = _get_category_display_names(variables)

        # 5. Perform Regression & Build Results
        if regression_type == "linear":
            X_with_const = sm.add_constant(X)
            model = sm.OLS(y, X_with_const).fit()
            r_squared = float(model.rsquared)
            
            # Enhanced interpretation with multi-region context
            if is_multi_region:
                interpretation = _generate_multi_region_linear_interpretation(
                    model, variables, category_names, analysis_type, cities, all_region_data
                )
                summary = _generate_multi_region_summary(
                    model, variables, category_names, analysis_type, regression_type, 
                    r_squared, cities, all_region_data
                )
            else:
                interpretation = _generate_linear_interpretation(model, variables, category_names, analysis_type)
                summary = _generate_enhanced_summary(model, variables, category_names, analysis_type, regression_type, r_squared, cities)

            results = {
                "details": {
                    "r_squared": r_squared,
                    "coefficients": _safe_to_list(model.params),
                    "f_statistic": float(model.fvalue),
                    "f_pvalue": float(model.f_pvalue),
                    "p_values": _safe_to_list(model.pvalues),
                    "confidence_intervals": _safe_conf_int_to_list(model.conf_int()),
                    "interpretation": interpretation,
                    "data": _prepare_multi_region_data(combined_df, variables, model, is_multi_region),
                    "correlations": _calculate_correlations(combined_df, variables),
                    "region_statistics": _calculate_region_statistics(all_region_data, variables) if is_multi_region else None
                }
            }

        else:  # Non-linear regression (polynomial)
            from sklearn.preprocessing import PolynomialFeatures
            from sklearn.linear_model import LinearRegression
            from sklearn.metrics import r2_score
            
            poly = PolynomialFeatures(degree=2)
            X_poly = poly.fit_transform(X)
            model = LinearRegression().fit(X_poly, y)
            y_pred = model.predict(X_poly)
            r_squared = float(r2_score(y, y_pred))

            # Enhanced interpretation for polynomial regression with multi-region support
            if is_multi_region:
                interpretation = _generate_multi_region_polynomial_interpretation(
                    model, variables, category_names, analysis_type, r_squared, cities, all_region_data
                )
                summary = _generate_multi_region_summary(
                    model, variables, category_names, analysis_type, regression_type, 
                    r_squared, cities, all_region_data
                )
            else:
                interpretation = _generate_polynomial_interpretation(model, variables, category_names, analysis_type, r_squared)
                summary = _generate_enhanced_summary(model, variables, category_names, analysis_type, regression_type, r_squared, cities)

            results = {
                "details": {
                    "r_squared": r_squared,
                    "coefficients": _safe_to_list(model.coef_),
                    "intercept": float(model.intercept_),
                    "interpretation": interpretation,
                    "data": _prepare_multi_region_data(combined_df, variables, model, is_multi_region, y_pred=y_pred),
                    "correlations": _calculate_correlations(combined_df, variables),
                    "region_statistics": _calculate_region_statistics(all_region_data, variables) if is_multi_region else None
                }
            }
        
        # 6. Final JSON Response
        final_response = {
            "analysis_mode": "multi_region" if is_multi_region else "single_region",
            "regions": cities,
            "region_count": len(cities),
            "regression_type": regression_type,
            "analysis_type": analysis_type,
            "variables_analyzed": {
                "independent": variables[:-1],
                "dependent": variables[-1]
            },
            "category_names": category_names,
            "summary": summary,
            **results
        }

        return jsonify(final_response)

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": f"An internal error occurred: {str(e)}"}), 500

def _validate_request(data):
    """Validate request data and extract variables"""
    try:
        if not data:
            return "Request data is required", None
            
        # Updated required fields - removed 'city', kept only 'cities'
        required_fields = ["cities", "regression_type", "analysis_type"]
        for field in required_fields:
            if field not in data:
                return f"Missing required field: {field}", None
        
        # Validate cities parameter
        cities = data.get("cities", [])
        if not isinstance(cities, list) or len(cities) == 0:
            return "Parameter 'cities' must be a non-empty list", None
        
        if data["regression_type"] not in ["linear", "non_linear"]:
            return "Invalid regression_type. Must be 'linear' or 'non_linear'", None
            
        if data["analysis_type"] not in ["single", "multi"]:
            return "Invalid analysis_type. Must be 'single' or 'multi'", None
        
        if data["analysis_type"] == "single":
            if "independent_variable" not in data or "dependent_variable" not in data:
                return "Single analysis requires independent_variable and dependent_variable", None
            variables = [data["independent_variable"], data["dependent_variable"]]
        else:
            if "variables" not in data or len(data["variables"]) < 2:
                return "Multi analysis requires at least 2 variables", None
            variables = data["variables"]
        
        return None, variables
        
    except Exception as e:
        return f"Validation error: {str(e)}", None

    
@app.route("/predict", methods=["POST"])
def predict_values():
    """
    Endpoint for making predictions based on regression analysis.
    Supports both single-variable and multi-variable predictions.
    """
    try:
        data = request.get_json()
        city = data.get("city")
        analysis_type = data.get("analysis_type")
        # prediction_year = data.get("prediction_year")
        
        if not all([city, analysis_type]):
            return jsonify({
                "error": "Missing required parameters: city, analysis_type, prediction_year"
            }), 400

        results = {
            "city": city,
            # "prediction_year": prediction_year,
            "predictions": {}
        }

        if analysis_type == "single":
            independent_var = data.get("independent_variable")
            dependent_var = data.get("dependent_variable")
            independent_value = data.get("independent_value")

            if not all([independent_var, dependent_var, independent_value]):
                return jsonify({
                    "error": "For single prediction, independent_variable, dependent_variable, and independent_value are required"
                }), 400

            # Fetch historical data for the model
            independent_data = (
                db.session.query(Data.amount, Data.year)
                .join(Category)
                .filter(Category.name == independent_var.upper(), Data.city == city)
                .order_by(Data.year)
                .all()
            )

            dependent_data = (
                db.session.query(Data.amount, Data.year)
                .join(Category)
                .filter(Category.name == dependent_var.upper(), Data.city == city)
                .order_by(Data.year)
                .all()
            )

            df_independent = pd.DataFrame(independent_data, columns=["amount", "year"])
            df_dependent = pd.DataFrame(dependent_data, columns=["amount", "year"])

            merged_df = pd.merge(df_independent, df_dependent, on="year", suffixes=("_independent", "_dependent"))

            if merged_df.empty:
                return jsonify({"error": "Insufficient historical data for prediction"}), 404

            # Create and train the model
            X = merged_df["amount_independent"].values.reshape(-1, 1)
            y = merged_df["amount_dependent"].values
            
            model = LinearRegression()
            model.fit(X, y)

            # Make prediction
            predicted_value = model.predict([[float(independent_value)]])[0]

            results["predictions"] = {
                "independent_variable": {
                    "name": independent_var,
                    "value": independent_value
                },
                "dependent_variable": {
                    "name": dependent_var,
                    "predicted_value": float(predicted_value)
                },
                "confidence_metrics": {
                    "r_squared": float(model.score(X, y)),
                }
            }

        return jsonify(results)

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/export-custom-template', methods=['GET'])
def export_custom_template():
    """Membuat template kustom berdasarkan filter dari frontend."""
    try:
        regency_ids = request.args.getlist('regency_id', type=int)
        categories = request.args.getlist('category')
        start_year = request.args.get('start_year', type=int)
        end_year = request.args.get('end_year', type=int)

        if not all([regency_ids, categories, start_year, end_year]):
            return jsonify({"error": "Missing required filters"}), 400

        # Fetch regencies dengan province (gunakan joinedload untuk efisiensi)
        regencies = (
            db.session.query(Regency)
            .options(joinedload(Regency.province))
            .filter(Regency.id.in_(regency_ids))
            .all()
        )
        
        if not regencies:
            return jsonify({"error": "No valid regencies found"}), 400

        # Buat mapping untuk regency data
        regency_data = {
            r.id: {
                'regency_id': r.id,
                'regency_name': r.name,
                'province_id': r.province_id,
                'province_name': r.province.name if r.province else ''
            }
            for r in regencies
        }

        rows = []
        for regency_id in regency_ids:
            if regency_id not in regency_data:
                continue
                
            reg_info = regency_data[regency_id]
            for year in range(start_year, end_year + 1):
                for category in categories:
                    rows.append({
                        'province_id': reg_info['province_id'],
                        'province_name': reg_info['province_name'],
                        'regency_id': reg_info['regency_id'],
                        'regency_name': reg_info['regency_name'],
                        'year': year,
                        'category': category,
                        'amount': ''
                    })
        
        if not rows:
            return jsonify({"error": "No data to generate for the selected filters"}), 400

        # Buat DataFrame dengan urutan kolom yang rapi
        df = pd.DataFrame(rows, columns=[
            'province_id', 
            'province_name', 
            'regency_id', 
            'regency_name', 
            'year', 
            'category', 
            'amount'
        ])
        
        output = io.BytesIO()
        
        # Gunakan ExcelWriter untuk formatting yang lebih baik
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Data')
            
            # Optional: Auto-adjust column width
            worksheet = writer.sheets['Data']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = max_length
        
        output.seek(0)
        
        filename = f'template_data_{start_year}-{end_year}.xlsx'
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        app.logger.error(f"Template export failed: {e}")
        return jsonify({"error": "Failed to generate custom template."}), 500


@app.route('/api/upload', methods=['POST'])
def upload_excel():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.xlsx'):
        return jsonify({"error": "No selected file or invalid file type (.xlsx required)"}), 400

    try:
        # Baca Excel
        df = pd.read_excel(io.BytesIO(file.read()), engine='openpyxl')

        # Normalisasi nama kolom
        df.columns = df.columns.str.strip().str.lower()

        # Required columns - nama kolom hanya untuk referensi, bukan untuk penyimpanan
        required_columns = ['regency_id', 'province_id', 'year', 'amount', 'category']
        if not set(required_columns).issubset(df.columns):
            return jsonify({"error": f"Missing required columns: {', '.join(required_columns)}"}), 400

        # Anggap string kosong/whitespace sebagai NA
        df = df.replace(r'^\s*$', pd.NA, regex=True)

        # Bersihkan kolom string
        df['category'] = df['category'].astype('string').str.strip()

        # Pastikan numeric, yang tidak bisa dikonversi jadi NaN
        df['regency_id'] = pd.to_numeric(df['regency_id'], errors='coerce')
        df['province_id'] = pd.to_numeric(df['province_id'], errors='coerce')
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

        # Validasi per-baris: wajib terisi
        missing_mask = (
            df['regency_id'].isna() |
            df['province_id'].isna() |
            df['year'].isna() |
            df['amount'].isna() |
            df['category'].isna()
        )

        skipped_count = int(missing_mask.sum())
        valid_df = df.loc[~missing_mask].copy()

        # Jika tidak ada baris valid, hentikan
        if valid_df.empty:
            return jsonify({
                "error": "Tidak ada baris valid untuk diproses.",
                "skipped_rows": skipped_count
            }), 400

        # Validasi regency_id dan province_id ada di database
        regency_ids_in_file = valid_df['regency_id'].astype(int).unique().tolist()
        province_ids_in_file = valid_df['province_id'].astype(int).unique().tolist()

        existing_regencies = Regency.query.filter(Regency.id.in_(regency_ids_in_file)).all()
        existing_regency_ids = {r.id for r in existing_regencies}

        existing_provinces = Province.query.filter(Province.id.in_(province_ids_in_file)).all()
        existing_province_ids = {p.id for p in existing_provinces}

        # Filter baris dengan regency_id dan province_id yang valid
        invalid_location_mask = (
            ~valid_df['regency_id'].astype(int).isin(existing_regency_ids) |
            ~valid_df['province_id'].astype(int).isin(existing_province_ids)
        )
        
        invalid_location_count = int(invalid_location_mask.sum())
        valid_df = valid_df.loc[~invalid_location_mask].copy()

        if valid_df.empty:
            return jsonify({
                "error": "Tidak ada baris dengan regency_id atau province_id yang valid.",
                "skipped_rows": skipped_count + invalid_location_count
            }), 400

        # Kategori
        unique_categories = valid_df['category'].unique().tolist()
        existing_categories = Category.query.filter(Category.name.in_(unique_categories)).all()
        existing_categories_map = {cat.name: cat.id for cat in existing_categories}

        new_category_names = [name for name in unique_categories if name not in existing_categories_map]
        if new_category_names:
            new_categories_obj = [Category(name=name) for name in new_category_names]
            db.session.bulk_save_objects(new_categories_obj, return_defaults=True)
            db.session.commit()
            for cat in new_categories_obj:
                existing_categories_map[cat.name] = cat.id

        # Data eksisting yang relevan
        regency_ids = valid_df['regency_id'].astype(int).unique().tolist()
        years_in_file = valid_df['year'].astype(int).unique().tolist()

        existing_data = (
            db.session.query(Data)
            .options(joinedload(Data.category))
            .filter(
                Data.regency_id.in_(regency_ids),
                Data.year.in_(years_in_file),
                Data.category_id.in_(existing_categories_map.values())
            )
            .all()
        )

        # Peta eksisting: gunakan tuple key agar aman
        existing_data_map = {(d.regency_id, d.year, d.category.name): d for d in existing_data}

        # Siapkan update/insert
        to_update = []
        to_insert = []

        for _, row in valid_df.iterrows():
            key = (int(row['regency_id']), int(row['year']), row['category'])
            if key in existing_data_map:
                existing_record = existing_data_map[key]
                to_update.append({
                    'id': existing_record.id,
                    'amount': float(row['amount'])
                })
            else:
                to_insert.append(
                    Data(
                        regency_id=int(row['regency_id']),
                        province_id=int(row['province_id']),
                        year=int(row['year']),
                        amount=float(row['amount']),
                        category_id=existing_categories_map[row['category']]
                    )
                )

        if to_update:
            db.session.bulk_update_mappings(Data, to_update)
        if to_insert:
            db.session.bulk_save_objects(to_insert)

        db.session.commit()

        total_skipped = skipped_count + invalid_location_count
        message = (
            f"Upload complete. {len(to_insert)} records inserted, "
            f"{len(to_update)} records updated, {total_skipped} rows skipped."
        )

        # Opsional: contoh baris yang di-skip (maks 5) untuk debugging
        skipped_examples = []
        if skipped_count > 0:
            sample = df.loc[missing_mask, required_columns].head(5).copy()
            sample = sample.assign(row=lambda x: x.index)
            skipped_examples = sample.to_dict(orient='records')

        return jsonify({
            "message": message,
            "inserted": len(to_insert),
            "updated": len(to_update),
            "skipped_rows": total_skipped,
            "skipped_examples": skipped_examples
        }), 200

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Upload failed: {e}")
        return jsonify({"error": "An internal error occurred during file processing."}), 500

# --- Ambil provinsi berdasarkan tahun ---
@app.route("/api/provinsi", methods=["GET"])
def get_provinsi():
    data = request.get_json()
    tahun = data.get("tahun")

    if not tahun:
        return jsonify({"error": "Parameter 'tahun' wajib ada"}), 400

    url = f"{os.getenv('BASE_URL')}/provinsi/{tahun}"
    resp = requests.get(url)

    if resp.status_code != 200:
        return jsonify({"error": "Gagal mengambil data provinsi"}), 500

    return jsonify(resp.json())


# --- Ambil pemda berdasarkan provinsi & tahun ---
@app.route("/api/pemda", methods=["GET"])
def get_pemda():
    data = request.get_json()
    provinsi_id = data.get("provinsi_id")
    tahun = data.get("tahun")

    if not provinsi_id or not tahun:
        return jsonify({"error": "Parameter 'provinsi_id' dan 'tahun' wajib ada"}), 400

    url = f"{os.getenv('BASE_URL')}/pemda/{provinsi_id}/{tahun}"
    resp = requests.get(url)

    if resp.status_code != 200:
        return jsonify({"error": "Gagal mengambil data pemda"}), 500

    return jsonify(resp.json())

@app.route("/api/scrape-apbd", methods=["POST"])
def scrape_apbd_api():
    """
    Body JSON:
    {
        "start_year": 2020,
        "end_year": 2022,
        "periode": 1,
        "provinsi": "Daerah Istimewa Yogyakarta",
        "pemda_code": "34.71",
        "category_id": 12
    }
    """
    try:
        data = request.get_json()

        start_year = data.get("start_year")
        end_year = data.get("end_year")
        periode = data.get("periode") 
        provinsi = data.get("provinsi")
        pemda_code = data.get("pemda_code")
        category_id = data.get("category_id")

        if not all([start_year, end_year, periode, provinsi, pemda_code, category_id]):
            return jsonify({"error": "Parameter wajib harus diisi"}), 400

        keyword_row = helper.get_category_keywords().get(category_id)
        pemda_name = helper.get_pemda_names().get(pemda_code, None)


        if not keyword_row:
            return jsonify({"error": "Category tidak valid atau belum terdaftar"}), 400

        all_data = []
        for year in range(int(start_year), int(end_year)+1):
            try:
                df_list = apbd.scrape_apbd(
                    periode, year, provinsi, pemda_code, pemda_name=pemda_name,
                    keyword_row=keyword_row
                )
                if df_list:
                    all_data.extend(df_list)
            except Exception as e:
                print(f"❌ Gagal scrape tahun {year}: {e}")

        if not all_data:
            return jsonify({"message": "Data tidak ditemukan"}), 404

        # simpan ke database dengan insert or update
        saved_data = []
        for row in all_data:
            amount = row.get("anggaran/pagu") or row.get("amount")
            if amount is not None:
                # konversi string ke float, contoh '1.885,42 M' => 1885420000
                amount = helper.parse_amount(amount)

            city = row.get("pemda_name") or row.get("pemda")
            year_row = row.get("tahun") or year

            # cek apakah data sudah ada
            existing = Data.query.filter_by(
                year=year_row,
                province_id=provinsi,
                regency_id=pemda_code,
                category_id=category_id
            ).first()

            if existing:
                existing.amount = amount  # update jika ada
                db.session.add(existing)
                saved_data.append(existing)
            else:
                data_entry = Data(
                    amount=amount,
                    year=year_row,
                    city=city,
                    category_id=category_id,
                    province_id=provinsi,
                    regency_id=pemda_code
                )
                db.session.add(data_entry)
                saved_data.append(data_entry)

        db.session.commit()

        return jsonify({"data": [d.json() for d in saved_data]}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API endpoints for provinces and regencies
@app.route("/api/provinces", methods=["GET"])
def get_provinces():
    """
    Get all provinces data
    Returns list of provinces with their codes and names
    """
    try:
        provinces, regencies = get_latest_provinces_regencies_data()

        if not provinces:
            return jsonify({"error": "Failed to fetch provinces data"}), 500

        return jsonify({
            "message": "Provinces data retrieved successfully",
            "data": provinces,
            "count": len(provinces)
        }), 200

    except Exception as e:
        logging.error(f"Error in get_provinces endpoint: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route("/api/regencies", methods=["GET"])
def get_regencies():
    """
    Get regencies data for a specific province
    Query parameters:
    - province_id: Province ID (required)
    Returns list of regencies for the specified province
    """
    try:
        province_id = request.args.get("province_id")

        if not province_id:
            return jsonify({"error": "Parameter 'province_id' is required"}), 400

        # Validate province exists
        province = Province.query.filter_by(id=province_id).first()
        if not province:
            return jsonify({"error": f"Province with id {province_id} not found"}), 404

        # Get regencies for the province
        regencies = Regency.query.filter_by(province_id=province_id).all()

        # Convert to dict
        regencies_data = [{
            "id": r.id,
            "province_id": r.province_id,
            "name": r.name,
            "province_bps_code": r.province_bps_code,
            "province_kemenkeu_code": r.province_kemenkeu_code,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        } for r in regencies]

        return jsonify({
            "message": f"Regencies data for province {province_id} retrieved successfully",
            "province_id": province_id,
            "province_name": province.name,
            "data": regencies_data,
            "count": len(regencies_data)
        }), 200

    except Exception as e:
        logging.error(f"Error in get_regencies endpoint: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route("/api/provinces-regencies", methods=["GET"])
def get_provinces_with_regencies():
    """
    Get all provinces with their regencies
    Returns complete data structure with provinces and their associated regencies
    """
    try:
        # Get all provinces
        provinces = Province.query.all()

        if not provinces:
            return jsonify({
                "message": "No provinces found",
                "data": [],
                "summary": {
                    "total_provinces": 0,
                    "total_regencies": 0
                }
            }), 200

        # Build response with provinces and their regencies
        provinces_data = []
        total_regencies = 0

        for province in provinces:
            # Get regencies for this province
            regencies = Regency.query.filter_by(province_id=province.id).all()
            
            regencies_data = [{
                "id": r.id,
                "province_id": r.province_id,
                "name": r.name,
                "province_bps_code": r.province_bps_code,
                "province_kemenkeu_code": r.province_kemenkeu_code,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            } for r in regencies]

            provinces_data.append({
                "id": province.id,
                "name": province.name,
                "bps_code": province.bps_code,
                "kemenkeu_code": province.kemenkeu_code,
                "created_at": province.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": province.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                "regencies": regencies_data,
                "regencies_count": len(regencies_data)
            })

            total_regencies += len(regencies_data)

        return jsonify({
            "message": "Provinces and regencies data retrieved successfully",
            "data": provinces_data,
            "summary": {
                "total_provinces": len(provinces_data),
                "total_regencies": total_regencies
            }
        }), 200

    except Exception as e:
        logging.error(f"Error in get_provinces_with_regencies endpoint: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route("/api/scrape-provinces-regencies", methods=["POST"])
def scrape_provinces_regencies():
    """
    Manually trigger scraping of provinces and regencies data
    This endpoint can be used to refresh the data from BPS API
    """
    try:
        provinces, regencies = get_latest_provinces_regencies_data()

        if not provinces or not regencies:
            return jsonify({"error": "Failed to scrape provinces and regencies data"}), 500

        return jsonify({
            "message": "Provinces and regencies data scraped successfully",
            "data": {
                "provinces": provinces,
                "regencies": regencies
            },
            "summary": {
                "total_provinces": len(provinces),
                "total_regencies": len(regencies)
            }
        }), 200

    except Exception as e:
        logging.error(f"Error in scrape_provinces_regencies endpoint: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


# Database-based endpoints for provinces and regencies
@app.route("/api/provinces-db", methods=["GET"])
def get_provinces_from_db():
    """
    Get all provinces data from database
    Returns list of provinces with their codes and names from database
    """
    try:
        from scraping.provinces_regencies_fixed import get_provinces_from_db as get_provinces_db_func

        provinces = get_provinces_db_func()

        if not provinces:
            return jsonify({"error": "No provinces data found in database"}), 404

        return jsonify({
            "message": "Provinces data retrieved from database successfully",
            "data": provinces,
            "count": len(provinces)
        }), 200

    except Exception as e:
        logging.error(f"Error in get_provinces_from_db endpoint: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route("/api/regencies-db", methods=["GET"])
def get_regencies_from_db():
    """
    Get regencies data from database
    Query parameters:
    - province_id: Province code (optional)
    Returns list of regencies from database
    """
    try:
        from scraping.provinces_regencies_fixed import get_regencies_from_db as get_regencies_db_func

        province_id = request.args.get("province_id")

        regencies = get_regencies_db_func(province_id)

        if not regencies:
            return jsonify({"error": "No regencies data found in database"}), 404

        return jsonify({
            "message": "Regencies data retrieved from database successfully",
            "province_id": province_id,
            "data": regencies,
            "count": len(regencies)
        }), 200

    except Exception as e:
        logging.error(f"Error in get_regencies_from_db endpoint: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@app.route("/api/provinces-regencies-db", methods=["GET"])
def get_provinces_with_regencies_from_db():
    """
    Get all provinces with their regencies from database
    Returns complete data structure with provinces and their associated regencies from database
    """
    try:
        from scraping.provinces_regencies_fixed import get_provinces_from_db as get_provinces_db_func

        provinces = get_provinces_db_func()

        if not provinces:
            return jsonify({"error": "No provinces and regencies data found in database"}), 404

        # Calculate total regencies
        total_regencies = sum(len(province.get("regencies", [])) for province in provinces)

        return jsonify({
            "message": "Provinces and regencies data retrieved from database successfully",
            "data": provinces,
            "summary": {
                "total_provinces": len(provinces),
                "total_regencies": total_regencies
            }
        }), 200

    except Exception as e:
        logging.error(f"Error in get_provinces_with_regencies_from_db endpoint: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
@app.route("/")
def hello_world():
    return "Hello World!"


if __name__ == "__main__":
    app.run(debug=True)

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
import numpy as np
from sqlalchemy import inspect
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column
import pymysql
import os
from io import BytesIO
import logging
import pandas as pd
from flask_migrate import Migrate
import statsmodels.api as sm
from models import db, Data, Category, APBD, Stunting
import datetime
import openpyxl
from scipy import stats
from scraping import jumlah_angkatan_bekerja, pdrb, scraping_bps, stunting, indeks_gini, tingkat_partisipasi
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import io


app = Flask(__name__)
CORS(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://admin:admin@localhost:3304/data_policy"
# app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://akmal_user:tiumy@JOGJACODE5d@localhost:3306/data_policy"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["FILE_FOLDER"] = "files/"  # Direktori penyimpanan file
os.makedirs(app.config["FILE_FOLDER"],exist_ok=True)  # Buat direktori jika belum ada
logging.basicConfig(level=logging.DEBUG)

db.init_app(app)
migrate = Migrate(app, db)
# class StuntingData(db.Model):
#     __tablename__ = 'stunting'
#     id = db.Column(db.Integer, primary_key=True)
#     year = db.Column(db.Integer, nullable=False)
#     city = db.Column(db.String(255), nullable=False)
#     prevalence = db.Column(db.String(255), nullable=False)


# class Category(db.Model):
#     __tablename__ = "categories"
#     id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
#     name: Mapped[str] = mapped_column(nullable=True)
#     created_at: Mapped[str] = mapped_column(default=datetime.datetime.now)
#     data = db.relationship("Data", back_populates="category")

#     def json(self):
#         return {"id": self.id, "name": self.name, "created_at": self.created_at}


# class Data(db.Model):
#     __tablename__ = "data"
#     id = db.Column(db.Integer, primary_key=True)
#     amount = db.Column(db.Float, nullable=True)
#     year = db.Column(db.Integer, nullable=True)
#     city = db.Column(db.String, nullable=True)
#     category = db.relationship("Category", back_populates="data")
#     category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))

#     def json(self):
#         return {
#             "id": self.id,
#             "amount": self.amount,
#             "year": self.year,
#             "city": self.city,
#             "category": self.category.json() if self.category else None,
#             "category_id": self.category_id,
#         }


# class APBD(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     city = db.Column(db.String(100), nullable=False)
#     type = db.Column(db.String(50), nullable=False)
#     year = db.Column(db.Integer, nullable=False)
#     amount = db.Column(db.Float, nullable=False)
#     file_path = db.Column(
#         db.String(200), nullable=True
#     )  # Tambahkan kolom untuk jalur file

#     def to_dict(self):
#         return {
#             "id": self.id,
#             "city": self.city,
#             "type": self.type,
#             "year": self.year,
#             "amount": self.amount,
#             "file_path": self.file_path,  # Sertakan jalur file dalam output
#         }


# class Stunting(db.Model):
#     __tablename__ = "stuntings"
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     year = db.Column(db.Integer, nullable=False)
#     city = db.Column(db.String(100), nullable=False)
#     prevalence = db.Column(db.Float, nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.datetime.now)

#     def json(self):
#         return {
#             "id": self.id,
#             "year": self.year,
#             "city": self.city,
#             "prevalence": self.prevalence,
#             "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
#         }

@app.route("/fetch_data", methods=["POST"])
def fetch_data_api():
    try:
        body = request.get_json()
        if not body:
            return jsonify({"error": "No JSON data provided"}), 400

        vervar = body.get("wilayah")
        var = body.get("jenis_data")
        th = body.get("tahun")

        # Debugging logs
        print(f"Received data: wilayah={vervar}, jenis_data={var}, tahun={th}")

        # Validate required parameters
        # if not all([vervar, var, th]):
        #     return jsonify({"error": "Missing required parameters: vervar, var, th"}), 400

        # # Mapping th to actual years in the database
        # year_mapping = {121: 2021, 122: 2022, 123: 2023, 124: 2024}
        # actual_year = year_mapping.get(th)
        # if not actual_year:
        #     return jsonify({"error": f"Invalid year code provided: {th}"}), 400

        # # Allowed vervar values
        # allowed_vervars = {
        #     3401 : "Kulon Progo",
        #     3471: "Kota Yogyakarta",
        #     3578: "Kota Surabaya",
        #     3510: "Banyuwangi",
        #     3273: "Kota Bandung"
        # }
        # actual_city = allowed_vervars.get(vervar)

        # if vervar not in allowed_vervars:
        #     return jsonify({"error": f"Invalid wilayah code provided: {vervar}"}), 400

        # # Debugging log for valid vervar and year
        # print(f"Valid wilayah: {allowed_vervars[vervar]}, year: {actual_year}")

        # Check if data already exists in the database
        # existing_data = Data.query.filter_by(
        #     year=actual_year,
        #     city=actual_city  
        # ).first()

        # if existing_data:
        #     return jsonify({
        #         "message": "Data already exists",
        #     }), 400

        # Fetch new data using the scraping function
        data = scraping_bps.fetch_data(vervar, var, th)
        print(f"Fetched data: {data}")

        if not data:
            return jsonify({"error": "No data found or failed to fetch data"}), 404

        # Determine category based on var
        if var == "413":
            category = 1
        elif var == "619":
            category = 2
        elif var == "621":
            category = 5
        elif var == "414":
            category = 6

        # Insert fetched data into the database
        for new_data in data:
            entry = Data(
                amount=new_data['data'],
                city=new_data['wilayah'],
                year=new_data['tahun'],
                category_id=category,
            )
            db.session.add(entry)
        db.session.commit()

        # Debugging log for successful commit
        print("Data successfully saved to the database.")

        return jsonify({"message": "Data successfully added", "data": entry.json()}), 200

    except Exception as e:
        # Debugging log for errors
        print(f"An error occurred: {str(e)}")
        return jsonify({"error": "An internal error occurred", "details": str(e)}), 500

@app.route('/api/indeks-gini', methods=['POST'])
def fetch_and_save_bps_data():
    try:
        # Ambil parameter dari query string
        body = request.get_json()
        var = body.get("jenis_data")
        tahun = body.get("tahun")
        vervar_label = body.get("wilayah")

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
                    category_id=10  # Sesuaikan dengan kategori yang sesuai
                )
                db.session.add(new_data)

        db.session.commit()

        return jsonify({"message": "Data berhasil diambil dan disimpan", "data": new_data.json()}), 200

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

        return jsonify({"message": "Data berhasil diambil dan disimpan", "data": new_data.json()}), 200

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

        # Simpan data ke database
        for item in bps_data:
            # Cek apakah data sudah ada di database
            existing_data = Data.query.filter_by(
                year=item["tahun"],
                city=item["wilayah"],
                category_id=8  # Gunakan category_id jika ini adalah foreign key
            ).first()

            if existing_data:
                return jsonify({
                    "messsage": "Data Already exist"
                }), 400
            else:
                # Jika data belum ada, buat entri baru
                new_data = Data(
                    amount=item["data"],
                    year=item["tahun"],
                    city=item["wilayah"],
                    category_id=8  # Sesuaikan dengan kategori yang sesuai
                )
                db.session.add(new_data)

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


@app.route("/api/data", methods=["GET"])
def get_data():
    city = request.args.get("city")
    category_id = request.args.get("category_id")

    query = Data.query

    if city:
        query = query.filter(Data.city == city)
    if category_id:
        query = query.filter(Data.category_id == category_id)

    data = query.order_by(Data.year).all()
    return jsonify([item.json() for item in data])


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
        )

        existing_data = Data.query.filter_by(
            year=new_data.year,
            city=new_data.city,
            category_id=new_data.category_id,
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

        db.session.commit()
        return jsonify(data.json())
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
    categories = Category.query.order_by(Category.name.asc()).all()
    return jsonify([category.json() for category in categories])

@app.route('/api/categories/<int:id>', methods=['GET'])
def get_category(id):
    category = Category.query.get_or_404(id)
    return jsonify(category.json())

@app.route('/api/categories', methods=['POST'])
def create_category():
    data = request.get_json()
    new_category = Category(name=data.get('name'))
    db.session.add(new_category)
    db.session.commit()
    return jsonify(new_category.json()), 201

@app.route('/api/categories/<int:id>', methods=['PUT'])
def update_category(id):
    category = Category.query.get_or_404(id)
    data = request.get_json()
    category.name = data.get('name', category.name)
    db.session.commit()
    return jsonify(category.json())

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


@app.route("/analysis", methods=["POST"])
def regression_analysis():
    try:
        data = request.get_json()
        regression_type = data.get("regression_type")  # 'linear' or 'non_linear'
        city = data.get("city")
        analysis_type = data.get("analysis_type")  # 'single' or 'multi'

        # Validate required parameters
        if not all([regression_type, city, analysis_type]):
            return jsonify({
                "error": "Missing required parameters: regression_type, city, and analysis_type"
            }), 400

        # Validate regression type
        if regression_type not in ["linear", "non_linear"]:
            return jsonify({
                "error": "Invalid regression type. Must be 'linear' or 'non_linear'"
            }), 400

        # Process based on analysis type
        if analysis_type == "single":
            independent_var = data.get("independent_variable")
            dependent_var = data.get("dependent_variable")
            if not independent_var or not dependent_var:
                return jsonify({
                    "error": "For single analysis, both independent_variable and dependent_variable are required"
                }), 400
            variables = [independent_var, dependent_var]
        else:
            variables = data.get("variables", [])
            if len(variables) < 2:
                return jsonify({
                    "error": "For multi analysis, at least 2 variables are required"
                }), 400

        # Fetch and prepare data
        data_frames = []
        for var in variables:
            var_data = (
                db.session.query(Data.amount, Data.year, Data.city)
                .join(Category)
                .filter(Category.name == var, Data.city == city)
                .order_by(Data.year)
                .all()
            )
            df = pd.DataFrame(var_data, columns=["amount", "year", "city"])
            df = df.rename(columns={"amount": var})
            data_frames.append(df)

        # Merge data frames
        merged_df = data_frames[0]
        for df in data_frames[1:]:
            merged_df = pd.merge(merged_df, df, on=["year", "city"])

        if merged_df.empty:
            return jsonify({"error": "No matching data found for the selected variables"}), 404

        # Prepare dependent and independent variables
        if analysis_type == "single":
            X = merged_df[variables[0]].values.reshape(-1, 1)
            y = merged_df[variables[1]].values
        else:
            X = merged_df[variables[:-1]].values
            y = merged_df[variables[-1]].values

        # Perform regression based on type
        if regression_type == "linear":
            # Linear regression analysis
            X_with_const = sm.add_constant(X)
            model = sm.OLS(y, X_with_const).fit()

            # Generate interpretation for linear regression
            interpretation = f"""
            Analisis regresi linear menunjukkan:

            1. Model Linear:
            - R-squared: {model.rsquared:.2f}
            - Intercept: {model.params[0]:.2f}
            - Koefisien: {', '.join([f'{coef:.2f}' for coef in model.params[1:]])}

            2. Signifikansi:
            - F-statistic: {model.fvalue:.2f}
            - Prob (F-statistic): {model.f_pvalue:.3f}
            """

            results = {
                "city": city,
                "regression_type": regression_type,
                "analysis_type": analysis_type,
                "summary": "",
                "details": {
                    "r_squared": float(model.rsquared),
                    "coefficients": model.params.tolist(),
                    "f_statistic": float(model.fvalue),
                    "f_pvalue": float(model.f_pvalue),
                    "interpretation": interpretation.strip(),
                    "data": {
                        "years": merged_df["year"].tolist(),
                        "independent_values": merged_df[variables[0]].tolist(),  # Array, bukan objek
                        "dependent_values": merged_df[variables[1]].tolist(),
                        "fitted_values": model.fittedvalues.tolist(),
                        "residuals": model.resid.tolist()
                    }
                }
            }

        else:  # non_linear regression
            # Fit polynomial regression (degree=2 as example)
            poly = PolynomialFeatures(degree=2)
            X_poly = poly.fit_transform(X)
            poly_model = LinearRegression()
            poly_model.fit(X_poly, y)
            y_pred = poly_model.predict(X_poly)

            # Calculate R-squared for polynomial fit
            r_squared = r2_score(y, y_pred)

            interpretation = f"""
            Analisis regresi non-linear (polynomial) menunjukkan:

            Kualitas Model:
            - R-squared: {r_squared:.2f}
            - Koefisien polynomial: {', '.join([f'{coef:.2f}' for coef in poly_model.coef_])}
            - Intercept: {poly_model.intercept_:.2f}

            Interpretasi:
            - Model menunjukkan hubungan non-linear antara variabel
            - {r_squared * 100:.1f}% variasi dalam data dapat dijelaskan oleh model polynomial
            """

            results = {
                "city": city,
                "regression_type": regression_type,
                "analysis_type": analysis_type,
                "summary": "",
                "details": {
                    "r_squared": float(r_squared),
                    "coefficients": poly_model.coef_.tolist(),
                    "intercept": float(poly_model.intercept_),
                    "interpretation": interpretation.strip(),
                    "data": {
                        "years": merged_df["year"].tolist(),
                        "independent_values": merged_df[variables[0]].tolist(),  # Array, bukan objek
                        "dependent_values": merged_df[variables[1]].tolist(),
                        "fitted_values": y_pred.tolist()
                    }
                }
            }

        return jsonify(results)

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    
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
    
@app.route('/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.endswith('.csv'):
        filepath = os.path.join(app.config['FILE_FOLDER'], file.filename)
        file.save(filepath)

        try:
            # Baca file CSV
            df = pd.read_csv(filepath)

            # Validasi kolom
            required_columns = ['city', 'year', 'amount', 'category']
            if not all(column in df.columns for column in required_columns):
                return jsonify({"error": "CSV file must contain columns: city, year, amount, category"}), 400

            # Simpan data ke database
            for _, row in df.iterrows():
                category_name = row['category']
                category = Category.query.filter_by(name=category_name).first()

                # Jika kategori tidak ada, buat kategori baru
                if not category:
                    category = Category(name=category_name)
                    db.session.add(category)
                    db.session.flush()  # Untuk mendapatkan ID kategori yang baru dibuat

                new_data = Data(
                    city=row['city'],
                    year=row['year'],
                    amount=row['amount'],
                    category_id=category.id
                )
                db.session.add(new_data)

            db.session.commit()
            return jsonify({"message": "Data imported successfully"}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    else:
        return jsonify({"error": "Invalid file type. Please upload a CSV file"}), 400

@app.route('/api/export-template', methods=['GET'])
def export_template():
    try:
        # Definisikan kolom-kolom template
        columns = ['city', 'year', 'amount', 'category']

        # Buat DataFrame kosong dengan kolom yang telah ditentukan
        df = pd.DataFrame(columns=columns)

        # Buat file CSV dalam memory
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)

        # Kirim file CSV sebagai response
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='template.csv'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/")
def hello_world():
    return "Hello World!"


if __name__ == "__main__":
    app.run(debug=True)

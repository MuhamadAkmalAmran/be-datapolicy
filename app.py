from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column
import pymysql
import os
import logging
import pandas as pd
import statsmodels.api as sm
import datetime
from scipy import stats
from scraping import scraping_bps, stunting


app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = "mysql+pymysql://admin:admin@localhost:3304/data_policy" 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['FILE_FOLDER'] = 'files/'  # Direktori penyimpanan file
os.makedirs(app.config['FILE_FOLDER'], exist_ok=True)  # Buat direktori jika belum ada
# logging.basicConfig(level=logging.DEBUG)

db = SQLAlchemy(app)

# class StuntingData(db.Model):
#     __tablename__ = 'stunting'
#     id = db.Column(db.Integer, primary_key=True)
#     year = db.Column(db.Integer, nullable=False)
#     city = db.Column(db.String(255), nullable=False)
#     prevalence = db.Column(db.String(255), nullable=False)

class Category(db.Model):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[str] = mapped_column(default=datetime.datetime.now)
    data = db.relationship("Data", back_populates="category")
    
    def json(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at 
        }
        
class Data(db.Model):
    __tablename__ = 'data'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=True)
    year = db.Column(db.Integer, nullable=True)
    city = db.Column(db.String, nullable=True)
    category = db.relationship("Category", back_populates="data")
    category_id  = db.Column(db.Integer, db.ForeignKey("categories.id"))
    
    def json(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'year': self.year,
            'city': self.city,
            'category': self.category.json() if self.category else None,
            'category_id': self.category_id
        }

   
        
class APBD(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    file_path = db.Column(db.String(200), nullable=True)  # Tambahkan kolom untuk jalur file

    def to_dict(self):
        return {
            'id': self.id,
            'city': self.city,
            'type': self.type,
            'year': self.year,
            'amount': self.amount,
            'file_path': self.file_path  # Sertakan jalur file dalam output
        }


class Stunting(db.Model):
    __tablename__ ='stuntings'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    prevalence = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
    
    def json(self):
        return {
            'id': self.id,
            'year': self.year,
            'city': self.city,
            'prevalence': self.prevalence,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }


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
        category = 1 if var == "413" else 2

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
    

@app.route('/stunting', methods=['GET'])
def list_stunting():
    year = request.args.get('year')
    city = request.args.get('city')
    
    query = Stunting.query
    
    if year:
        query = query.filter_by(year=year)
    if city:
        query = query.filter_by(city=city)
        
    data = query.all()
    return jsonify([item.json() for item in data]), 200

@app.route('/stunting', methods=['POST'])
def scrape_endpoint():
    data = request.get_json()
    kab_kota = data.get('kab_kota')
    year = data.get('year')

    if not all([year, kab_kota]):
        return jsonify({"error": "Please provide year and kabupaten_kota parameters."}), 400

    # Determine provinsi based on kabupaten_kota
    if kab_kota in ["Kota Yogyakarta", "Kulon Progo"]:
        provinsi = "DI YOGYAKARTA"
    elif kab_kota in ["Kota Surabaya", "Banyuwangi"]:
        provinsi = "JAWA TIMUR"
    elif kab_kota == "Kota Bandung":
        provinsi = "JAWA BARAT"
    else:
        return jsonify({"error": "Unable to determine provinsi for the provided kabupaten_kota."}), 400
    
    existing_data = Data.query.filter_by(
            year=year,
            city=kab_kota,
            category_id=3
        ).first()

    if existing_data:
        return jsonify({
            "message": "Data already exists",
        }), 400
        
    # driver = stunting.init_driver()
    scraped_data = stunting.scrape_data(year, provinsi, kab_kota)

    # Save data to database
    for record in scraped_data:
        entry = Data(year=record['year'], city=record['city'], amount=record['amount'], category_id=3)
        db.session.add(entry)
    db.session.commit()

    return jsonify(entry.json())

@app.route("/apbd", methods=["POST"])
def create_apbd():
    data = request.form  # Gunakan request.form untuk mengambil data teks
    file = request.files.get('file')  # Ambil file dari request
    
    # Simpan file jika ada
    file_path = None
    if file:
        file_name = file.filename
        file_path = os.path.join(app.config['FILE_FOLDER'], file_name)
        file.save(file_path)  # Simpan file ke direktori

    # Buat objek APBD baru
    new_apbd = APBD(
        city=data.get('city'),
        type=data.get('type'),
        year=data.get('year'),
        amount=data.get('amount'),
        file_path=file_path  # Simpan jalur file ke database
    )
    
    # Tambahkan ke database
    db.session.add(new_apbd)
    db.session.commit()
    
    return jsonify({'message': 'APBD created', 'data': new_apbd.to_dict()}), 201

@app.route('/analysis', methods=['POST'])
def regression_analysis():
    """
    Enhanced regression analysis between APBD and selected dependent variables.
    Returns correlation statistics, regression results, and diagnostic information.
    """
    try:
        data = request.get_json()
        region = data.get('region')
        analysis_type = data.get('analysis_type')  # 'single' or 'multi'
        dependent_vars = data.get('dependent_variables', [])  # List of dependent variables

        if not region or not analysis_type or not dependent_vars:
            return jsonify({
                'error': 'Missing required parameters: region, analysis_type, and dependent_variables'
            }), 400

        # Fetch APBD data (independent variable)
        apbd_data = (
            db.session.query(
                APBD.amount,
                APBD.year,
                APBD.city,
                # APBD.type,
            )
            .filter(APBD.city == region)
            .all()
        )

        results = {}
        
        for dependent_var in dependent_vars:
            # Fetch dependent variable data
            var_data = (
                db.session.query(
                    Data.amount,
                    Data.year,
                    Data.city
                )
                .join(Category)
                .filter(
                    Category.name == dependent_var,
                    Data.city == region
                )
                .all()
            )

            # Create pandas DataFrames
            df_apbd = pd.DataFrame(apbd_data, columns=['amount', 'year', 'city'])
            df_var = pd.DataFrame(var_data, columns=['amount', 'year', 'city'])

            # Merge data on year and city
            merged_df = pd.merge(
                df_apbd,
                df_var,
                on=['year', 'city'],
                suffixes=('_apbd', '_var')
            )

            if merged_df.empty:
                continue

            # Prepare data for analysis
            X = merged_df['amount_apbd'].values
            y = merged_df['amount_var'].values

            # Basic correlation analysis
            correlation, p_value = stats.pearsonr(X, y)

            # Linear regression
            X = sm.add_constant(X)
            model = sm.OLS(y, X).fit()

            # Calculate confidence intervals
            conf_int = model.conf_int()

            # Prepare regression diagnostics
            residuals = model.resid
            fitted_values = model.fittedvalues

            # Durbin-Watson test for autocorrelation
            dw_stat = sm.stats.stattools.durbin_watson(residuals)

            # Heteroskedasticity test (Breusch-Pagan)
            bp_test = sm.stats.diagnostic.het_breuschpagan(residuals, X)

            # Store results for this dependent variable
            results[dependent_var] = {
                'correlation': {
                    'coefficient': float(correlation),
                    'p_value': float(p_value)
                },
                'regression': {
                    'coefficients': model.params.tolist(),
                    'std_errors': model.bse.tolist(),
                    'r_squared': float(model.rsquared),
                    'adj_r_squared': float(model.rsquared_adj),
                    'f_statistic': float(model.fvalue),
                    'f_pvalue': float(model.f_pvalue),
                    'confidence_intervals': conf_int.tolist()
                },
                'diagnostics': {
                    'durbin_watson': float(dw_stat),
                    'breusch_pagan_stat': float(bp_test[0]),
                    'breusch_pagan_pval': float(bp_test[1])
                },
                'data_points': {
                    'years': merged_df['year'].tolist(),
                    'apbd_values': merged_df['amount_apbd'].tolist(),
                    'dependent_values': merged_df['amount_var'].tolist(),
                    'fitted_values': fitted_values.tolist(),
                    'residuals': residuals.tolist()
                }
            }

        if not results:
            return jsonify({'error': 'No data available for analysis'}), 404

        return jsonify({
            'region': region,
            'analysis_type': analysis_type,
            'results': results
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500



@app.route("/")
def hello_world():
    return "Hello World!"


if __name__ == "__main__":
    # create_table()
    # db.create_all()
    app.run(debug=True)

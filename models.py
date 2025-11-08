from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=True)  # Tambahkan panjang string
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    data = db.relationship("Data", back_populates="category")
    
    def to_dict(self):
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
    city = db.Column(db.String(255), nullable=True)  # Tambahkan panjang
    regency_id = db.Column(db.Integer, nullable=True, index=True)  # Tambah index
    province_id = db.Column(db.Integer, nullable=True, index=True)  # Tambah index
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    
    category = db.relationship("Category", back_populates="data")
    
    def json(self):
        return {
            'id': self.id,
            'amount': self.amount,
            'year': self.year,
            'city': self.city,
            'category': self.category.to_dict() if self.category else None,
            'category_id': self.category_id,
            'province_id': self.province_id,
            'regency_id': self.regency_id,
        }
        
class APBD(db.Model):
    __tablename__ = 'apbd'
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    file_path = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'city': self.city,
            'type': self.type,
            'year': self.year,
            'amount': self.amount,
            'file_path': self.file_path
        }

class Stunting(db.Model):
    __tablename__ = "stuntings"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    prevalence = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def json(self):
        return {
            "id": self.id,
            "year": self.year,
            "city": self.city,
            "prevalence": self.prevalence,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }

class Province(db.Model):
    __tablename__ = 'provinces'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    bps_code = db.Column(db.String(255), nullable=True)
    kemenkeu_code = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)  # Ubah dari TIMESTAMP
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    regencies = db.relationship('Regency', backref='province', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Province {self.id}: {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'bps_code': self.bps_code,
            'kemenkeu_code': self.kemenkeu_code,
            'created_at': self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'updated_at': self.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        }

class Regency(db.Model):
    __tablename__ = 'regencies'

    id = db.Column(db.Integer, primary_key=True)
    province_id = db.Column(db.Integer, db.ForeignKey('provinces.id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    province_bps_code = db.Column(db.String(255), nullable=True)
    province_kemenkeu_code = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)  # Ubah dari TIMESTAMP
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self):
        return f'<Regency {self.id}: {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'province_id': self.province_id,
            'name': self.name,
            'province_bps_code': self.province_bps_code,
            'province_kemenkeu_code': self.province_kemenkeu_code,
            'created_at': self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'updated_at': self.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        }
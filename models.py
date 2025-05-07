import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)
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
  __tablename__ = 'apbd'
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
    __tablename__ = "stuntings"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    year = db.Column(db.Integer, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    prevalence = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.now)

    def json(self):
        return {
            "id": self.id,
            "year": self.year,
            "city": self.city,
            "prevalence": self.prevalence,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }

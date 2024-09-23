# app/models.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
class Registration(db.Model):
    name = db.Column(db.String(20), nullable=False)
    learning_style = db.Column(db.String(1))
    username = db.Column(db.String(80), primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __init__(self, name, username, email, password):
        self.name = name
        self.username = username
        self.email = email
        self.password = password

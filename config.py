import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///casino.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STARTING_BALANCE = 1000
    ADMIN_USERNAME = 'admin'
    SESSION_PERMANENT = False
    SESSION_TYPE = 'filesystem'
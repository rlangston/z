from os import environ, path

basedir = path.abspath(path.dirname(__file__))

class Config:
    SECRET_KEY = environ.get("SECRET_KEY") or "secret"
    PASSWORD = environ.get("PASSWORD") or "password"
    SQLALCHEMY_DATABASE_URI = environ.get('DATABASE_URL') or 'sqlite:///' + path.join(basedir, 'z.db')

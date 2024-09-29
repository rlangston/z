import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
	SECRET_KEY = os.environ.get("SECRET_KEY") or "secret"
	PASSWORD = os.environ.get("PASSWORD") or "password"
	DATABASE = os.path.join(basedir, "z.db")

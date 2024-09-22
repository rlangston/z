import sqlite3
import os
basedir = os.path.abspath(os.path.dirname(__file__))
parentdir = os.path.dirname(basedir)

SECRET_KEY = os.environ.get("SECRET_KEY") or "secret"
DATABASE = os.path.join(parentdir, "z.db")

db = sqlite3.connect(DATABASE)
db.row_factory = sqlite3.Row

with open(os.path.join(basedir, "schema.sql")) as f:
    db.executescript(f.read())

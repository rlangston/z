from flask import g
import sqlite3
from app import app

def get_db():
	if "db" not in g:
		g.db = sqlite3.connect(app.config["DATABASE"])
		g.db.row_factory = sqlite3.Row
	return g.db


@app.before_request
def before_request():
	get_db()


@app.teardown_request
def teardown_request(exception):
	db = g.pop("db", None)
	if db is not None:
		db.close


def query_db(query, args=(), one=False):
	cur = get_db().execute(query, args)
	rv = cur.fetchall()
	cur.close()
	return (rv[0] if rv else None) if one else rv


def execute_db(query, args=()):
	r = get_db().execute(query, args).fetchone()
	get_db().commit()
	return r





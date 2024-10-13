from flask import render_template, request, redirect, url_for, session
from functools import wraps
from datetime import datetime
import json
import mistune
import re
from app import app
from app import db

def require_login(func):
	"""
	require_login(func) is a decorator for a function func which checks if the session variable userid is 1, and if not redirects to the login page, otherwise it returns the function ie renders the page
	"""
	@wraps(func)
	def wrapper(*args, **kwargs):
		if session.get("userid") != 1:
			return redirect(url_for("login"))
		return func(*args, **kwargs)
	return wrapper


class TaskListRenderer(mistune.HTMLRenderer):
	def list_item(self, text):
		"""
		TaskListRenderer() inherits from and modifies the mistune.HTMLRenderer function to add checkboxes to markdown task lists
		"""
		# Check for task list pattern '- [ ]' or '- [x]'
		if text.startswith("[ ]"):
			checkbox = '<input type="checkbox" disabled>'
			return f"{checkbox} {text[3:]} <br />\n"
		elif text.startswith("[x]"):
			checkbox = '<input type="checkbox" checked disabled>'
			return f"{checkbox} {text[3:]} <br />\n"
		return f"<li>{text}</li>\n"

	def table(self, content):
		# Add a custom class to the table
		return f'<table class="table table-striped">\n{content}</table>\n'

# Create a Markdown parser with the custom renderer
markdown = mistune.create_markdown(renderer=TaskListRenderer(), plugins=['table'])


@app.route("/")
@app.route("/index")
@require_login
def index():
	"""
	index() returns the main z page with the item list etc

	Optional arguments are
		q = search string, defaults to ""
		tags = a string of tags separated by spaces, defaults to ""
		id = z_id to pre-select, or 0 if not present

	The route /index or / calls this function
	"""
	search = request.args.get("q", default = "", type = str)
	tags_query = request.args.get("tags", default = "", type = str)
	z_id = request.args.get("id", default = 0, type = int)
	tags_list = []
	tags_required_list = []

	if tags_query == "<none>":
		no_tag = True
	else:
		for tag in tags_query.split():
			print(tag)
			if tag.startswith("+"):
				# tags_list.append(tag[1:])
				tags_required_list.append(tag[1:])
			else:
				tags_list.append(tag)
		no_tag = False

	search_param = f"%{search}%"
	query = """
        SELECT zettels.id, zettels.body, zettels.modified, zettels.created
        FROM zettels
	"""

	if tags_list:
		placeholders = ", ".join("?" for _ in tags_list)
		query += f"""
			INNER JOIN tags_zettels ON zettels.id = tags_zettels.zettelid
			INNER JOIN tags ON tags.id = tags_zettels.tagid
			WHERE tags.tagname IN ({placeholders})
			AND zettels.body LIKE ?
			GROUP BY zettels.id
		"""
		i = db.query_db(query, tags_list + [search_param])
	elif no_tag == True:
		query += """
			WHERE id NOT IN (SELECT zettelid FROM tags_zettels)
			AND zettels.body LIKE ?
			GROUP BY zettels.id
		"""
		i = db.query_db(query, [search_param])
	else:
		query += """
			WHERE zettels.body LIKE ?
			GROUP BY zettels.id
		"""
		i = db.query_db(query, [search_param])

	items = []
	for item in i:
		tags = db.query_db("SELECT t.tagname FROM tags t JOIN tags_zettels tz ON t.id = tz.tagid JOIN zettels z ON z.id = tz.zettelid WHERE z.id = ? ORDER BY t.tagname ASC", [item["id"]])
		item_tags = [tag[0] for tag in tags]
		if all(item_tag in item_tags for item_tag in tags_required_list):
			items.append({
				"id": item["id"],
				"title": get_first_line(item["body"]),
				"date": item["modified"],
				"tags": " ".join(item_tags)
			})
	return render_template("index.html", items=items, search=search, tags=tags_query, selectedid=z_id)


@app.route("/tags", methods=['POST'])
@require_login
def tags():
	"""
	tags() returns a list of the tags in the database which are used at least once
	The route /tags calls this function
	"""

	query = """
		SELECT t.tagname, t.id, COUNT(tz.zettelid) AS zettel_count
		FROM tags t
		JOIN tags_zettels tz ON t.id = tz.tagid
		GROUP BY t.tagname
		HAVING COUNT(tz.zettelid) > 0;
	"""
	t = db.query_db(query)
	return render_template("tags.html", tags=t)


@app.route("/zettel", methods=['POST'])
@require_login
def zettel():
	"""
	zettel() gets the zettel with the id sent in the JSON request
	returns a JSON string with text of zettel and markdown render of zettel with id
	The route /zettel calls this function
	"""
	r = request.get_json()
	s = db.query_db("SELECT body FROM zettels WHERE id=?", (r["id"],), one=True)

	rs = {
		"text": s["body"],
		"markdown": markdown(strip_tags(s["body"]))
	}
	return json.dumps(rs)


@app.route("/savezettel", methods=['POST'])
@require_login
def save_zettel():
	"""
	save_zettel() saves the zettel to the database using the JSON data provided by the HTTP request
	returns a JSON string containing the new title and new tags for saved zettel
	The route /savezettel calls this function
	"""
	r = request.get_json()

	db.execute_db("UPDATE zettels SET body=?, modified=CURRENT_TIMESTAMP WHERE id=?", [r["body"], r["id"]])

	# delete existing tags in order to replace with the new ones
	db.execute_db("DELETE FROM tags_zettels WHERE zettelid=?", [r["id"]])

	# insert new tags
	tags = get_tags(r["body"])
	tags.sort()
	for tag in tags:
		tag_id = db.query_db("SELECT * FROM tags WHERE tagname=?", [tag], one=True)
		if tag_id is None:
			tag_id  = db.execute_db("INSERT INTO tags (tagname) VALUES (?) RETURNING id", [tag])
		db.execute_db("INSERT INTO tags_zettels (tagid,zettelid) VALUES (?, ?)", [tag_id["id"], r["id"]])

	rs = {
		"title": get_first_line(r["body"]),
		"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
		"tags": " ".join(tag for tag in tags),
		"text": r["body"],
		"markdown": markdown(strip_tags(r["body"]))
	}

	return json.dumps(rs)


@app.route("/deletezettel", methods=['POST'])
@require_login
def delete_zettel():
	"""
	delete_zettel deletes the zettel with the id in the JSON data provided by the HTTP request
	The route /deletezettel calls this function
	"""
	r = request.get_json()
	db.execute_db("DELETE FROM tags_zettels WHERE zettelid=?", [r["id"]])
	db.execute_db("DELETE FROM zettels WHERE id=?", [r["id"]])
	return {}


@app.route("/newzettel", methods=['POST'])
@require_login
def new_zettel():
	"""
	new_zettel inserts a blank record into the database and then returns the record entered as a JSON string
	The route /newzettel calls this function
	"""
	z_id = db.execute_db("INSERT INTO zettels (body) VALUES ('') RETURNING id")

	# Get default values from database
	r = db.query_db("SELECT * FROM zettels WHERE id=?", [z_id["id"]], one=True)
	rs = {
		"id": r["id"],
		"title": get_first_line(r["body"]),
		"date": r["modified"],
		"tags": "",
		"text": r["body"],
		"markdown": markdown(strip_tags(r["body"]))
	}
	return json.dumps(rs)

@app.route("/login", methods=['GET', 'POST'])
def login():
	# Redirect to home if already logged in
	if session.get("userid") == 1:
		return redirect(url_for(""))
	if request.method == "POST":
		if request.form["password"] == app.config["PASSWORD"]:
			session["userid"] = 1
			return redirect(url_for("index"))
	return render_template("login.html")


@app.route("/logout")
def logout():
	session.pop("userid", None)
	return redirect(url_for("login"))


def get_first_line(s, maxlength=40):
	"""
	get_first_line(string s, int maxlength=40) returns the first line of the string up to a maximum length of 40
	"""
	newline_index = s.find('\n')
	if 0 <= newline_index < maxlength:
		title = s[:newline_index].lstrip("#")
	else:
		title = s[:maxlength].lstrip("#")
	return title.translate( { ord(i): None for i in "[]"} )


def get_tags(s):
	"""
	get_tags(string s) extracts the tags from the final line of the string.
	"""

	# Split the input text into lines
	lines = s.split("\n")

	# Return empty list if there is only a single line
	if len(lines) <= 1:
		return []

	# Get the final line
	last_line = lines[-1]

	# Find words that start with #
	result = [word[1:] for word in last_line.split() if word.startswith('#')]

	return result


def strip_tags(s):
	"""
	strip_tags(string s) removes the alphabetical tags and replaces numerical tags (such as "#6") in lines other than the last with the relevant markdown code to link
	"""

	lines = s.split("\n")

	# If there is only a single line, return it
	if len(lines) == 1:
		return lines[0]

	# Remove the final line if it has tags
	if lines[-1].startswith("#"):
		lines = lines[:-1]

	# Replace numerical links
	pattern = r"#(\d+)(?=\s|$)"
	def replace_func(match):
		digits = match.group(1)  # Extract the digits
		return f"[{digits}](index?id={digits})"

	lines[:] = [re.sub(pattern, replace_func, line) for line in lines]

	# Return text containing the lines
	return "\n".join(lines)


from flask import render_template, request
from datetime import datetime
from app import app
from app import db
import json
import markdown

# TODO deploy plus to github

# TODO links (? display ids on zettels)

# TODO boolean searches for search and tags

# TODO update for SQLAlchemy rather than direct SQL calls
# TODO check classes and ids consistent in index.html and styles.css / script.js
# TODO tidy up all code - single button class

# TODO update styles and colors

# TODO merge items (tags and text) - need to re-enable drag and drop

@app.route("/")
@app.route("/index")
def index():
	"""
	index() returns the main z page with the item list etc

	Optional arguments are
		q = search string, defaults to ""
		tags = a string of tags separated by spaces, defaults to ""

	The route /index or / calls this function
	"""
	search = request.args.get("q", default = "", type = str)
	tags_query = request.args.get("tags", default = "", type = str)
	tags_list = tags_query.split()
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
	else:
		query += """
			WHERE zettels.body LIKE ?
			GROUP BY zettels.id
		"""
		i = db.query_db(query, [search_param])

	items = []
	for item in i:
		tags = db.query_db("SELECT t.tagname FROM tags t JOIN tags_zettels tz ON t.id = tz.tagid JOIN zettels z ON z.id = tz.zettelid WHERE z.id = ? ORDER BY t.tagname ASC", [item["id"]])
		items.append({
			"id": item["id"],
			"title": get_first_line(item["body"]),
			"date": item["modified"],
			"tags": " ".join(tag[0] for tag in tags)
   		})
	return render_template("index.html", items=items, search=search, tags=tags_query)


@app.route("/tags", methods=['POST'])
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
	# print(t[0]["id"], t[0]["tagname"], t[0]["zettel_count"])
	return render_template("tags.html", tags=t)


@app.route("/zetteltext/<int:z_id>", methods=['POST'])
def zetteltext(z_id):
	"""
	zettel(z_id) returns the text of zettel with id z_id
	The route zettel/[id] calls this function
	"""
	r = db.query_db("SELECT body FROM zettels WHERE id=?", [z_id], one=True)
	return r["body"]


@app.route("/zettel/<int:z_id>", methods=['POST'])
def zettel(z_id):
	"""
	zettel(z_id) returns a JSON string with text of zettel and markdown render of zettel with id z_id
	The route zettel/[id] calls this function
	"""
	# TODO: change this to take JSON
	r = db.query_db("SELECT body FROM zettels WHERE id=?", [z_id], one=True)
	rs = {
		"text": r["body"],
		"markdown": markdown.markdown(strip_tags(r["body"]))
	}
	return json.dumps(rs)


@app.route("/savezettel", methods=['POST'])
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
	for tag in tags:
		tag_id = db.query_db("SELECT * FROM tags WHERE tagname=?", [tag], one=True)
		if tag_id is None:
			tag_id  = db.execute_db("INSERT INTO tags (tagname) VALUES (?) RETURNING id", [tag])
		db.execute_db("INSERT INTO tags_zettels (tagid,zettelid) VALUES (?, ?)", [tag_id["id"], r["id"]])

	# TODO: sort tags in alphabetical order
	rs = {
		"title": get_first_line(r["body"]),
		"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
		"tags": " ".join(tag for tag in tags),
		"text": r["body"],
		"markdown": markdown.markdown(strip_tags(r["body"]))
	}

	return json.dumps(rs)


@app.route("/deletezettel", methods=['POST'])
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
def new_zettel():
	z_id = db.execute_db("INSERT INTO zettels (body) VALUES ('New item') RETURNING id")
	r = db.query_db("SELECT * FROM zettels WHERE id=?", [z_id["id"]], one=True)
	rs = {
		"id": r["id"],
		"body": r["body"],
		"title": get_first_line(r["body"]),
		"date": r["modified"],
		"tags": ""
	}
	return json.dumps(rs)


"""
	Database schema:
	TABLE zettels
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	body TEXT NOT NULL,
	modified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
"""


def get_first_line(s, maxlength=40):
	"""
	get_first_line(string s, int maxlength=40) returns the first line of the string up to a maximum length of 40
	"""
	newline_index = s.find('\n')
	if 0 <= newline_index < maxlength:
		return s[:newline_index]
	return s[:maxlength]


def get_tags(s):
    # Split the input text into lines
    lines = s.strip().splitlines()

    # Get the final line
    if not lines:
        return []  # Return empty list if no lines are present

    last_line = lines[-1]

    # Find words that start with #
    result = [word[1:] for word in last_line.split() if word.startswith('#')]

    return result


def strip_tags(s):
	lines = s.rstrip().split("\n")
	if len(lines) == 1:
		return s
	if lines[-1].startswith("#"):
		return "\n".join(lines[:-1])
	return s

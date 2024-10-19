from flask import render_template, request, redirect, url_for, session, jsonify
from functools import wraps
from datetime import datetime
from sqlalchemy import func

import json
import mistune
import re

from .models import Zettel, Tag, TagZettel
from .db import db

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


def register_routes(app):
	@app.route("/")
	@app.route("/index")
	@require_login
	def index():
		"""
		index() returns the main z page with the item list etc

		Optional arguments are
			q = search string, defaults to ""
			tags = a string of tags separated by spaces, defaults to "".  If a tag is preceded by "+" then it is a required tag
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
				if tag.startswith("+"):
					# tags_list.append(tag[1:])
					tags_required_list.append(tag[1:])
				else:
					tags_list.append(tag)
			no_tag = False

		query = Zettel.query

		if no_tag == True:
			# Just want records which have no tag
			query = query.outerjoin(TagZettel).filter(TagZettel.zettelid == None)
		elif tags_list:
			query = query.join(TagZettel).join(Tag).filter(Tag.tagname.in_(tags_list))

		if search:
			query = query.filter(Zettel.body.like(f"%{search}%"))

		zettels = query.all()

		items = []
		for zettel in zettels:
			tags = db.session.query(Tag.tagname).join(TagZettel).filter(TagZettel.zettelid == zettel.id).all()
			item_tags = [tag[0] for tag in tags]
			if all(item_tag in item_tags for item_tag in tags_required_list):
				items.append({
					"id": zettel.id,
					"title": get_first_line(zettel.body),
					"date": zettel.modified.strftime("%Y-%m-%d %H:%M:%S"),
					"tags": " ".join([tag[0] for tag in tags])
				})
		return render_template("index.html", items=items, search=search, tags=tags_query, selectedid=z_id)


	@app.route("/tags", methods=['POST'])
	@require_login
	def tags():
		"""
		tags() returns a list of the tags in the database which are used at least once
		The route /tags calls this function
		"""

		tags = (
			db.session.query(
				Tag.tagname,
				Tag.id,
				func.count(TagZettel.zettelid).label("zettel_count"))
			.join(TagZettel)
			.group_by(Tag.tagname)
			.having(db.func.count(TagZettel.zettelid) > 0)
			.all()
		)
		return render_template("tags.html", tags=tags)


	@app.route("/zettel", methods=['POST'])
	@require_login
	def zettel():
		"""
		zettel() gets the zettel with the id sent in the JSON request
		returns a JSON string with text of zettel and markdown render of zettel with id
		The route /zettel calls this function
		"""
		r = request.get_json()
		zettel = Zettel.query.get(r["id"])

		if not zettel:
			return jsonify({"error": "Zettel not found"}), 404

		rs = {
			"text": zettel.body,
			"markdown": markdown(strip_tags(zettel.body))
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

		# Fetch the existing zettel
		zettel = Zettel.query.get(r["id"])
		if not zettel:
			return {"error": "Zettel not found"}, 404

		# Update the zettel's body and modified timestamp
		zettel.body = r["body"]
		zettel.modified = datetime.now()

		# Remove existing tag associations
		db.session.query(TagZettel).filter(TagZettel.zettelid == zettel.id).delete()

		# Insert new tags
		tags = get_tags(zettel.body)
		tags.sort()
		for tag_name in tags:
			# Find or create the tag
			tag = Tag.query.filter_by(tagname=tag_name).first()
			if not tag:
				tag = Tag(tagname=tag_name)
				db.session.add(tag)
				db.session.flush()  # Ensure tag ID is available before using it

			# Create the association between tag and zettel
			tag_zettel = TagZettel(tagid=tag.id, zettelid=zettel.id)
			db.session.add(tag_zettel)

		db.session.commit()

		rs = {
			"title": get_first_line(zettel.body),
			"date": zettel.modified.strftime("%Y-%m-%d %H:%M:%S"),
			"tags": " ".join(tags),
			"text": zettel.body,
			"markdown": markdown(strip_tags(zettel.body))
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
		# Delete associated tags
		db.session.query(TagZettel).filter(TagZettel.zettelid == r["id"]).delete()

		# Delete the zettel
		zettel = Zettel.query.get(r["id"])
		if zettel:
			db.session.delete(zettel)

		db.session.commit()
		return {}


	@app.route("/newzettel", methods=['POST'])
	@require_login
	def new_zettel():
		"""
		new_zettel inserts a blank record into the database and then returns the record entered as a JSON string
		The route /newzettel calls this function
		"""

		new_zettel = Zettel(body="", modified=datetime.now(), created=datetime.now())
		db.session.add(new_zettel)
		db.session.commit()

		rs = {
			"id": new_zettel.id,
			"title": get_first_line(new_zettel.body),
			"date": new_zettel.modified.strftime("%Y-%m-%d %H:%M:%S"),
			"tags": "",
			"text": new_zettel.body,
			"markdown": markdown(strip_tags(new_zettel.body))
		}

		return json.dumps(rs)


	@app.route("/newmailzettel", methods=['POST'])
	def new_mail_zettel():
		"""
		new_mail_zettel inserts a record into the database based on the JSON request received
		it anticipates that the JSON will include two fields ["envelope"]["to"] and ["plain"] as it will have been forwarded from an email
		the "to" field is checked against the password and a new item is only added if it validates
		the zettel text is then set to be the "plain" field

		The route /newmailzettel calls this function
		"""

		r = request.get_json()
		index = r["headers"]["to"].find("<")
		if index != -1:
			to = r["headers"]["to"][index + 1:]
		else:
			to = r["headers"]["to"]
		if to.split("@")[0] != app.config["PASSWORD"]:
			return "Address not valid", 422

		new_zettel = Zettel(body=trim_blank_lines(["plain"]), modified=datetime.now(), created=datetime.now())
		db.session.add(new_zettel)
		db.session.flush() # Ensure new zettel id is available before using it

		# Insert new tags
		tags = get_tags(new_zettel.body)
		tags.sort()
		for tag_name in tags:
			# Find or create the tag
			tag = Tag.query.filter_by(tagname=tag_name).first()
			if not tag:
				tag = Tag(tagname=tag_name)
				db.session.add(tag)
				db.session.flush()  # Ensure tag ID is available before using it

			# Create the association between tag and zettel
			tag_zettel = TagZettel(tagid=tag.id, zettelid=new_zettel.id)
			db.session.add(tag_zettel)

		db.session.commit()

		rs = {
			"id": new_zettel.id,
			"title": get_first_line(new_zettel.body),
			"date": new_zettel.modified.strftime("%Y-%m-%d %H:%M:%S"),
			"tags": "",
			"text": new_zettel.body,
			"markdown": markdown(strip_tags(new_zettel.body))
		}

		return json.dumps(rs), 200


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


def trim_blank_lines(s):
	"""
	trim_blank_lines(string s) removes any blank lines at the end of text
	"""
	lines = s.splitlines()  # Split the text into lines
	while lines and not lines[-1].strip():  # Remove blank or whitespace-only lines from the end
		lines.pop()
	return "\n".join(lines)  # Join the remaining lines back into a single string

from .db import db

class Zettel(db.Model):
    __tablename__ = 'zettels'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    modified = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    created = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    tagname = db.Column(db.String(50), nullable=False)

class TagZettel(db.Model):
    __tablename__ = 'tags_zettels'
    zettelid = db.Column(db.Integer, db.ForeignKey('zettels.id'), primary_key=True)
    tagid = db.Column(db.Integer, db.ForeignKey('tags.id'), primary_key=True)

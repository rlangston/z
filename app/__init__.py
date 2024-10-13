from flask import Flask

from config import Config
from .db import db

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    from .models import Zettel
    from .routes import register_routes
    db.create_all()
    register_routes(app)

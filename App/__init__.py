from flask import Flask
from .database import db
from .config import load_config  # uses default_config.py in dev (per template)

def create_app(config_overrides=None):
    app = Flask(__name__)
    # Ensure load_config is called with the expected signature.
    overrides = config_overrides or {}
    cfg = load_config(app, overrides)
    if cfg:
        # If load_config returns a mapping, merge it; if it mutates app.config, this is harmless.
        app.config.update(cfg)

    db.init_app(app)

    with app.app_context():
        # import models so SQLAlchemy sees them, then create tables
        from .models import core  # noqa: F401
        db.create_all()

    return app

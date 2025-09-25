import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine.url import make_url
from sqlalchemy import MetaData

db = SQLAlchemy()

# Keep a reference to the last created/bound Flask app
_bound_app = None

def bind_app(app):
    global _bound_app
    _bound_app = app

def _resolve_app(app):
    # Prefer explicit app, otherwise use bound app
    return app or _bound_app

def create_db(app=None, *, drop=False):
    """
    Create tables. If drop=True, drop all first.
    If no app passed, uses the last bound app.
    """
    app = _resolve_app(app)
    if app is None:
        raise RuntimeError("No Flask app bound. Call create_app(...) first.")
    ctx = app.app_context()
    ctx.push()
    try:
        # Ensure all models are imported so mappers are registered
        from .models import core  # noqa: F401
        from .models import user as user_models  # noqa: F401
        if drop:
            db.drop_all()
        db.create_all()
    finally:
        ctx.pop()

# Back-compat for tests importing init_db
def init_db(app=None, *, drop=False):
    return create_db(app=app, drop=drop)

def reset_db(app, *, hard=False):
    """
    Drop all tables using reflection. If hard and using SQLite file, delete it.
    """
    ctx = app.app_context()
    ctx.push()
    try:
        meta = MetaData()
        meta.reflect(bind=db.engine)
        meta.drop_all(bind=db.engine)
        db.engine.dispose()
        if hard:
            uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
            try:
                url = make_url(uri)
                if url.drivername == "sqlite" and url.database and url.database != ":memory:":
                    path = url.database
                    if not os.path.isabs(path):
                        path = os.path.join(os.getcwd(), path)
                    if os.path.exists(path):
                        os.remove(path)
            except Exception:
                pass
    finally:
        ctx.pop()

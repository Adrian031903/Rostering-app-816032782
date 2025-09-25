import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine.url import make_url
from sqlalchemy import MetaData

db = SQLAlchemy()

def create_db(app=None, *, drop=False):
    """
    Create tables. If drop=True, drop all first.
    """
    ctx = app.app_context() if app else None
    if ctx: ctx.push()
    try:
        from .models import core  # ensure models are imported
        if drop:
            db.drop_all()
        db.create_all()
    finally:
        if ctx: ctx.pop()

def reset_db(app, *, hard=False):
    """
    Drop all tables using reflection. If hard and using SQLite file, delete it.
    """
    ctx = app.app_context()
    ctx.push()
    try:
        # drop via reflection to catch stale tables
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

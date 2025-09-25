import os
from flask import Flask, render_template
from flask_uploads import DOCUMENTS, IMAGES, TEXT, UploadSet, configure_uploads
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage

from App.database import init_db
from App.config import load_config

from App.controllers import (
    setup_jwt,
    add_auth_context
)

from App.views import views, setup_admin

def add_views(app):
    for view in views:
        app.register_blueprint(view)

# Delegate to the app factory and keep a global app context for tests
from . import create_app as _create_app
from .database import bind_app

def create_app(config_overrides=None):
    app = _create_app(config_overrides)

    # Ensure JWT is configured for tests that call create_access_token
    if not app.config.get("JWT_SECRET_KEY"):
        app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret")
    setup_jwt(app)
    add_auth_context(app)

    bind_app(app)
    # Push a context so tests calling db.* without context still work
    app.app_context().push()
    return app
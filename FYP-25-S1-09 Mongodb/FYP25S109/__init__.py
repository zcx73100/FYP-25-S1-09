from flask import Flask
from flask_pymongo import PyMongo
import sys
import os
mongo = PyMongo()

def create_app():
    app = Flask(__name__)

    # Configure your Flask app (static folder, etc.) as needed...
    file_dir = os.path.dirname(os.path.abspath(__file__))
    static_path = os.path.join(file_dir, 'static')
    app = Flask(__name__, static_folder=static_path, static_url_path='/static')

    # Flask Configuration
    app.config['SECRET_KEY'] = 'fyp25'
    app.config["MONGO_URI"] = "mongodb://localhost:27017/fyps12509"
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # Initialize MongoDB
    mongo.init_app(app)

    # Register Blueprints
    from .boundary import boundary
    app.register_blueprint(boundary, url_prefix='/')

    # ✅ Import OpenShot API Helper
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from api.openshot_api import create_video_project

    # Import and register the SadTalker blueprint from sadtalker_boundary.py (which is now in the same package)
    from .boundary_sadtalker import boundary_sadtalker
    app.register_blueprint(boundary_sadtalker, url_prefix='/sadtalker')

    return app

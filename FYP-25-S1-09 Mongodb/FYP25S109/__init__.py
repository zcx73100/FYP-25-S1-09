from flask import Flask
from flask_pymongo import PyMongo
import sys
import os
mongo = PyMongo()

def create_app():
    app = Flask(__name__)

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

    return app

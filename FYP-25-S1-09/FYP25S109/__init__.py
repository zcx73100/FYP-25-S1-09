import os
from flask import Flask
from flask_pymongo import PyMongo

mongo = PyMongo()

def create_app():
    # __file__ is at: <project_root>/FYP-25-S1-09/FYP25S109/__init__.py
    # We want the static folder to be: <project_root>/FYP25S109/static
    # Compute the absolute path of the current folder (FYP25S109)
    file_dir = os.path.dirname(os.path.abspath(__file__))
    # Set static folder relative to FYP25S109 folder
    static_path = os.path.join(file_dir, 'static')
    
    # Create the Flask app, overriding the static folder and url path.
    app = Flask(
        __name__,
        static_folder=static_path,   # e.g., ...\FYP25S109\static
        static_url_path='/static'
    )

    # Basic configuration
    app.config['SECRET_KEY'] = 'fyp25'
    # (MongoDB configuration; adjust as needed)
    app.config["MONGO_URI"] = "mongodb://localhost:27017/fyps12509"
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # Initialize MongoDB
    mongo.init_app(app)

    # Register the blueprint (defined in boundary.py)
    from .boundary import boundary
    app.register_blueprint(boundary, url_prefix='/')

    return app

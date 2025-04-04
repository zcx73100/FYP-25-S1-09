from flask import Flask
from flask_pymongo import PyMongo
import sys
import os
from .chatbot import chatbot

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

    # ✅ Register Chatbot Blueprint
    from .chatbot import chatbot
    app.register_blueprint(chatbot, url_prefix='/')

    return app

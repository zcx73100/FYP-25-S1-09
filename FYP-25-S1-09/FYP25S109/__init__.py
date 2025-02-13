from flask import Flask
from flask_mysqldb import MySQL

mysql = MySQL()

#You can change the user/password/db base on what you have set up
def create_app():
  app=Flask(__name__)
  app.config['SECRET_KEY'] = 'fyp25'
  app.config['MYSQL_USER'] = "fyp2509"
  app.config['MYSQL_PASSWORD'] = "password"
  app.config['MYSQL_DB'] = "fyps12509"

  app.config['UPLOAD_FOLDER'] = 'FYPS12509/static/uploads/'
  app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

  mysql = MySQL(app)

#from .views import views
  from .boundary import boundary

#app.register_blueprint(views, url_prefix='/')
  app.register_blueprint(boundary, url_prefix='/')

  return app
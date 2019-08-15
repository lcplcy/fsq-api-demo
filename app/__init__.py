from flask import Flask
from flask_cors import CORS, cross_origin
import foursquare
from config import Config
from geopy.geocoders import GoogleV3

def split_string(string, delimiter=" "):
    return string.strip().split(delimiter)

app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config.from_object(Config)
geolocator = GoogleV3(api_key=app.config['GOOGLEMAPSAPI_KEY'], timeout=None)
client = foursquare.Foursquare(client_id=app.config['FOURSQUARE_CLIENT_ID'],
                               client_secret=app.config['FOURSQUARE_CLIENT_SECRET'],
                               redirect_uri='https://api-compare.herokuapp.com/redirect')

FSQ_CLIENT_ID = app.config['FOURSQUARE_CLIENT_ID']
FSQ_CLIENT_SECRET = app.config['FOURSQUARE_CLIENT_SECRET']
MAPBOX_ACCESS_KEY = app.config['MAPBOX_ACCESS_KEY']

app.jinja_env.globals.update(split_string=split_string)

from app import routes

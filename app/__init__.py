from flask import Flask
import foursquare
from config import Config
from geopy.geocoders import GoogleV3

app = Flask(__name__)
app.config.from_object(Config)
geolocator = GoogleV3(api_key=app.config['GOOGLEMAPSAPI_KEY'], timeout=None)
client = foursquare.Foursquare(client_id=app.config['FOURSQUARE_CLIENT_ID'],
                               client_secret=app.config['FOURSQUARE_CLIENT_SECRET'],
                               redirect_uri='https://api-compare.herokuapp.com/redirect')

FSQ_CLIENT_ID = app.config['FOURSQUARE_CLIENT_ID']
FSQ_CLIENT_SECRET = app.config['FOURSQUARE_CLIENT_SECRET']
MAPBOX_ACCESS_KEY = app.config['MAPBOX_ACCESS_KEY']

from app import routes

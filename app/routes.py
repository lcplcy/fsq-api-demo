from flask import render_template, request, redirect, url_for, session
from app import app, client, geolocator, FSQ_CLIENT_ID, FSQ_CLIENT_SECRET, MAPBOX_ACCESS_KEY
import re
import os
import json

LATLNG_REGEX = re.compile("\-?(90|[0-8]?[0-9]\.[0-9]{0,6})\,\-?(180|(1[0-7][0-9]|[0-9]{0,2})\.[0-9]{0,6})")
RESULT_LIMIT = 9

def fsq_result_to_geojson(fsq_result, endpoint="search"):
    geojson = {'type': 'FeatureCollection', 'features': []}
    fsq_array = []
    if endpoint=="search":
        fsq_array = fsq_result["venues"]
    elif endpoint=="explore":
        fsq_items = fsq_result["groups"][0]["items"]
        for i in fsq_items:
            fsq_array.append(i["venue"])
    for row in fsq_array:
        feature = {'type': 'Feature',
                   'properties': {},
                   'geometry': {'type': 'Point',
                                'coordinates': []}}
        feature['geometry']['coordinates'] = [row["location"]["lng"], row["location"]["lat"]]
        feature['properties']['venuename'] = row["name"]
        feature['properties']['venueid'] = row["id"]

        address = ""
        try:
            address = row["location"]["address"]
        except KeyError:
            pass
        feature['properties']['address'] = address

        rating = 0
        venue_details = client.venues(row["id"])["venue"]
        try:
            rating = venue_details["rating"]
        except KeyError:
            pass
        feature['properties']['rating'] = rating

        image = ""
        try:
            image = venue_details["bestPhoto"]["prefix"] + "100x100" + venue_details["bestPhoto"]["suffix"]
        except KeyError:
            pass

        feature['properties']['image'] = image
        geojson['features'].append(feature)
    return geojson

def fsq_result_calc_center(fsq_result, endpoint="search"):
    lat = []
    long = []
    fsq_array = []
    if endpoint=="search":
        fsq_array = fsq_result["venues"]
    elif endpoint=="explore":
        fsq_items = fsq_result["groups"][0]["items"]
        for i in fsq_items:
            fsq_array.append(i["venue"])
    for i in fsq_array:
        lat.append(float(i["location"]["lat"]))
        long.append(float(i["location"]["lng"]))
    return "%f,%f" % (sum(long)/len(long), sum(lat)/len(lat))

@app.route('/', methods=['GET','POST'])
def index():
    search_type = request.args.get("search_type")

    no_results = True
    fsq_result = ""
    result_geojson = ""
    map_center = ""
    api_get_url = "https://api.foursquare.com/v2/venues/{search_type}?client_id={{client_id}}&client_secret={{client_secret}}&v={{v}}&limit=10&radius=250&{ll_or_near}&{intent}"

    if search_type:
        curr_location = request.args.get("cl")
        no_results = False

        if search_type == "search":
            if LATLNG_REGEX.match(curr_location):
                fsq_result = client.venues.search(params={'ll': curr_location,
                                                          'intent':"browse",
                                                          'radius':250,
                                                          'limit': RESULT_LIMIT})
                api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="intent=browse")
            else:
                fsq_result = client.venues.search(params={'near': curr_location,
                                                          'intent':"browse",
                                                          'radius':250,
                                                          'limit': RESULT_LIMIT})
                api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="intent=browse")
            result_geojson = fsq_result_to_geojson(fsq_result, endpoint="search")
            map_center = fsq_result_calc_center(fsq_result, endpoint="search")
        if search_type == "explore":
            if LATLNG_REGEX.match(curr_location):
                fsq_result = client.venues.explore(params={'ll': curr_location,
                                                          'radius':250,
                                                          'limit': RESULT_LIMIT})
                api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="")
            else:
                fsq_result = client.venues.explore(params={'near': curr_location,
                                                          'radius':250,
                                                          'limit': RESULT_LIMIT})
                api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="")
            result_geojson = fsq_result_to_geojson(fsq_result, endpoint="explore")
            map_center = fsq_result_calc_center(fsq_result, endpoint="explore")
        return render_template("index.html",no_results=no_results,
                                result_geojson=result_geojson, map_center=map_center,
                                fsq_result=fsq_result, api_get_url=api_get_url,
                                MAPBOX_ACCESS_KEY=MAPBOX_ACCESS_KEY)
    else:
        return render_template("index.html",no_results=no_results)

@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                 endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)

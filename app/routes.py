from flask import render_template, request, redirect, url_for, session, jsonify
from app import app, client, geolocator, FSQ_CLIENT_ID, FSQ_CLIENT_SECRET, MAPBOX_ACCESS_KEY
from flask_cors import cross_origin
import foursquare
import re
import os
import json

# show venue counts for countries
# /venues/explore offset

LATLNG_REGEX = re.compile("\-?(90|[0-8]?[0-9]\.[0-9]{0,6})\,\-?(180|(1[0-7][0-9]|[0-9]{0,2})\.[0-9]{0,6})")
RESULT_LIMIT = 9

@app.before_request
def before_request():
    if request.url.startswith('http://fsq-api.herokuapp.com'):
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)


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
        if len(row["categories"]) == 0:
            continue
        feature = {'type': 'Feature',
                   'properties': {},
                   'geometry': {'type': 'Point',
                                'coordinates': []}}
        feature['geometry']['coordinates'] = [row["location"]["lng"], row["location"]["lat"]]
        feature['properties']['venuename'] = row["name"]
        feature['properties']['venueid'] = row["id"]
        if endpoint=="explore":
            rating = 0
            if "rating" in row:
                rating = row["rating"]
            feature['properties']['rating'] = rating
            hours = "-"
            if "hours" in row:
                if "richStatus" in row["hours"]:
                    hours = row["hours"]["richStatus"]["text"]
            feature["properties"]["hours"] = hours

        try:
            for index,i in enumerate(row["categories"]):
                if i["primary"]:
                    category_icon = row["categories"][index]["icon"]["prefix"] + "44" + row["categories"][index]["icon"]["suffix"]
                    feature['properties']['category_icon'] = category_icon
        except (KeyError,IndexError) as e:
            feature['properties']['category_icon'] = "http://maps.google.com/mapfiles/ms/micons/blue.png"

        address = ""
        try:
            address = row["location"]["address"]
        except KeyError:
            pass
        feature['properties']['address'] = address

        """ Pull rating from the venue details API
        rating = 0
        venue_details = client.venues(row["id"])["venue"]
        try:
            rating = venue_details["rating"]
        except KeyError:
            pass
        feature['properties']['rating'] = rating
        """
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
    api_get_url = "https://api.foursquare.com/v2/venues/{search_type}?client_id={{client_id}}&client_secret={{client_secret}}&v=20190101&limit=10&radius=250&{ll_or_near}{intent}"

    if search_type:
        curr_location = request.args.get("cl")
        no_results = False
        locale = request.args.get("locale")

        if search_type == "search":
            try:
                if LATLNG_REGEX.match(curr_location):
                    if locale:
                        fsq_result = client.venues.search(params={'ll': curr_location,
                                                                  'intent':"browse",
                                                                  'radius':250,
                                                                  'locale':locale,
                                                                  'limit': RESULT_LIMIT})
                        api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="&intent=browse") + "&locale=" + locale
                    else:
                        fsq_result = client.venues.search(params={'ll': curr_location,
                                                                  'intent':"browse",
                                                                  'radius':250,
                                                                  'limit': RESULT_LIMIT})
                        api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="&intent=browse")
                else:
                    if locale:
                        fsq_result = client.venues.search(params={'near': curr_location,
                                                              'intent':"browse",
                                                              'radius':250,
                                                              'locale':locale,
                                                              'limit': RESULT_LIMIT})
                        api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="&intent=browse") + "&locale=" + locale
                    else:
                        fsq_result = client.venues.search(params={'near': curr_location,
                                                              'intent':"browse",
                                                              'radius':250,
                                                              'limit': RESULT_LIMIT})
                        api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="&intent=browse")
            except (foursquare.ParamError,foursquare.FailedGeocode) as e:
                curr_location = "1.2787325314969156,103.8434731966384"
                return redirect("?search_type=search&cl=" + curr_location)

            result_geojson = fsq_result_to_geojson(fsq_result, endpoint="search")
            map_center = fsq_result_calc_center(fsq_result, endpoint="search")
        if search_type == "explore":
            section = ""
            if "section" in request.args:
                section = request.args.get("section")
            if len(section) > 0:
                try:
                    if LATLNG_REGEX.match(curr_location):
                        if locale:
                            fsq_result = client.venues.explore(params={'ll': curr_location,
                                                                      'radius':250,
                                                                      'section':section,
                                                                      'locale':locale,
                                                                      'limit': RESULT_LIMIT})
                            api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="") + "&section=" + section + "&locale=" + locale
                        else:
                            fsq_result = client.venues.explore(params={'ll': curr_location,
                                                                      'radius':250,
                                                                      'section':section,
                                                                      'limit': RESULT_LIMIT})
                            api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="") + "&section=" + section
                    else:
                        if locale:
                            fsq_result = client.venues.explore(params={'near': curr_location,
                                                                      'radius':250,
                                                                      'section':section,
                                                                      'locale':locale,
                                                                      'limit': RESULT_LIMIT})
                            api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="") + "&section=" + section + "&locale=" + locale
                        else:
                            fsq_result = client.venues.explore(params={'near': curr_location,
                                                                      'radius':250,
                                                                      'section':section,
                                                                      'limit': RESULT_LIMIT})
                            api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="") + "&section=" + section
                except (foursquare.ParamError,foursquare.FailedGeocode) as e:
                    curr_location = "1.2787325314969156,103.8434731966384"
                    return redirect("?search_type=explore&cl=" + curr_location + "&section=" + section)

            else:
                try:
                    if LATLNG_REGEX.match(curr_location):
                        if locale:
                            fsq_result = client.venues.explore(params={'ll': curr_location,
                                                                      'radius':250,
                                                                      'locale':locale,
                                                                      'limit': RESULT_LIMIT})
                            api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="") + "&locale=" + locale
                        else:
                            fsq_result = client.venues.explore(params={'ll': curr_location,
                                                                      'radius':250,
                                                                      'limit': RESULT_LIMIT})
                            api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="")
                    else:
                        if locale:
                            fsq_result = client.venues.explore(params={'near': curr_location,
                                                                      'radius':250,
                                                                      'locale':locale,
                                                                      'limit': RESULT_LIMIT})
                            api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="") + "&locale=" + locale
                        else:
                            fsq_result = client.venues.explore(params={'near': curr_location,
                                                                      'radius':250,
                                                                      'limit': RESULT_LIMIT})
                            api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="")
                except (foursquare.ParamError,foursquare.FailedGeocode) as e:
                    curr_location = "1.2787325314969156,103.8434731966384"
                    return redirect("?search_type=explore&cl=" + curr_location)
            result_geojson = fsq_result_to_geojson(fsq_result, endpoint="explore")
            map_center = fsq_result_calc_center(fsq_result, endpoint="explore")
        return render_template("index.html",no_results=no_results,
                                result_geojson=result_geojson, map_center=map_center,
                                fsq_result=fsq_result, api_get_url=api_get_url,
                                MAPBOX_ACCESS_KEY=MAPBOX_ACCESS_KEY)
    else:
        return render_template("index.html",no_results=no_results)

@app.route('/details',methods=['GET'])
@cross_origin()
def venue_details():
    venueid = request.args.get("venueid")
    locale = request.args.get("locale")
    fsq_result = None
    if locale:
        fsq_result = client.venues(venueid,params={'locale':locale})["venue"]
    else:
        fsq_result = client.venues(venueid)["venue"]
    return jsonify(fsq_result)

@app.route('/suggestcomplete',methods=['GET'])
@cross_origin()
def suggest_complete():
    query = request.args.get("query")
    curr_location = request.args.get("cl")
    locale = request.args.get("locale")
    fsq_result = None

    if LATLNG_REGEX.match(curr_location):
        if locale:
            fsq_result = client.venues.suggestcompletion(params={'ll': curr_location,
                                                      'radius': 250,
                                                      'query': query,
                                                      'locale': locale,
                                                      'limit': RESULT_LIMIT})
        else:
            fsq_result = client.venues.suggestcompletion(params={'ll': curr_location,
                                                      'radius': 250,
                                                      'query': query,
                                                      'limit': RESULT_LIMIT})
    else:
        if locale:
            fsq_result = client.venues.suggestcompletion(params={'near': curr_location,
                                                      'radius': 250,
                                                      'query': query,
                                                      'locale': locale,
                                                      'limit': RESULT_LIMIT})
        else:
            fsq_result = client.venues.suggestcompletion(params={'near': curr_location,
                                                      'radius': 250,
                                                      'query': query,
                                                      'limit': RESULT_LIMIT})
    return jsonify(fsq_result)

@app.route('/search', methods=['GET'])
@cross_origin()
def venue_search():
    search_type = request.args.get("search_type")
    curr_location = request.args.get("cl")
    locale = request.args.get("locale")
    fsq_result = None
    map_center = None
    result_geojson = None
    api_get_url = "https://api.foursquare.com/v2/venues/{search_type}?client_id={{client_id}}&client_secret={{client_secret}}&v=20190101&limit=10&radius=250&{ll_or_near}{intent}"
    if search_type == "search":
        try:
            if LATLNG_REGEX.match(curr_location):
                if locale:
                    fsq_result = client.venues.search(params={'ll': curr_location,
                                                              'intent':"browse",
                                                              'radius':250,
                                                              'locale':locale,
                                                              'limit': RESULT_LIMIT})
                    api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="&intent=browse") + "&locale=" + locale
                else:
                    fsq_result = client.venues.search(params={'ll': curr_location,
                                                              'intent':"browse",
                                                              'radius':250,
                                                              'limit': RESULT_LIMIT})
                    api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="&intent=browse")
            else:
                if locale:
                    fsq_result = client.venues.search(params={'near': curr_location,
                                                          'intent':"browse",
                                                          'radius':250,
                                                          'locale':locale,
                                                          'limit': RESULT_LIMIT})
                    api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="&intent=browse") + "&locale=" + locale
                else:
                    fsq_result = client.venues.search(params={'near': curr_location,
                                                          'intent':"browse",
                                                          'radius':250,
                                                          'limit': RESULT_LIMIT})
                    api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="&intent=browse")
        except (foursquare.ParamError,foursquare.FailedGeocode) as e:
            curr_location = "1.2787325314969156,103.8434731966384"
            return redirect("?search_type=search&cl=" + curr_location)

        result_geojson = fsq_result_to_geojson(fsq_result, endpoint="search")
        map_center = fsq_result_calc_center(fsq_result, endpoint="search")
    if search_type == "explore":
        section = ""
        offset = 0
        if "section" in request.args:
            section = request.args.get("section")
        if "offset" in request.args:
            offset = request.args.get("offset")
        if len(section) > 0:
            try:
                if LATLNG_REGEX.match(curr_location):
                    if locale:
                        fsq_result = client.venues.explore(params={'ll': curr_location,
                                                                  'radius':250,
                                                                  'section':section,
                                                                  'locale':locale,
                                                                  'limit': RESULT_LIMIT,
                                                                  'offset': offset})
                        api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="") + "&section=" + section + "&locale=" + locale + "&offset=" + str(offset) + "&limit=" + str(RESULT_LIMIT)
                    else:
                        fsq_result = client.venues.explore(params={'ll': curr_location,
                                                                  'radius':250,
                                                                  'section':section,
                                                                  'limit': RESULT_LIMIT,
                                                                  'offset': offset})
                        api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="") + "&section=" + section + "&offset=" + str(offset) + "&limit=" + str(RESULT_LIMIT)
                else:
                    if locale:
                        fsq_result = client.venues.explore(params={'near': curr_location,
                                                                  'radius':250,
                                                                  'section':section,
                                                                  'locale':locale,
                                                                  'limit': RESULT_LIMIT,
                                                                  'offset': offset})
                        api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="") + "&section=" + section + "&locale=" + locale + "&offset=" + str(offset) + "&limit=" + str(RESULT_LIMIT)
                    else:
                        fsq_result = client.venues.explore(params={'near': curr_location,
                                                                  'radius':250,
                                                                  'section':section,
                                                                  'limit': RESULT_LIMIT,
                                                                  'offset': offset})
                        api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="") + "&section=" + section + "&offset=" + str(offset) + "&limit=" + str(RESULT_LIMIT)
            except (foursquare.ParamError,foursquare.FailedGeocode) as e:
                curr_location = "1.2787325314969156,103.8434731966384"
                return redirect("/search?search_type=explore&cl=" + curr_location + "&section=" + section)

        else:
            try:
                if LATLNG_REGEX.match(curr_location):
                    if locale:
                        fsq_result = client.venues.explore(params={'ll': curr_location,
                                                                  'radius':250,
                                                                  'locale':locale,
                                                                  'limit': RESULT_LIMIT,
                                                                  'offset': offset})
                        api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="") + "&locale=" + locale + "&offset=" + str(offset) + "&limit=" + str(RESULT_LIMIT)
                    else:
                        fsq_result = client.venues.explore(params={'ll': curr_location,
                                                                  'radius':250,
                                                                  'limit': RESULT_LIMIT,
                                                                  'offset': offset})
                        api_get_url = api_get_url.format(search_type=search_type,ll_or_near="ll="+curr_location,intent="") + "&offset=" + str(offset) + "&limit=" + str(RESULT_LIMIT)
                else:
                    if locale:
                        fsq_result = client.venues.explore(params={'near': curr_location,
                                                                  'radius':250,
                                                                  'locale':locale,
                                                                  'limit': RESULT_LIMIT,
                                                                  'offset': offset})
                        api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="") + "&locale=" + locale + "&offset=" + str(offset) + "&limit=" + str(RESULT_LIMIT)
                    else:
                        fsq_result = client.venues.explore(params={'near': curr_location,
                                                                  'radius':250,
                                                                  'limit': RESULT_LIMIT,
                                                                  'offset': offset})
                        api_get_url = api_get_url.format(search_type=search_type,ll_or_near="near="+curr_location,intent="") + "&offset=" + str(offset) + "&limit=" + str(RESULT_LIMIT)
            except (foursquare.ParamError,foursquare.FailedGeocode) as e:
                curr_location = "1.2787325314969156,103.8434731966384"
                return redirect("/search?search_type=explore&cl=" + curr_location)
        result_geojson = fsq_result_to_geojson(fsq_result, endpoint="explore")
        map_center = fsq_result_calc_center(fsq_result, endpoint="explore")
    return jsonify({'result_geojson':result_geojson,'map_center':map_center,'api_get_url':api_get_url,'fsq_result':fsq_result})

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

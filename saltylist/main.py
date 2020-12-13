# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime

# [START gae_python38_auth_verify_token]
from flask import Flask, render_template, request, make_response, jsonify, abort
from google.auth.transport import requests
from google.cloud import datastore
import google.oauth2.id_token

import logging

firebase_request_adapter = requests.Request()
# [END gae_python38_auth_verify_token]

datastore_client = datastore.Client()

app = Flask(__name__)

def find_rule_matches(rules, offset):
    # fake_list = [
    #     {"title": "Play Guitar",
    #     "type": "dow",
    #     "days": [0,2,4]},
    #     {"title": "Weigh In",
    #     "type": "dow",
    #     "days": [0,1,2,3,4,5,6]},
    #     {"title": "Check Portal",
    #     "type": "dow",
    #     "days": [0]},
    #     {"title": "Pay Rent",
    #     "type": "dom",
    #     "days": [1,15]}

    # ]

    # rules = fake_list
    delt = datetime.timedelta(days=offset)
    target_date = datetime.datetime.today() + delt
    dow = target_date.weekday()
    dom = target_date.day


    print("target date is %s" % target_date)
    print("dow is %s" % dow)
    print("dom is %s" % dom)

    arr = []
    
    # Check matching Day of Week rules
    for rl in [x for x in rules if x['type'] == "dow"]:
        if dow in rl["days"]:
            arr.append(rl["title"])
    
    # Check matching Day of Month rules
    for rl in [x for x in rules if x['type'] == "dom"]:
        if dow in rl["days"]:
            arr.append(rl["title"])

    return arr

def store_time(email, dt):
    entity = datastore.Entity(key=datastore_client.key('User', email, 'visit'))
    entity.update({
        'timestamp': dt
    })

    datastore_client.put(entity)

def fetch_times(email, limit):
    ancestor = datastore_client.key('User', email)
    query = datastore_client.query(kind='visit', ancestor=ancestor)
    query.order = ['-timestamp']

    times = query.fetch(limit=limit)

    return times

def fetch_rules(email, limit):
    ancestor = datastore_client.key('User', email)
    query = datastore_client.query(kind='rule', ancestor=ancestor)

    rules = query.fetch(limit=limit)

    return rules

# def get_or_create_rule(


@app.route('/rules.json')
def rules():
    id_token = request.cookies.get("token")
    error_message = None
    body = {}

    if id_token:
        try:
            user = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)


            rules = fetch_rules(user['email'], 50)

            body = {
                "email": user['email'],
                "rules": list(rules)
            }
        except ValueError as exc:
            # This will be raised if the token is expired or any other
            # verification checks fail.
            error_message = str(exc)

    resp = make_response(jsonify(body))
    resp.mimetype = 'application/json'
    return resp

@app.route('/addRule.json')
def addRule():
    id_token = request.cookies.get("token")
    error_message = None
    body = {}

    if id_token:
        try:
            ruleType = request.args.get("type").strip().lower()
            title = request.args.get("title").strip()
            days = [int(x) for x in request.args.get("days").split(",")]

        except:
            print("bad input")
            abort(400)

        try:

            user = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            email = user['email']
            ancestor = datastore_client.key('User', email)

            #print("days: " + days)

            body = {
                'type': ruleType,
                'title': title,
                'days': days
            }

            rule_key = ruleType + "-" + title

            entity = datastore.Entity(key=datastore_client.key('User', email, 'rule', rule_key))
            entity.update(body)

            datastore_client.put(entity)
        except ValueError as exc:
            # This will be raised if the token is expired or any other
            # verification checks fail.
            error_message = str(exc)

    else:
        print("not logged in")
        abort(401)

    resp = make_response(jsonify(body))
    resp.mimetype = 'application/json'
    return resp

@app.route('/today.json')
def today():
    
    try:
        offset = int(request.args.get("offset").strip())
    except:
        offset = 0

    print("offset is %s" % offset)

    body = {
        "name": "Jane Doe",
        "date": datetime.datetime.today(),
        "checks": ["Brush Teeth", "Take Vitamins"],
        "offset": offset
    }
    resp = make_response(jsonify(body))
    resp.mimetype = 'application/json'
    return resp
    
@app.route('/user.json')
def user():
    id_token = request.cookies.get("token")
    error_message = None
    body = {}

    if id_token:
        try:
            offset = int(request.args.get("offset").strip())
        except:
            offset = 0

        print("offset is %s" % offset)
        try:
            user = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)


            rules = fetch_rules(user['email'], 50)
            checks = find_rule_matches(list(rules), offset)

            body = {
                "email": user['email'],
                "checks": checks
            }
        except ValueError as exc:
            # This will be raised if the token is expired or any other
            # verification checks fail.
            error_message = str(exc)
    else:
        print("not logged in")
        abort(401)

    resp = make_response(jsonify(body))
    resp.mimetype = 'application/json'
    return resp


# [START gae_python38_auth_verify_token]
@app.route('/')
def root():
    # Verify Firebase auth.
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    times = None

    if id_token:
        try:
            # Verify the token against the Firebase Auth API. This example
            # verifies the token on each page load. For improved performance,
            # some applications may wish to cache results in an encrypted
            # session store (see for instance
            # http://flask.pocoo.org/docs/1.0/quickstart/#sessions).
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)


            store_time(claims['email'], datetime.datetime.now())
            times = fetch_times(claims['email'], 10)
        except ValueError as exc:
            # This will be raised if the token is expired or any other
            # verification checks fail.
            error_message = str(exc)

    return render_template(
        'index.html',
        user_data=claims, error_message=error_message, times=times)
# [END gae_python38_auth_verify_token]


if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.

    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)

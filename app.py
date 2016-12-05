#!/usr/bin/env python
from flask import Flask, url_for, redirect
from flask import request
from fitbit.api import FitbitOauth2Client
import os
import datetime
import yaml
import rethinkdb as r
from beeprint import pp

CREDS_FILE = 'users.yml'

app = Flask(__name__)



def get_credentials():
    return yaml.load(open(CREDS_FILE))['app']

def get_redirect_url():
    return 'http://localhost:5000' + url_for('token')


def save_token(user):
    with r.connect('rtdb.goodes.net') as conn:
        r.db('fb4s').table('tokens').insert(user, conflict='update').run(conn)

def save_credentials(user_id, code):
    code = code[0]
    user_id = user_id[0]
    print code
    print user_id
    oauth.fetch_access_token(code, get_redirect_url())
    # current = yaml.load(open(CREDS_FILE))
    user = oauth.token
    user['id'] = user_id
    pp(user)
    save_token(user)
    # current[user_id] = user
    # with open(CREDS_FILE, "w") as fp:
    #     yaml.dump(current, fp)

@app.route('/')
def hello_world():
    return '<A HREF="{}">Register</A>'.format(url_for('redirecter', device_id=17))

@app.route('/redirect/<int:device_id>')
def redirecter(device_id):
    state_str = "device_{:04}".format(int(device_id))
    redirect_uri = get_redirect_url()
    url, _ = oauth.authorize_token_url(redirect_uri=redirect_uri, state=state_str)
    return redirect(url)


@app.route('/token/')
def token():
    # show the post with the given id, the id is an integer
    args = dict(request.args)
    save_credentials(args['state'], args['code'])
    return "done"
    return '{}'.format()

creds = get_credentials()
oauth = FitbitOauth2Client(creds['client_id'], creds['client_secret'])


if __name__ == "__main__":
    print get_credentials()
    app.run()

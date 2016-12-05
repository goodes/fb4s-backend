#!/usr/bin/env python
#######################################################################################################################
# Copyright Daniel Goodman 2016 (c)
#######################################################################################################################
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from pyvirtualdisplay import Display
from fitbit_cli import get_password, FitbitWebsite
from beeprint import pp
from bidi import algorithm
from raven import Client
from collections import defaultdict
import math
import yaml

import base64
from xhtml2pdf import pisa             # import python module


import os
import sys
import time
import click
import datetime
import dateutil.parser
import fitbit
import pytz
import plotly.plotly as py
import plotly.offline as pyo
import plotly.graph_objs as go
import rethinkdb as r

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_FILE = '../users.yml'

def get_credentials():
    file_path = os.path.abspath(os.path.join(BASE_DIR, CREDS_FILE))
    return yaml.load(open(file_path))['app']
# <style>
#     @page {{
#         size: letter landscape;
#         margin: 2cm;
#     }}
# </style>
# <strong>{caption}</strong><br>

TEMPLATE = (u"""<html>
<head>
<style>
    @page {{
        size: a4 portrait;
        margin: 1cm;
    }}
</style>
</head>

<body>
<strong>{caption}</strong>
<img style="width: {width}; height: {height}" src="data:image/png;base64,{image_1}">
<br>
<img style="width: {width}; height: {height}" src="data:image/png;base64,{image_2}">
</body>
</html>""".encode('utf-8'))

RTDB_SERVER = 'rtdb.goodes.net'
TZ = pytz.timezone('Israel')
EPOCH_IL = TZ.localize(datetime.datetime(1970, 1, 1))
ACTIVITIES = ['steps', 'minutesSedentary', 'minutesLightlyActive', 'minutesFairlyActive', 'minutesVeryActive']

# sc = Client('https://3ab10cc3de6b43ff85dcbc299fee9ab9:03d274977fef4938ac49d8abbc9fbb13@sentry.io/118250')
sc = Client()


def convert_html_to_pdf(source_html, output_filename):
    # open output file for writing (truncated binary)
    with open(output_filename, "w+b") as result_file:
        # convert HTML to PDF
        pisa_status = pisa.CreatePDF(
                source_html,                # the HTML to convert
                dest=result_file)           # file handle to recieve result

    # return True on success and False on errors
    return pisa_status.err



class FitbitClient:
    def __init__(self, device_id, password=None, verbose=False):
        self.device_id = device_id
        self.password = password
        self.dev_id_str = "{:04}".format(device_id)
        self.dev_id = "device_{}".format(self.dev_id_str)
        self.email = "fb4schl+device{}@gmail.com".format(self.dev_id_str)
        self.student_name = 'Device {}'.format(self.dev_id_str)
        self.client = None
        self.verbose = verbose


    def get_oauth_token(self):
        with r.connect(RTDB_SERVER) as conn:
            token = r.db('fb4s').table('tokens').get(self.dev_id).run(conn)
        if token is None:
            raise KeyError('No token for {}'.format(self.dev_id))
        return token

    def set_oauth_token(self, user):
        user['id'] = self.dev_id
        with r.connect(RTDB_SERVER) as conn:
            r.db('fb4s').table('tokens').insert(user, conflict='update').run(conn)
        if self.verbose:
            click.secho("Updating token for {}".format(self.dev_id), fg='yellow')

    def get_fb_client(self):
        token = self.get_oauth_token()
        # pp(token)
        creds = get_credentials()
        client = fitbit.Fitbit(
                        creds['client_id'],
                        creds['client_secret'],
                        access_token=token['access_token'],
                        refresh_token=token['refresh_token'],
                        refresh_cb=self.set_oauth_token,
                        )
        # pp(client.client.token)
        client.client.refresh_token()
        return client

    def collect_stats(self, start_date, end_date=None):
        end_date = end_date or 'today'
        client = self.get_fb_client()
        device_data = dict()
        click.secho("{} collecting ... ".format(self.dev_id), nl=False)
        for activity_name in ACTIVITIES:
            activity_type = 'activities/{}'.format(activity_name)
            activity_key = 'activities-{}'.format(activity_name)
            response = client.time_series(activity_type, base_date=start_date, end_date=end_date)
            for activity in response[activity_key]:
                year, month, day = activity['dateTime'].split('-')
                ts = TZ.localize(datetime.datetime(int(year), int(month), int(day)))
                # print "{:30} {:20} {:20} {}".format(
                #     self.dev_id, activity['dateTime'], activity_name, activity['value'])
                if ts not in device_data:
                    device_data[ts] = {
                        'id': [self.dev_id, ts],
                        'device_id': self.dev_id,
                        'ts': ts,
                        }
                device_data[ts][activity_name] = int(activity['value'])
        # pp(device_data)
        click.secho("updating ... ", nl=False)
        with r.connect(RTDB_SERVER) as conn:
            r.db('fb4s').table('device_data').insert(device_data.values(), conflict='update').run(conn)
            click.secho("done")

    def get_averages(self, dates):
        data = {}
        for activity_name in ACTIVITIES:
            data[activity_name] = []
        with r.connect(RTDB_SERVER) as conn:
            for entry in r.db('fb4s').table('device_data').filter({'device_id': 'avg'}).order_by('ts').run(conn):
                ts = entry['ts']
                if ts.weekday() not in [4, 5] and ts in dates:
                    for activity_name in ACTIVITIES:
                        data[activity_name].append(entry[activity_name])
        return data
        resp_data = {}
        for activity_name in ACTIVITIES:
            count = len(data[activity_name])
            avg = int(sum(data[activity_name])/float(count))
            # print avg, count
            resp_data[activity_name] = [ avg ] * count
        return resp_data

    def plot(self, device_mappings=None, start_date=None, end_date=None):
        data = {
            'x_axis': []
        }
        for activity_name in ACTIVITIES:
            data[activity_name] = []
        end_date = end_date or TZ.localize(datetime.datetime(2016, 12, 4))
        start_date = start_date or TZ.localize(datetime.datetime(2016, 11, 1))
        with r.connect(RTDB_SERVER) as conn:
            for entry in r.db('fb4s').table('device_data').filter({'device_id': self.dev_id}).order_by('ts').run(conn):
                ts = entry['ts']
                if ts.weekday() not in [4, 5] and start_date <= ts < end_date:
                    data['x_axis'].append(ts)
                    for activity_name in ACTIVITIES:
                        data[activity_name].append(entry.get(activity_name,0))

        averages = self.get_averages(data['x_axis'])

        trace_steps = go.Bar(
            x=data['x_axis'],
            y=data['steps'],
            name='\xd7\xa6\xd7\xa2\xd7\x93\xd7\x99\xd7\x9d',  # 'steps',
            )
        average_steps = go.Scatter(
            x=data['x_axis'],
            y=averages['steps'],
            name='\xd7\xa6\xd7\xa2\xd7\x93\xd7\x99\xd7\x9d (\xd7\x9e\xd7\x9e\xd7\x95\xd7\xa6\xd7\xa2)',  # 'Average Steps',
            line=dict(dash='dash'))

        trace_lightly_active = go.Scatter(x=data['x_axis'], y=data['minutesLightlyActive'], name='Lightly Active')
        trace_fairly_active = go.Bar(
            x=data['x_axis'],
            y=data['minutesFairlyActive'],
            name='\xd7\xa4\xd7\xa2\xd7\x99\xd7\x9c \xd7\x91\xd7\x99\xd7\xa0\xd7\x95\xd7\xa0\xd7\x99',  # 'Fairly Active'
            marker=dict(color='#668cc9'),
            )
        trace_very_active = go.Bar(
            x=data['x_axis'],
            y=data['minutesVeryActive'],
            name='\xd7\xa4\xd7\xa2\xd7\x99\xd7\x9c \xd7\x9e\xd7\x90\xd7\x95\xd7\x93',
            marker=dict(color='orange'),
            )
        average_very_active = go.Scatter(
            x=data['x_axis'],
            y=averages['minutesVeryActive'],
            name='\xd7\xa4\xd7\xa2\xd7\x99\xd7\x9c \xd7\x9e\xd7\x90\xd7\x95\xd7\x93 (\xd7\x9e\xd7\x9e\xd7\x95\xd7\xa6\xd7\xa2)', # 'Average Very Active',
            line=dict(dash='dash', color='red'),

            )
        average_fairly_active = go.Scatter(
            x=data['x_axis'],
            y=[x+y for x, y in zip(averages['minutesFairlyActive'], averages['minutesVeryActive'])],
            name='\xd7\xa4\xd7\xa2\xd7\x99\xd7\x9c \xd7\x91\xd7\x99\xd7\xa0\xd7\x95\xd7\xa0\xd7\x99 (\xd7\x9e\xd7\x9e\xd7\x95\xd7\xa6\xd7\xa2)',  # very active (average)
            line=dict(dash='dash', color='#0000FF')
            )
        # trace_lightly_active = go.Scatter(x=data['x_axis'], y=data['minutesLightlyActive'], yaxis='y2', name='Lightly Active')
        # trace_fairly_active = go.Bar(x=data['x_axis'], y=data['minutesFairlyActive'], yaxis='y2', name='Fairly Active')
        # trace_very_active = go.Bar(x=data['x_axis'], y=data['minutesVeryActive'], yaxis='y2', name='Very Active')
        # average_very_active = go.Scatter(x=data['x_axis'], y=averages['minutesVeryActive'], yaxis='y2', name='Average Very Active', line=dict(dash='dash'))
        # average_fairly_active = go.Scatter(x=data['x_axis'], y=averages['minutesFairlyActive'], yaxis='y2', name='Average Fairly Active', line=dict(dash='dash'))

        student_name = ''
        if device_mappings is not None:
            student_name = device_mappings.get(self.dev_id, self.dev_id).encode('utf-8')
        print student_name

        # trace0 = go.Bar(x=x_axis, y=delete_axis, name='delete')
        # trace1 = go.Bar(x=x_axis, y=create_axis, name='create')
        steps_data = [
            trace_steps,
            average_steps,
            ]
        activity_data = [
            trace_fairly_active,
            trace_very_active,
            average_very_active,
            average_fairly_active
            ]
        plot_spec = {
            'data': steps_data,
            'layout': {
                'barmode': 'group',
                'xaxis': dict(type='date'),
                'yaxis': dict(side='left', title='\xd7\xa6\xd7\xa2\xd7\x93\xd7\x99\xd7\x9d', zeroline=True),
                # 'yaxis2': dict(overlaying='y', side='right', title='Minutes Active', rangemode="tozero", zeroline=True),
                'legend': dict(x=0.0,y=1.0),
                },

            }
        pyo.plot(plot_spec, filename='/tmp/fb4schl.html', auto_open=False)

        activity_plot_spec = {
            'data': activity_data,
            'layout': {
                'barmode': 'overlay',
                'xaxis': dict(type='date'),
                'yaxis': dict(side='left', title='\xd7\x93\xd7\xa7\xd7\x95\xd7\xaa', zeroline=True),
                # 'yaxis2': dict(overlaying='y', side='right', title='Minutes Active', rangemode="tozero", zeroline=True),
                'legend': dict(x=0.0,y=1.0),
                "title": student_name,
                },
            }
        pyo.plot(activity_plot_spec, filename='/tmp/fb4schl_a.html', auto_open=False)

        # pyo.init_notebook_mode()

        width = 770
        height = 550

        image_data_1 = py.image.get(plot_spec, 'png', width=width, height=height, scale=3)  # , width=width, height=height)
        image_data_2 = py.image.get(activity_plot_spec, 'png', width=width, height=height, scale=3)  # , width=width, height=height)
        image_1 = base64.b64encode(image_data_1).decode('utf-8')
        image_2 = base64.b64encode(image_data_2).decode('utf-8')
        # print image
        report_html = TEMPLATE.format(image_1=image_2, image_2=image_1, caption='',
        width=width, height=height)
        with open('/tmp/.html', "w") as rp:
            rp.write(report_html)
        convert_html_to_pdf(report_html, '/tmp/{}.pdf'.format(student_name.encode('utf-8')))

    def get_device_info(self):
        client = self.get_fb_client()

        with r.connect(RTDB_SERVER) as conn:
            current_state = r.db('fb4s').table('device_info').get(self.dev_id).run(conn) or {}

            device_info = client.get_devices()[-1]
            sync_time = TZ.localize(dateutil.parser.parse(device_info['lastSyncTime']))

            update = False
            if sync_time != current_state.get('last_sync', EPOCH_IL):
                r.db('fb4s').table('device_log').insert(
                    dict(device_id=self.dev_id, ts=sync_time, type='sync')
                    ).run(conn)
                update = True

            battery = device_info['battery'].lower()
            old_battery = current_state.get('battery', '')
            if battery != old_battery:
                r.db('fb4s').table('device_log').insert(
                    dict(device_id=self.dev_id, ts=sync_time, type='battery', new=battery, previous=old_battery)
                    ).run(conn)
                update = True

            if update:
                device_entry = dict(
                    id=self.dev_id,
                    fb_id=device_info['id'],
                    last_sync=sync_time,
                    mac=device_info['mac'],
                    battery=battery,
                )
                click.secho("Updating device {:30}: B[{:5}] S[{}]".format(
                    self.dev_id,
                    device_entry['battery'],
                    device_entry['last_sync'].ctime(),
                    ), fg='green')
                r.db('fb4s').table('device_info').insert(device_entry, conflict='update').run(conn)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('device_id', type=int)
@click.option('--end-id', type=int, help="If craeating more the one account, final device_id")
def update_stats(device_id, end_id):
    if end_id is not None:
        if end_id < device_id:
            click.secho("end_id must be greater then device_id", fg='red')
            sys.exit(1)
    else:
        end_id = device_id

    for dev_id in xrange(device_id, end_id+1):
        sc.context.activate()
        sc.context.merge({'device_id': dev_id})
        try:
            fc = FitbitClient(dev_id)
            fc.collect_stats('2016-11-20')
        except Exception as ex:
            sc.captureException()
            print "{:3} {} - {}".format(dev_id, type(ex), str(ex))
        finally:
            sc.context.clear()


@cli.command()
@click.argument('device_id', type=int)
@click.option('--end-id', type=int, help="If craeating more the one account, final device_id")
@click.option('-v', '--verbose', is_flag=True)
def update_device_info(device_id, end_id, verbose):
    if end_id is not None:
        if end_id < device_id:
            click.secho("end_id must be greater then device_id", fg='red')
            sys.exit(1)
    else:
        end_id = device_id

    for dev_id in xrange(device_id, end_id+1):
        sc.context.activate()
        sc.context.merge({'device_id': dev_id})
        try:
            fc = FitbitClient(dev_id, verbose=verbose)
            fc.get_device_info()
        except KeyError as ex:
            if verbose:
                click.secho("Skipping {}".format(dev_id), fg='red')
        except Exception:
            ex_t, ex_v, ex_tb = sys.exc_info()
            sc.captureException()
            click.secho("Error with device {}".format(dev_id), fg='red')
            click.secho(str(ex_v), fg='red')
            # raise ex_t, ex_v, ex_tb
        finally:
            sc.context.clear()


def get_device_mappings(conn):
    t = r.db('fb4s').table('device_mappings')
    s = r.db('fb4s').table('students')
    return dict((x['id'], x['name']) for x in
        t.eq_join('student_id', s).without({'right': "id"}).zip().with_fields('id','name').run(conn))


@cli.command()
@click.argument('device_id', type=int)
@click.option('-a', '--all', is_flag=True)
def plot(device_id, all):
    with r.connect(RTDB_SERVER) as conn:
        device_mappings = get_device_mappings(conn)
    if not all:
        fc = FitbitClient(device_id)
        fc.plot(device_mappings)
    else:
        for key, v in sorted(device_mappings.iteritems()):
            device_id = int(key[-3:])
            print "{} {:4} {}".format(key, device_id, algorithm.get_display(v))
            fc = FitbitClient(device_id)
            fc.plot(device_mappings)


# r.db('fb4s').table('device_info')
#   .filter(r.row("last_sync").lt(r.time(2016, 11, 27, 'Z')))
#   	.orderBy('id')
#   		.withFields('id', 'last_sync')
#

def median(lst):
    lst = sorted(lst)
    if len(lst) < 1:
            return None
    if len(lst) %2 == 1:
            return lst[((len(lst)+1)/2)-1]
    else:
            return float(sum(lst[(len(lst)/2)-1:(len(lst)/2)+1]))/2.0

@cli.command()
def calculate_averages():
    with r.connect(RTDB_SERVER) as conn:
        dates = set([x['ts'] for x in r.db('fb4s').table('device_data').with_fields(['ts']).order_by('ts').run(conn)])
        for date_ts in sorted(dates):
            entries = r.db('fb4s').table('device_data').filter({'ts': date_ts}).run(conn)
            avgs = defaultdict(list)
            for e in entries:
                ignore=False
                for i in ['minutesFairlyActive', 'minutesSedentary', 'minutesVeryActive', 'minutesLightlyActive']:
                    if e.get(i, 0) == 1440:
                        # print "Skipping", e['id']
                        ignore = True
                        break
                if e['device_id'] == 'avg':
                    ignore = True
                if not ignore:
                    # print "continue", e['id']
                    for i in ['minutesFairlyActive', 'minutesSedentary', 'minutesVeryActive', 'minutesLightlyActive', 'steps']:
                        v = e.get(i)
                        if v is not None:
                             avgs[i].append(v)
            print date_ts.ctime()
            avg_data = {}
            for k, v in avgs.iteritems():
                print "{:20} | {:>8.2f}".format(k, sum(v)/float(len(v)))
                # avg_data[k] = round(sum(v)/float(len(v)), 2)
                avg_data[k] = median(v)
            avg_data["device_id"] = 'avg'
            avg_data['ts'] = date_ts
            avg_data['id'] = ['avg', date_ts]
            r.db('fb4s').table('device_data').insert(avg_data, conflict='replace').run(conn)

@cli.command()
@click.argument('days', type=int)
def show_missing(days):
    delta = datetime.timedelta(days=days)
    now = TZ.localize(datetime.datetime.now())
    ts = now.replace(hour=0, minute=0, second=0, microsecond=0) - delta
    click.secho(ts.ctime())
    with r.connect(RTDB_SERVER) as conn:
        device_mappings = get_device_mappings(conn)
        table = r.db('fb4s').table('device_info')
        missing = table.filter(r.row["last_sync"].lt(ts)).order_by('id').with_fields('id', 'last_sync').run(conn)
        for e in missing:
            device = e['id']
            click.secho("{:30} {:40} {}".format(
                device,
                algorithm.get_display(device_mappings.get(device, 'unknown')),
                str(datetime.timedelta(seconds=int((now - e['last_sync']).total_seconds()))),
            ))

@cli.command()
def show_students():
    with r.connect(RTDB_SERVER) as conn:
        device_mappings = get_device_mappings(conn)
        for key, v in sorted(device_mappings.iteritems()):
            device_id = int(key[-3:])
            print "{} {:4} {}".format(key, device_id, algorithm.get_display(v))

if __name__ == "__main__":
    cli()

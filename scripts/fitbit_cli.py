#!/usr/bin/env python
#######################################################################################################################
# Copyright Daniel Goodman 2016 (c)
#######################################################################################################################
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from pyvirtualdisplay import Display
from raven import Client
import os
import sys
import time
import click
import datetime

now_ts = datetime.datetime.now()
today = now_ts.strftime("%h %-d")

ACCOUNT_NAME_FMT = "fb4schl+device{}@gmail.com"
ENV_PASSWD = "FITBIT_USER_PASSWORD"

# 3 lost 2016-11-18
# 4 DOA
SKIPS = [4, 39, 40, 41, 42]

class SeleniumHelper:
    def set_id(self, element, key, value, clear=True):
        e = element.find_element_by_id(key)
        if clear:
            e.clear()
        e.send_keys(value)

    def set_select_value(self, element, key, value):
        sel = Select(element.find_element_by_id(key))
        sel.select_by_value(value)

    def set_radio_value(self, element, key, value):
        sel = Radio(element.find_element_by_id(key))
        sel.select_by_value(value)

    def set_name(self, element, key, value, clear=True):
        e = element.find_element_by_name(key)
        if clear:
            e.clear()
        e.send_keys(value)

    def set_radio_click(self, element, key):
        element.find_element_by_id(key).click()

    def click_name(self, element, key):
        element.find_element_by_name(key).click()

    def sleep_for(self, secs, message=None, quiet=False):
        if message is not None:
            print message
        for sec in xrange(secs, 0, -1):
            if not quiet:
                print "sleeping {}".format(sec)
            time.sleep(1)


class FitbitWebsite(SeleniumHelper):
    def __init__(self):
        # self.driver = webdriver.Chrome()
        self.display = Display(visible=0, size=(1920, 1080))
        self.display.start()
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(30)
        self.base_url = "https://www.fitbit.com/"
        self.verificationErrors = []
        self.accept_next_alert = True

    def close(self):
        self.display.stop()
        self.driver.close()
        self.driver.quit()

    def login(self, email, password):
        self.driver.get(os.path.join(self.base_url, "login"))
        e = self.driver.find_element_by_id('loginForm')
        self.set_name(e, 'email', email)
        self.set_name(e, 'password', password)
        self.click_name(e, 'rememberMe')
        e.find_element_by_class_name("track-Auth-Login-ClickFitbit").click()

    def logout(self):
        self.driver.get(os.path.join(self.base_url, "logout"))
        # driver.find_element_by_css_selector("span.icon").click()
        # driver.find_element_by_link_text("Log Out").click()

    def set_timezone(self):
        self.driver.get(os.path.join(self.base_url, "user/profile/edit"))
        e = self.driver.find_element_by_id('editProfile')
        self.set_select_value(e, 'timezone', 'Asia/Jerusalem')
        # doing a submit() on the form does not seem to work, so instead
        # we'll click on the save button
        self.click_name(e, 'save')

    def edit_profile(self, student_name):
        self.driver.get(os.path.join(self.base_url, "user/profile/edit"))
        e = self.driver.find_element_by_id('editProfile')
        self.set_id(e, 'fullname', student_name)
        self.set_select_value(e, 'country', 'IL')
        self.set_select_value(e, 'heightSystem', 'METRIC')
        self.set_select_value(e, 'weightSystem', 'METRIC')
        self.set_select_value(e, 'gender', 'FEMALE')
        self.set_name(e, 'birthMonth', '1')
        self.set_name(e, 'birthDayOfMonth', '1')
        self.set_name(e, 'birthYear', '1990')
        self.set_id(e, 'heightCM', '100')
        self.set_id(e, 'kg', '50')
        self.set_radio_click(e, 'startsSunday')
        self.set_select_value(e, 'clock', '24')
        self.set_select_value(e, 'timezone', 'Asia/Jerusalem')
        # doing a submit() on the form does not seem to work, so instead
        # we'll click on the save button
        self.click_name(e, 'save')

    def create_account(self, email, password, student_name):
        driver = self.driver
        driver.get(self.base_url + "/signup")
        driver.find_element_by_name("email").clear()
        driver.find_element_by_name("email").send_keys(email)
        driver.find_element_by_name("password").clear()
        driver.find_element_by_name("password").send_keys(password)
        driver.find_element_by_id("termsPrivacyConnected").click()
        driver.find_element_by_id("emailSubscribeConnected").click()
        driver.find_element_by_xpath("//button[@type='submit']").click()
        self.sleep_for(5)
        driver.find_element_by_id("fullname").clear()
        driver.find_element_by_id("fullname").send_keys(student_name)
        driver.find_element_by_id("gender-button").click()
        driver.find_element_by_id("gender-button").send_keys(Keys.DOWN)
        driver.find_element_by_name("birthMonth").clear()
        driver.find_element_by_name("birthMonth").send_keys("1")
        driver.find_element_by_name("birthDayOfMonth").clear()
        driver.find_element_by_name("birthDayOfMonth").send_keys("1")
        driver.find_element_by_name("birthYear").clear()
        driver.find_element_by_name("birthYear").send_keys("1990")
        driver.find_element_by_css_selector("div.nobr").click()
        driver.find_element_by_id("heightCM").clear()
        driver.find_element_by_id("heightCM").send_keys("100")
        driver.find_element_by_css_selector("#fitbitSelect_2 > div.nobr").click()
        driver.find_element_by_css_selector("#fitbitSelect_2 > div.nobr").click()
        driver.find_element_by_id("field-weight-kg").clear()
        driver.find_element_by_id("field-weight-kg").send_keys("50")
        driver.find_element_by_id("complete-profile-submit").click()
        self.sleep_for(10)
        # driver.find_element_by_css_selector("span.icon").click()
        # driver.find_element_by_xpath("//a[contains(text(),'Settings')]").click()
        # driver.find_element_by_xpath("//a[contains(text(),'Settings')]").click()
        # Select(driver.find_element_by_id("timezone")).select_by_visible_text("(GMT+03:00) Tel Aviv")
        # driver.find_element_by_name("save").click()
        # print "sleeping"
        # time.sleep(5)
        # driver.find_element_by_css_selector("span.icon").click()
        # driver.find_element_by_link_text("Log Out").click()
        # self.sleep_for(2)

    def go_to_device_info_page(self):
        driver = self.driver
        driver.find_element_by_css_selector("span.icon").click()
        driver.find_element_by_css_selector("span.sync.deviceDetail").click()

    def get_device_id(self):
        driver = self.driver
        return str(os.path.split(driver.current_url)[-1])

    def get_last_sync(self):
        driver = self.driver
        date_stamp = driver.find_element_by_class_name("lastSyncTime").text.replace('Today', today)
        return datetime.datetime.strptime(date_stamp, '%b %d at %I:%M%p').replace(year=2016)

    def edit_device(self, distance=None, calories=None, clock=None, smiley=None):
        driver = self.driver
        driver.find_element_by_css_selector("span.icon").click()
        driver.find_element_by_css_selector("span.sync.deviceDetail").click()
        for li_id, item in enumerate([distance, calories, clock, smiley]):
            if item is not None:
                element = driver.find_element_by_xpath(
                    "//div[@id='profile_body']/div/div/div[2]/div/ul/li[{}]/div/a".format(li_id + 1))
                print li_id, item, element.text
                if (item and element.text == 'OFF') or (not item and element.text == 'ON'):
                    element.click()

    def device_id_to_serial(self, device_id):
        order = [6, 5, 4, 3, 2, 1]
        return "".join([device_id[(offset-1)*2:(offset*2)].upper() for offset in order])

    def serial_to_device_id(self, serial):
        order = [6, 5, 4, 3, 2, 1]
        return "".join([serial[(offset-1)*2:(offset*2)].lower() for offset in order])

    def resend_verify(self):
        driver = self.driver
        # print driver.find_element_by_css_selector("span.exit").text
        print "looking for resend"
        driver.find_element_by_class_name('resend_verification_email').click()
        # # print driver.find_element_by_xpath("//div[16]/div[2]/div/div/i").text
        # driver.find_element_by_xpath("//div[16]/div[2]/div/div/i").click()

def format_timedelta(dt):
    return "{} days {:02}:{:02}".format(int(dt.days), int(dt.seconds/3600), int(dt.seconds/60) % 60)

def get_password(password=None):
    password = password or os.getenv(ENV_PASSWD, None)
    if password is None:
        click.secho(
            "No password specified. Please specify option --password' or define env var '{}'".format(ENV_PASSWD),
            fg='red'
            )
        sys.exit(1)
    return password

@click.group()
# @click.argument('device_id', type=int)
# @click.option('--password', type=str, help="Specify the user password")
# @click.option('--end-id', type=int, help="If craeating more the one account, final device_id")
def cli():
    pass

@cli.command(help="Create a new account")
@click.argument('device_id', type=int)
@click.option('--password', type=str, help="Specify the user password")
@click.option('--end-id', type=int, help="If craeating more the one account, final device_id")
def create_account(device_id, password, end_id):
    password = get_password(password)

    if end_id is not None:
        if end_id < device_id:
            click.secho("end_id must be greater then device_id", fg='red')
            sys.exit(1)
    else:
        end_id = device_id

    client = FitbitWebsite()
    click.secho('Using password: {}'.format(password), fg='yellow')
    for dev_id in xrange(device_id, end_id+1):
        dev_id_str = "{:04}".format(dev_id)
        email = "fb4schl+device{}@gmail.com".format(dev_id_str)
        student_name = 'Device {}'.format(dev_id_str)
        click.secho("Creating device {} {:>35} / {}".format(dev_id_str, email, student_name), fg='green')
        client.create_account(email, password, student_name)
        client.sleep_for(5)
        client.logout()
    client.close()

@cli.command(help="Update account time zone")
@click.argument('device_id', type=int)
@click.option('--password', type=str, help="Specify the user password")
@click.option('--end-id', type=int, help="If craeating more the one account, final device_id")
def set_timezone(device_id, password, end_id):
    password = get_password(password)

    if end_id is not None:
        if end_id < device_id:
            click.secho("end_id must be greater then device_id", fg='red')
            sys.exit(1)
    else:
        end_id = device_id

    client = FitbitWebsite()
    click.secho('Using password: {}'.format(password), fg='yellow')
    for dev_id in xrange(device_id, end_id+1):
        dev_id_str = "{:04}".format(dev_id)
        email = "fb4schl+device{}@gmail.com".format(dev_id_str)
        student_name = 'Device {}'.format(dev_id_str)
        click.secho("Creating device {} {:>35} / {}".format(dev_id_str, email, student_name), fg='green')
        client.login(email, password)
        try:
            client.sleep_for(5, quiet=True)
            # client.sleep_for(5)
            # client.resend_verify()
            client.set_timezone()
            client.sleep_for(5, quiet=True)
            client.edit_device(calories=False, distance=True, smiley=True, clock=None)
        except Exception as ex:
            click.secho(str(ex), fg='red')
            click.secho(str(type(ex)), fg='red')
        client.sleep_for(5, quiet=True)
        client.logout()
        # client.create_account(email, password, student_name)
    client.close()

@cli.command(help="List device identifers")
@click.argument('device_id', type=int)
@click.option('--password', type=str, help="Specify the user password")
@click.option('--end-id', type=int, help="If craeating more the one account, final device_id")
def get_device_ids(device_id, password, end_id):
    password = get_password(password)

    if end_id is not None:
        if end_id < device_id:
            click.secho("end_id must be greater then device_id", fg='red')
            sys.exit(1)
    else:
        end_id = device_id

    client = FitbitWebsite()
    # click.secho('Using password: {}'.format(password), fg='yellow')
    try:
        for dev_id in xrange(device_id, end_id+1):
            if dev_id in SKIPS:
                continue
            dev_id_str = "{:04}".format(dev_id)
            email = "fb4schl+device{}@gmail.com".format(dev_id_str)
            student_name = 'Device {}'.format(dev_id_str)
            client.login(email, password)
            client.sleep_for(2, quiet=True)
            try:
                client.go_to_device_info_page()
                client.sleep_for(2, quiet=True)
                device_serial = client.get_device_id()
                last_sync = format_timedelta((now_ts - client.get_last_sync()))
            except NoSuchElementException:
                device_serial = "NOT FOUND"
                last_sync = "NOT FOUND"
            click.secho("{}\t{}\t{}".format(student_name, device_serial, last_sync))
            client.logout()
    finally:
        client.close()

@cli.command(help="Update teh auth token for the device")
@click.argument('device_id', type=int)
@click.option('--password', type=str, help="Specify the user password")
@click.option('--end-id', type=int, help="If craeating more the one account, final device_id")
def get_auth_token(device_id, password, end_id):
    password = get_password(password)

    if end_id is not None:
        if end_id < device_id:
            click.secho("end_id must be greater then device_id", fg='red')
            sys.exit(1)
    else:
        end_id = device_id

    client = FitbitWebsite()
    # click.secho('Using password: {}'.format(password), fg='yellow')
    redirect_uri = "http://localhost:5000/redirect/{}"
    try:
        for dev_id in xrange(device_id, end_id+1):
            if dev_id in SKIPS:
                continue
            dev_id_str = "{:04}".format(dev_id)
            email = "fb4schl+device{}@gmail.com".format(dev_id_str)
            student_name = 'Device {}'.format(dev_id_str)
            client.logout()
            client.login(email, password)
            client.sleep_for(2, quiet=True)
            state = "UNKNOWN"
            try:
                client.driver.get(redirect_uri.format(dev_id))
                client.sleep_for(2, quiet=True)
                if client.driver.title == u'App Authorization':
                    client.driver.find_element_by_id("allow-button").click()
                client.sleep_for(2, quiet=True)
                if client.driver.title == u'' and 'done' in client.driver.page_source:
                    state = "SUCCESS"
                client.logout()
            except NoSuchElementException:
                state = "SUCCESS"
            click.secho("{}\t{}".format(student_name,state))
            client.logout()
    finally:
        client.close()

if __name__ == "__main__":
    sc = Client('https://3ab10cc3de6b43ff85dcbc299fee9ab9:03d274977fef4938ac49d8abbc9fbb13@sentry.io/118250')
    try:
        cli()
    except:
        a, b, c = sys.exc_info()
        sc.captureException()
        raise a, b, c

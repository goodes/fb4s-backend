# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import NoAlertPresentException
import unittest, time, re

class GetAuth(unittest.TestCase):
    def setUp(self):
        self.driver = webdriver.Firefox()
        self.driver.implicitly_wait(30)
        self.base_url = "http://localhost:5000/"
        self.verificationErrors = []
        self.accept_next_alert = True
    
    def test_get_auth(self):
        driver = self.driver
        driver.get(self.base_url + "/")
        driver.find_element_by_link_text("Register").click()
        driver.find_element_by_link_text("Register").click()
        driver.find_element_by_css_selector("#loginForm > fieldset > dl.field-group > dd > input[name=\"email\"]").clear()
        driver.find_element_by_css_selector("#loginForm > fieldset > dl.field-group > dd > input[name=\"email\"]").send_keys("fb4schl+device0025@gmail.com")
        driver.find_element_by_css_selector("#loginForm > fieldset > dl.field-group > dd > input[name=\"email\"]").clear()
        driver.find_element_by_css_selector("#loginForm > fieldset > dl.field-group > dd > input[name=\"email\"]").send_keys("fb4schl+device0025@gmail.com")
        driver.find_element_by_css_selector("#loginForm > fieldset > dl.field-group > dd > input[name=\"email\"]").clear()
        driver.find_element_by_css_selector("#loginForm > fieldset > dl.field-group > dd > input[name=\"email\"]").send_keys("fb4schl+device0017@gmail.com")
        driver.find_element_by_css_selector("#loginForm > fieldset > dl.field-group > dd > input[name=\"email\"]").clear()
        driver.find_element_by_css_selector("#loginForm > fieldset > dl.field-group > dd > input[name=\"email\"]").send_keys("fb4schl+device0017@gmail.com")
        # ERROR: Caught exception [Error: Dom locators are not implemented yet!]
        # ERROR: Caught exception [Error: Dom locators are not implemented yet!]
        driver.find_element_by_id("rememberMe").click()
        driver.find_element_by_id("rememberMe").click()
        driver.find_element_by_xpath("(//button[@type='submit'])[2]").click()
        driver.find_element_by_xpath("(//button[@type='submit'])[2]").click()
        driver.find_element_by_id("allow-button").click()
        driver.find_element_by_id("allow-button").click()
        driver.find_element_by_id("allow-button").click()
        driver.find_element_by_id("allow-button").click()
        driver.find_element_by_id("allow-button").click()
        driver.find_element_by_id("allow-button").click()
        driver.find_element_by_css_selector("span.icon").click()
        driver.find_element_by_link_text("Log Out").click()
        driver.find_element_by_link_text("Log Out").click()
    
    def is_element_present(self, how, what):
        try: self.driver.find_element(by=how, value=what)
        except NoSuchElementException as e: return False
        return True
    
    def is_alert_present(self):
        try: self.driver.switch_to_alert()
        except NoAlertPresentException as e: return False
        return True
    
    def close_alert_and_get_its_text(self):
        try:
            alert = self.driver.switch_to_alert()
            alert_text = alert.text
            if self.accept_next_alert:
                alert.accept()
            else:
                alert.dismiss()
            return alert_text
        finally: self.accept_next_alert = True
    
    def tearDown(self):
        self.driver.quit()
        self.assertEqual([], self.verificationErrors)

if __name__ == "__main__":
    unittest.main()

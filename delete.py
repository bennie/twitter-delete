#!/usr/bin/env python3
""" Delete the content out of your twitter account
"""

# Written with the aid of this tutorial and it's example code:
# https://www.geeksforgeeks.org/twitter-automation-using-selenium-python/

import time

from pprint import pprint
from selenium import webdriver
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options

def get_credentials() -> dict:
    credentials = dict()
    with open('credentials.txt') as f:
        for line in f.readlines():
            try:
                key, value = line.split(": ")
            except ValueError:
                print('Add your email and password in credentials file')
                exit(0)
            credentials[key] = value.rstrip(" \n")
    return credentials

def login(creds):
	firefox_options = Options()
	firefox_options.add_argument('--width=1200')
	firefox_options.add_argument('--height=1800')

	brows = webdriver.Firefox(options = firefox_options)
	brows.implicitly_wait(2)

	brows.get(f'https://twitter.com/i/flow/login?redirect_after_login=%2F{creds["username"]}')
	time.sleep(2)

	username = brows.find_element("xpath", '//input[@type="text"]')
	username.send_keys(creds["username"])
	username.send_keys(Keys.RETURN)
	time.sleep(2)

	password = brows.find_element("xpath", '//input[@type="password"]')
	password.send_keys(creds['password'])
	password.send_keys(Keys.RETURN)
	time.sleep(2)

	return brows

def find_more_links(brows):
	more_links = []
	svgs = brows.find_elements("xpath", "//div[contains(@aria-label, 'Timeline') and contains(@aria-label, 'posts')]//*[name()='svg']")
	for svg in svgs:
		if "M3 12c0-1.1.9-2 2-2s2 .9 2 2-.9 2-2 2-2-.9-2-2zm9" in svg.get_attribute('innerHTML'):
			more_links.append(svg)
	return more_links

def try_to_delete(brows) -> bool:
	# Click on the option to "Delete" that shows up in the menu
	try:
		elem = brows.find_element("xpath", "//span[text()='Delete']")
		elem.click()
	except NoSuchElementException:
		print("It doesn't look like we can delete things...")
		return False

	# Confirm the delete
	elem = brows.find_element("xpath", "//span[text()='Delete']")
	elem.click()

	time.sleep(1)
	return True

def main():
	creds = get_credentials()
	brows = login(creds)
	actions = ActionChains(brows)

	# Load the profile and start deleting tweets

	brows.get(f'https://twitter.com/{creds["username"]}')
	time.sleep(2)

	delete_count = 0
	reply_count = 0
	repost_count = 0

	while True:
		# Find the "..." SVG and click on it
		more_links = find_more_links(brows)

		if len(more_links) < 1:
			print("No links to click and delete...")
			break

		more_links[0].click()

		didit = try_to_delete(brows)

		if didit:
			print("Deleted tweet...")
			delete_count += 1
		else:
			print("Seems to be nothing to delete...")
			break

	print(f'{delete_count} tweets deleted')
	time.sleep(2)

	# Remove replies

	while True:
		brows.get(f'https://twitter.com/{creds["username"]}/with_replies')
		time.sleep(2)

		last_pass = reply_count

		more_links = find_more_links(brows)

		for link in more_links:
			link.click()

			didit = try_to_delete(brows)

			if didit:
				print("Deleted reply...")
				reply_count += 1
			else:
				actions.send_keys(Keys.ESCAPE).perform()

		if last_pass == reply_count:
			# We did a loop and had zero deletes
			break

	print(f'{reply_count} tweet replies deleted')
	time.sleep(2)

	brows.close()

if __name__ == '__main__':
    main()
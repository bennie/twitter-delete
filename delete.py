#!/usr/bin/env python3
""" Delete the content out of your twitter account
"""

# Written with the aid of this tutorial and it's example code:
# https://www.geeksforgeeks.org/twitter-automation-using-selenium-python/

import json
import os
import time
import sys

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

DELETE_COUNT = None
ERROR_COUNT = None
TWEET_IDS = None
LOGFILE = None

def find_more_links(brows):
    """ Find any of the '...' links """
    more_links = []
    svgs = brows.find_elements("xpath", "//article[contains(@tabindex, '-1')]//*[name()='svg']")
    for svg in svgs:
        try:
            if "M3 12c0-1.1.9-2 2-2s2 .9 2 2-.9 2-2 2-2-.9-2-2zm9" in svg.get_attribute('innerHTML'):
                more_links.append(svg)
        except StaleElementReferenceException:
            # Tweets can contain SVGs and we might have removed those in passing. So skip any stale refs
            pass
    return more_links

def find_repost_links(brows):
    """ Find any repost icons that show green """
    repost_links = []
    svgs = brows.find_elements("xpath", "//div[contains(@style, 'rgb(0, 186, 124)')]//*[name()='svg']")
    for svg in svgs:
        if "M4.75 3.79l4.603 4.3-1.706 1.82L6 8.38v7.37c0 .97.784" in svg.get_attribute('innerHTML'):
            repost_links.append(svg)
    return repost_links

def firefox_scroll(brows, element):
    """ scroll to a given element on the screen """
    y_loc = element.location['y']
    y_loc -= 120  # We're gonna scroll past the link
    script = f'window.scrollTo(1,{y_loc});'  # x is 1 to avoid actually hovering over the element
    brows.execute_script(script)

def get_credentials() -> dict:
    """ Read user and pass from credentials.txtr """
    credentials = {}
    with open('credentials.txt') as file:
        for line in file.readlines():
            try:
                key, value = line.split(": ")
            except ValueError:
                print('Add your email and password in credentials file')
                sys.exit(0)
            credentials[key] = value.rstrip(" \n")
    return credentials

def login(creds):
    """ Login to Twitter """
    firefox_options = Options()
    firefox_options.add_argument('--width=1200')
    firefox_options.add_argument('--height=1600')

    brows = webdriver.Firefox(options=firefox_options)
    brows.implicitly_wait(2)
    brows.set_page_load_timeout(20)

    brows.get(f'https://twitter.com/i/flow/login?redirect_after_login=%2F{creds["username"]}')

    username = WebDriverWait(brows, 20).until(EC.visibility_of_element_located((By.XPATH, '//input[@type="text"]')))
    username.send_keys(creds["username"])
    username.send_keys(Keys.RETURN)

    password = WebDriverWait(brows, 20).until(EC.visibility_of_element_located((By.XPATH, '//input[@type="password"]')))
    password.send_keys(creds['password'])
    password.send_keys(Keys.RETURN)

    time.sleep(2)
    return brows

def try_to_delete(brows, actions, more_link) -> bool:
    """ Given a link, try to delete the tweet. """
    try:
        firefox_scroll(brows, more_link)
        more_link.click()
    except StaleElementReferenceException:
        # Reposts can contain "..." and we might have removed those in passing. So skip any stale refs
        pass

    # Click on the option to "Delete" that shows up in the menu
    try:
        elem = brows.find_element("xpath", "//span[text()='Delete']")
        elem.click()
    except NoSuchElementException:
        print("Nope...")
        actions.send_keys(Keys.ESCAPE).perform()
        return False

    # Confirm the delete
    elem = brows.find_element("xpath", "//span[text()='Delete']")
    elem.click()
    return True

def try_undo_repost(brows, actions, repost_link) -> bool:
    """ Given a link, try to un-repost. """
    try:
        firefox_scroll(brows, repost_link)  # Firefox doesn't scroll on move_to_element() - work around with Javascript
    except StaleElementReferenceException:
        return False

    actions.move_to_element(repost_link).click().perform()

    elem = WebDriverWait(brows, 20).until(EC.visibility_of_element_located((By.XPATH, "//span[text()='Undo repost']")))
    elem.click()
    return True

def delete_all_the_twitter_things():
    """ Login and try to delete every tweetid we have """
    global DELETE_COUNT, ERROR_COUNT, TWEET_IDS, LOGFILE

    print("Loggin in.")
    creds = get_credentials()
    brows = login(creds)
    actions = ActionChains(brows)

    time.sleep(2)

    for tweet_id in TWEET_IDS:
        url = f'https://x.com/{creds["username"]}/status/{tweet_id}'
        print(url)
        if brows.current_url != url:
            try:
                brows.get(url)
            except TimeoutException:
                brows.refresh()
                print("Reloading the page...")
            time.sleep(2)

        if "Hmm...this page doesn’t exist. Try searching for something else." in brows.page_source:
            print("Dead page.")
            LOGFILE.write(f"{tweet_id} DEAD\n")
            time.sleep(2)
            continue

        # Look for the "..." and see if we can delete
        more_links = find_more_links(brows)

        didit = False
        if len(more_links) > 0:
            didit = try_to_delete(brows, actions, more_links[0])
            if didit:
                print("Deleted tweet...")
                LOGFILE.write(f"{tweet_id} DELETED\n")
                DELETE_COUNT += 1
                time.sleep(2)

        # Maybe it's a repost?
        if not didit:
            # find green repost links, click on them to un-repost
            repost_links = find_repost_links(brows)

            if len(repost_links) > 0:
                didit = try_undo_repost(brows, actions, repost_links[0])

                if didit:
                    DELETE_COUNT += 1
                    LOGFILE.write(f"{tweet_id} UNREPOST\n")
                    print("Deleted repost...")
                    time.sleep(2)

        if not didit:
            LOGFILE.write(f"{tweet_id} NOPE\n")
            ERROR_COUNT += 1

    brows.close()

def main():
    """ The main program -- do I really need to docstring this? """
    global DELETE_COUNT, ERROR_COUNT, TWEET_IDS, LOGFILE
    DELETE_COUNT = 0
    ERROR_COUNT = 0
    TWEET_IDS = []

    with open('tweets.js') as file:
        _, raw_data = file.read().split('=',1)
        data = json.loads(raw_data)
        for i in data:
            TWEET_IDS.append(i["tweet"]["id_str"])

    print(len(TWEET_IDS), "tweet IDs found to delete.")

    # Read any work done, and remove from tweet list
    already_done = 0
    if os.access("twitter-delete.log", os.R_OK):
        file = open("twitter-delete.log", "r")
        for line in file:
            if " " in line:
                tweetid, _ = line.split(" ")
                TWEET_IDS.remove(tweetid)
                already_done += 1

    if already_done > 0:
        print(f"{already_done} tweet ids already done, skipping.")
        print(len(TWEET_IDS), "tweet IDs left to delete.")

    TWEET_IDS.sort()

    # Open LOGFILE to write

    LOGFILE = open("twitter-delete.log", "a")

    # Global try/catch is bad m'kay
    # Except when it is appropriate
    try:
        delete_all_the_twitter_things()
    except TimeoutException:
        print("\nERROR: Timeout Exception")
        print("Stopping... try again to delete more")
    except KeyboardInterrupt:
        print("\nERROR: Caught Interrupt")
        print("Stopping...")

    print("\nTotals:")
    print(f'{DELETE_COUNT} tweets deleted')
    print(f'{ERROR_COUNT} tweets couldn\'t be deleted')


if __name__ == '__main__':
    main()

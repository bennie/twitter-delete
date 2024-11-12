#!/usr/bin/env python3
""" Delete the content out of your twitter account
"""

# Written with the aid of this tutorial and it's example code:
# https://www.geeksforgeeks.org/twitter-automation-using-selenium-python/

import json

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


def find_more_links(brows):
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
    repost_links = []
    svgs = brows.find_elements("xpath", "//div[contains(@style, 'rgb(0, 186, 124)')]//*[name()='svg']")
    for svg in svgs:
        if "M4.75 3.79l4.603 4.3-1.706 1.82L6 8.38v7.37c0 .97.784" in svg.get_attribute('innerHTML'):
            repost_links.append(svg)
    return repost_links

def firefox_scroll(brows, element):
    y = element.location['y']
    y -= 120  # We're gonna scroll past the link
    script = f'window.scrollTo(1,{y});'  # x is 1 to avoid actually hovering over the element
    brows.execute_script(script)

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
    firefox_options.add_argument('--height=800')

    brows = webdriver.Firefox(options=firefox_options)
    brows.implicitly_wait(2)

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
    try:
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
    try:
        firefox_scroll(brows, repost_link)  # Firefox doesn't scroll on move_to_element() - work around with Javascript
    except StaleElementReferenceException:
        return False

    actions.move_to_element(repost_link).click().perform()

    elem = WebDriverWait(brows, 20).until(EC.visibility_of_element_located((By.XPATH, "//span[text()='Undo repost']")))
    elem.click()
    return True

def delete_all_the_twitter_things():
    global delete_count, error_count, tweet_ids

    print("Loggin in.")
    creds = get_credentials()
    brows = login(creds)
    actions = ActionChains(brows)

    time.sleep(2)

    for tweet_id in tweet_ids:
        url = f'https://x.com/{creds["username"]}/status/{tweet_id}'
        if brows.current_url != url:
            brows.get(url)
            time.sleep(2)

        print(url)

        if "Hmm...this page doesn’t exist. Try searching for something else." in brows.page_source:
            print("Dead page.")
            continue

        # Look for the "..." and see if we can delete
        more_links = find_more_links(brows)

        didit = False
        if len(more_links) > 0:
            didit = try_to_delete(brows, actions, more_links[0])
            if didit:
                print("Deleted tweet...")
                delete_count += 1

        # Maybe it's a repost?
        if not didit:
            # find green repost links, click on them to un-repost
            repost_links = find_repost_links(brows)

            if len(repost_links) > 0:
                didit = try_undo_repost(brows, actions, repost_links[0])

                if didit:
                    delete_count += 1
                    print("Deleted repost...")

        if not didit:
            error_count += 1

        time.sleep(2)

    brows.close()

def main():
    global delete_count, error_count, tweet_ids
    delete_count = 0
    error_count = 0
    tweet_ids = []

    with open('tweets.js') as file:
        _, raw_data = file.read().split('=',1)
        data = json.loads(raw_data)
        for i in data:
            tweet_ids.append(i["tweet"]["id_str"])

    print(len(tweet_ids), "tweet IDs found to delete.")

    tweet_ids.sort()

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
    print(f'{delete_count} tweets deleted')
    print(f'{error_count} tweets couldn\'t be deleted')


if __name__ == '__main__':
    main()

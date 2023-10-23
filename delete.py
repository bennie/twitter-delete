#!/usr/bin/env python3
""" Delete the content out of your twitter account
"""

# Written with the aid of this tutorial and it's example code:
# https://www.geeksforgeeks.org/twitter-automation-using-selenium-python/

import time

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


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


def find_repost_links(brows):
    repost_links = []
    svgs = brows.find_elements("xpath", "//div[contains(@style, 'rgb(0, 186, 124)')]//*[name()='svg']")
    for svg in svgs:
        if "M4.75 3.79l4.603 4.3-1.706 1.82L6 8.38v7.37c0 .97.784" in svg.get_attribute('innerHTML'):
            repost_links.append(svg)
    return repost_links


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

    url = f'https://twitter.com/{creds["username"]}'
    if brows.current_url != url:
        brows.get(url)
        time.sleep(2)

    print(url)

    delete_count = 0
    reply_count = 0
    repost_count = 0

    while True:
        # find green repost links, click on them to un-repost
        repost_links = find_repost_links(brows)

        if len(repost_links) > 0:
            actions.move_to_element(repost_links[0]).click().perform()
            repost_count += 1
            print("Deleted repost...")
            continue

        # Find the "..." SVG and click on it
        more_links = find_more_links(brows)

        if len(more_links) > 0:
            more_links[0].click()

            didit = try_to_delete(brows)

            if didit:
                print("Deleted tweet...")
                delete_count += 1
                continue
            else:
                print("Seems to be nothing to delete...")
                actions.send_keys(Keys.ESCAPE).perform()
                continue

        if len(more_links) < 1 and len(repost_links) < 1:
            break

    print(f'{delete_count} tweets deleted')
    print(f'{repost_count} reposts deleted')
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

    print(f'{reply_count} replies deleted')
    time.sleep(2)

    brows.close()


if __name__ == '__main__':
    main()

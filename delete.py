#!/usr/bin/env python3
""" Delete the content out of your twitter account
"""

# Written with the aid of this tutorial and it's example code:
# https://www.geeksforgeeks.org/twitter-automation-using-selenium-python/

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
    firefox_options.add_argument('--height=2500')

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


def find_like_links(brows):
    like_links = []
    svgs = brows.find_elements("xpath", "//div[contains(@style, 'rgb(249, 24, 128)')]//*[name()='svg']")
    for svg in svgs:
        if "M20.884 13.19c-1.351 2.48-4.001 5.12-8.379" in svg.get_attribute('innerHTML'):
            like_links.append(svg)
    return like_links


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
        try:
            if "M3 12c0-1.1.9-2 2-2s2 .9 2 2-.9 2-2 2-2-.9-2-2zm9" in svg.get_attribute('innerHTML'):
                more_links.append(svg)
        except StaleElementReferenceException:
            # Tweets can contain SVGs and we might have removed those in passing. So skip any stale refs
            pass
    return more_links


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


def try_unlike(brows, actions, like_link) -> bool:
    try:
        firefox_scroll(brows, like_link)  # Firefox doesn't scroll on move_to_element() - work around with Javascript
    except StaleElementReferenceException:
        return False

    actions.move_to_element(like_link).click().perform()
    return True


def delete_all_the_twitter_things():
    global delete_count, reply_count, repost_count, like_count

    creds = get_credentials()
    brows = login(creds)
    actions = ActionChains(brows)

    # Load the profile and start deleting tweets

    url = f'https://twitter.com/{creds["username"]}'
    if brows.current_url != url:
        brows.get(url)
        time.sleep(2)

    print(url)

    while True:
        all_actions = delete_count + reply_count + repost_count
        if (all_actions > 0 and (all_actions % 100 == 0)):
            print("Reloading the page at 100 actions...")
            brows.get(url)
            time.sleep(2)
        elif (all_actions > 0 and (all_actions % 25 == 0)):
            print("Pausing...")
            time.sleep(1)

        # find green repost links, click on them to un-repost
        repost_links = find_repost_links(brows)

        if len(repost_links) > 0:
            didit = try_undo_repost(brows, actions, repost_links[0])

            if didit:
                repost_count += 1
                print("Deleted repost...")
                continue

        # Find the "..." SVG and click on it
        more_links = find_more_links(brows)

        if len(more_links) > 0:

            didit = try_to_delete(brows, actions, more_links[0])

            if didit:
                print("Deleted tweet...")
                delete_count += 1
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

        # find green repost links, click on them to un-repost
        repost_links = find_repost_links(brows)

        for link in repost_links:
            didit = try_undo_repost(brows, actions, link)

            if didit:
                print("Deleted repost...")
                reply_count += 1

        # main posts
        more_links = find_more_links(brows)

        for link in more_links:
            didit = try_to_delete(brows, actions, link)

            if didit:
                print("Deleted reply...")
                reply_count += 1

        if last_pass == reply_count:
            # We did a loop and had zero deletes
            break

    # Remove likes

    while True:
        brows.get(f'https://twitter.com/{creds["username"]}/likes')
        time.sleep(2)

        last_pass = like_count

        # find likes, click on them to unlike
        like_links = find_like_links(brows)

        for link in like_links:
            didit = try_unlike(brows, actions, link)

            if didit:
                print("Deleted like...")
                like_count += 1
                time.sleep(1)

        if last_pass == like_count:
            # We did a loop and had zero deletes
            break


    time.sleep(2)
    brows.close()


def main():
    global delete_count, reply_count, repost_count, like_count
    delete_count = 0
    reply_count = 0
    repost_count = 0
    like_count = 0

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
    print(f'{repost_count} reposts deleted')
    print(f'{reply_count} replies deleted')
    print(f'{like_count} likes deleted')


if __name__ == '__main__':
    main()

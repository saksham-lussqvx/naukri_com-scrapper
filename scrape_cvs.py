from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import os
import time
import datetime
import shutil
import multiprocessing

login_url = "https://hiring.naukri.com/hiring/job-listing"
# if not available then create a config file
if not os.path.exists("config.txt"):
    with open("config.txt", "w") as f:
        f.write("login_id=\npasswd=")
    input("Please enter your login id and password in config.txt file and then press enter to continue")
# read the config file
with open("config.txt", "r") as f:
    lines = f.readlines()
    login_id = lines[0].split("=")[-1].strip()
    passwd = lines[1].split("=")[-1].strip()

def login_if_needed(page, login_url, login_id, passwd):
    page.goto(login_url)
    time.sleep(3)
    try:
        page.click("id=loginRegTab", timeout=4000)
        time.sleep(3)
        # text = "Registered Email ID"
        page.type('input[name="username"]', login_id)
        # click on submit_button_1  rcom-btn-primary rcom-btn-regular
        page.type('input[name="password"]', passwd)
        time.sleep(2)
        #button class="submit_button_1  rcom-btn-primary rcom-btn-regular"
        page.click('button[type="submit"]')
    except Exception as e:
        print("Maybe already logged in")
    max_wait = 10
    while True:
        # get the current url
        url = page.url
        if url == login_url:
            break
        time.sleep(1)
        max_wait -= 1
        if max_wait == 0:
            break
def get_all_jobs(page):
    page.reload()
    time.sleep(4)
    # click on mjrFilterCheckbox
    page.click('span[class="mjrFilterCheckbox"]')
    time.sleep(1)
    # click on id=mjrSearchBtn
    page.click("id=mjrSearchBtn")
    time.sleep(3)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
    # get all class="mjrTupleTitle ellipsis"
    time.sleep(2)
    elements = page.query_selector_all('a[class="mjrTupleTitle ellipsis"]')
    links = []
    names = []
    for element in elements:
        links.append(element.get_attribute("href"))
        names.append(element.text_content())
    return links, names

def get_all_people(date_to_include, page, link):
    link = f"https://hiring.naukri.com{link}"
    while True:
        try:
            page.goto(link)
            # click class=label-count
            time.sleep(3)
            m = page.query_selector('div[class="badges-container"]')
            # under m get all divs and click on the first one 
            m.query_selector_all('div')[0].click()
            time.sleep(2)
            #span class="sel-text"
            page.click('span[class="sel-text"]')
            time.sleep(2)
            # find dropdown-options show-count-options
            e = page.query_selector('div[class="dropdown-options show-count-options"]')
            # find all li
            all_li = e.query_selector_all('li')
            # click the second one
            all_li[1].click()
            # scroll to the bottom of the page
            time.sleep(2)
            num = int(page.query_selector('span[class="page-value"]').text_content().split(" ")[-1])
            break
        except Exception as e:
            print(e)
            continue
    profiles = []
    dates = []
    while True:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        # now scroll back up slowly to the top
        time.sleep(1)
        for i in range(1, 30):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight/30*{})".format(i))
            time.sleep(0.4)
        time.sleep(2)
        all_people = page.query_selector_all('a[class="candidate-name"]')
        for person in all_people:
            profiles.append(person.get_attribute("href").split("?")[0])
        # get all class="flex-row flex-aic item"
        all_dates = page.query_selector_all('span[class="flex-row flex-aic item"]')
        for d in all_dates:
            d = d.text_content().split("Applied on: ")[-1].strip()
            d = datetime.datetime.strptime(d, "%d %b %y").strftime("%d-%m-%y")
            dates.append(d)
        num -= 1
        if num == 0:
            break
        page.click('i[class="oreFontIcons ore-arrow_down ico ico-expand next "]')
        time.sleep(2)
        # check if last date is less than date_to_include, if it is then break
        if len(date_to_include) != 0:
            if dates[-1] < date_to_include:
                break
    # remove all profiles that are not in date_to_include
    final_dates = []
    final_profiles = []
    for d, p in zip(dates, profiles):
        if d >= date_to_include:
            final_dates.append(d)
            final_profiles.append(p)
    return final_profiles

def download_cvs(profiles, name,b_name:int):
    new_session = get_session(f"{b_name}")
    login_if_needed(new_session, login_url, login_id, passwd)
    for link in profiles:
        with open("current_link.txt", "r") as f:
            if link in f.read():
                continue
        try:
            new_session.goto(link, timeout=5000)
            max_tries = 5
            to_refresh = 5
            while True: 
                time.sleep(1)
                # check if the download button is available
                if new_session.query_selector('i[class="oreFontIcons ore-download icon"]') == None:
                    to_refresh -= 1
                    if to_refresh == 0:
                        new_session.reload()
                        to_refresh = 5
                        max_tries -= 2
                    continue
                if max_tries <= 0:
                    break
                try:
                    with new_session.expect_download(timeout=5000) as download_info:
                        new_session.click('i[class="oreFontIcons ore-download icon"]')
                    download = download_info.value
                    download.save_as(f"{name}/{download.suggested_filename}")
                    with open("current_link.txt", "a") as f:
                        f.write(f"{link}\n")
                    break
                except:
                    max_tries -= 1
                    continue
        except:
            continue
    new_session.close()
    time.sleep(2)
    # delete the folder
    path = os.path.join(os.getcwd(), f"{b_name}")
    shutil.rmtree(f"{path}")

def get_session(name:str):
    # create a new Chrome session ans store it in a directory
    p = sync_playwright().start()
    path = os.path.join(os.getcwd(), name)

    browser = p.chromium.launch_persistent_context(path, headless=False,args=['--window-size=1920,1080'], viewport={"width": 1920, "height": 1080})
    page = browser.pages[0]
    stealth_sync(page)
    return page


def split_list(l, n):
    k, m = divmod(len(l), n)
    return (l[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))


if __name__ == "__main__":
    to_include = input("Enter date to include in format dd-mm-yy: ")
    try:
        path = os.path.join(os.getcwd(), "browser_main")
        shutil.rmtree(f"{path}")
    except:
        pass
    page = get_session("browser_main")
    login_if_needed(page, login_url, login_id, passwd)
    all_jobs, names = get_all_jobs(page)
    if os.path.exists("main_links.txt") == False:
        with open("main_links.txt", "w") as f:
            f.write("")
    for job, name in zip(all_jobs, names):
        if job in open("main_links.txt", "r").read():
            continue
        # create a folder of the job
        profiles = get_all_people(to_include, page, job)
        # save in a txt file 
        print(len(profiles))
        try:os.mkdir(name)
        except:pass
        # now split profiles into 4 parts, it can be odd or even so add all extra to the last one
        profiles = list(split_list(profiles, 4))
        if os.path.exists("current_link.txt") == False:
            with open("current_link.txt", "w") as f:
                f.write("")
        
        # now download all cvs
        threads = []
        for i in profiles:
            t = multiprocessing.Process(target=download_cvs, args=(i,name,profiles.index(i),))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        # now append the link to main_links.txt
        with open("main_links.txt", "a") as f:
            f.write(f"{job}\n")
    page.close()
    time.sleep(2)
    # delete the folder
    path = os.path.join(os.getcwd(), "browser_main")
    shutil.rmtree(f"{path}")
    os.remove("main_links.txt")
    print("All done")

from selenium import webdriver
from selenium.webdriver.common.by import By
import os
import time
import datetime
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


def login_if_needed(driver:webdriver.Chrome, login_url:str, login_id:str, passwd:str):
    driver.get(login_url)
    time.sleep(5)
    try:
        driver.find_element(By.ID, "loginRegTab").click()
        time.sleep(3)
        driver.find_element(By.CLASS_NAME, "username_input.__input").send_keys(login_id)
        
        driver.find_element(By.CLASS_NAME, "password_input.__input").send_keys(passwd)
        # click on submit_button_1  rcom-btn-primary rcom-btn-regular
        driver.find_element(By.CLASS_NAME, "rcom-btn-primary").click()
    except Exception as e:
        print("Maybe already logged in")
    time.sleep(4)


def get_session(download_dir="",headless=False):
    # create a new Chrome session ans store it in a directory
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    if headless:
        options.add_argument("--headless")
    # set error log to 3
    if len(download_dir) != 0:  
        path = os.getcwd()
        prefs = {"download.default_directory" : os.path.join(path, download_dir)}
        options.add_experimental_option("prefs",prefs)
    options.add_argument("--log-level=3")
    # remove automated control message
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver = webdriver.Chrome(options=options, executable_path="chromedriver.exe")
    return driver

def get_all_jobs(driver:webdriver.Chrome):
    driver.refresh()
    time.sleep(4)
    # click on mjrFilterCheckbox
    driver.find_element(By.CLASS_NAME, "mjrFilterCheckbox").click()
    time.sleep(1)
    # click on id=mjrSearchBtn
    driver.find_element(By.ID, "mjrSearchBtn").click()
    time.sleep(2)
    # get all class="mjrTupleTitle ellipsis"
    elements = driver.find_elements(By.CLASS_NAME, "mjrTupleTitle.ellipsis")
    links = []
    names = []
    for element in elements:
        links.append(element.get_attribute("href"))
        names.append(element.text)
    return links, names


def get_all_people(date_to_include:str, driver:webdriver.Chrome, link:str):
    driver.get(link)
    # click class=label-count
    time.sleep(3)
    m = driver.find_element(By.CLASS_NAME, "badges-container")
    # under m get all divs and click on the first one 
    m.find_elements(By.TAG_NAME, "div")[0].click()
    time.sleep(2)
    driver.find_element(By.CLASS_NAME, "oreFontIcons.ore-arrow_down.ico.ico-expand").click()
    time.sleep(2)
    # find dropdown-options show-count-options
    e = driver.find_element(By.CLASS_NAME, "dropdown-options.show-count-options")
    # find all li
    all_li = e.find_elements(By.TAG_NAME, "li")
    # click the second one
    all_li[1].click()
    # scroll to the bottom of the page
    time.sleep(2)
    num = int(driver.find_element(By.CLASS_NAME, "page-value").text.split(" ")[-1])
    profiles = []
    dates = []
    while True:
        if num == 0:
            break
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        # now scroll back up slowly to the top
        time.sleep(1)
        for i in range(1, 30):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/30*{})".format(i))
            time.sleep(0.2)
        time.sleep(2)
        all_people = driver.find_elements(By.CLASS_NAME, "candidate-name")
        for person in all_people:
            profiles.append(person.get_attribute("href"))
        # get all class="flex-row flex-aic item"
        all_dates = driver.find_elements(By.CLASS_NAME, "flex-row.flex-aic.item")
        for d in all_dates:
            d = d.text.split("Applied on: ")[-1]
            d = datetime.datetime.strptime(d, "%d %b %y").strftime("%d-%m-%y")
            dates.append(d)
        driver.find_element(By.CLASS_NAME, "oreFontIcons.ore-arrow_down.ico.ico-expand.next").click()
        time.sleep(2)
        num -= 1
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

def download_cvs(profiles:list, name:str):
    # do the login
    driver = get_session(download_dir=name)
    login_if_needed(driver, login_url, login_id, passwd)
    for link in profiles:
        driver.get(link)
        max_tries = 5
        while True:
            time.sleep(1)
            if max_tries == 0:
                break
            try:
                driver.find_elements(By.CLASS_NAME, "actionItems")[2].click()
                # wait till the download is complete
                time.sleep(3)
                break
            except:
                max_tries -= 1
                continue
    driver.quit()

if __name__ == '__main__':
    to_include = input("Enter date to include in format dd-mm-yy: ")
    session = get_session()
    login_if_needed(session, login_url, login_id, passwd)
    all_jobs,names = get_all_jobs(session)
    for job, name in zip(all_jobs, names):
        # create a folder of the job
        profiles = get_all_people(to_include, session, job)
        try:os.mkdir(name)
        except:pass
        # now split profiles into 4 parts, it can be odd or even so add all extra to the last one
        list_1, list_2, list_3, list_4 = [], [], [], []
        for i, profile in enumerate(profiles):
            if i % 4 == 0:
                list_1.append(profile)
            elif i % 4 == 1:
                list_2.append(profile)
            elif i % 4 == 2:
                list_3.append(profile)
            else:
                list_4.append(profile)
        profiles = [list_1, list_2, list_3, list_4]
        # now download all cvs
        threads = []
        for i in profiles:
            t = multiprocessing.Process(target=download_cvs, args=(i,name,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
    session.quit()
    print("All done")

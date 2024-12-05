import CAMS_Queries
from CommonFunctions import *
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime, timedelta
import sys
from selenium.common.exceptions import UnexpectedAlertPresentException
import numpy as np
import copy


# function for handling errors
def error_protocol(driver, action, exception=None, company_name=None, company_id=None):
    actions = {
        'search': "searching for company",
        'update': "updating company",
        'add': "adding company",
        'login': "logging in to ENS",
        'logout': "logging out",
        'driver': "initializing web driver",
        'cams': "getting CAMS data",
        'delete_contact': "deleting company",
        'delete_device': "deleting phone",
        'report': "getting report",
        "data": 'getting company data from ENS'
    }
    if action in ['cams', 'driver', 'report']:
        subject = "Automated ENS script error"
        sender_email = "bwimer@iso-ne.com"
        receiver_email = "opticalloutsupport@iso-ne.com"
        msg = f"An error occurred when {actions[action]}. Error: {exception}"
        send_email_html(msg, subject, sender_email, receiver_email, cc_email='')
        sys.exit(1)

    elif action == 'logout':
        try:
            # send username
            input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[1]/div/div[4]/input"], "test")
            # close driver
            driver.quit()
        except Exception as exception:
            msg = f"""Error occured when trying to logout. Did not succeed in logging out of ENS, but the script finished 
            successfully. Someone must MANUALLY logout of ENS to avoid login build up. Error: {exception}"""
            subject = "Automated ENS script error"
            sender_email = "bwimer@iso-ne.com"
            receiver_email = "opticalloutsupport@iso-ne.com"
            send_email_html(msg, subject, sender_email, receiver_email, cc_email='')
            sys.exit(1)

    elif action == 'login':
        try:
            click_button(driver, ["/html/body/form/table/tbody/tr[1]/td/div[1]/div/div[1]/a"])
        except UnexpectedAlertPresentException as e:
            msg = f"An error occured when trying to login to ens. Error: {e}"
            subject= "Automated ENS script error"
            sender_email = "bwimer@iso-ne.com"
            receiver_email = "opticalloutsupport@iso-ne.com"
            send_email_html(msg, subject, sender_email, receiver_email, cc_email='')
            sys.exit(1)

    else:
        msg_success = f"""An error occurred when {actions[action]}: {company_name if company_name else ""} with id: {company_id if company_id else ""} in ENS.
        Successfully logged out of ENS, but did not complete task. Error: {exception}"""

        msg_fail = f"""An error occurred when {actions[action]}: {company_name if company_name else ""} with id: {company_id if company_id else ""} in ENS.
        Did not successfully logout of ENS, someone must MANUALLY logout of ENS to avoid login build up. Error: {exception if exception else ""}"""

        try:
            logout_ens(driver)
            # send username
            input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[1]/div/div[4]/input"], "test")
            subject = "Automated ENS script error"
            sender_email = "bwimer@iso-ne.com"
            receiver_email = "opticalloutsupport@iso-ne.com"
            send_email_html(msg_success, subject, sender_email, receiver_email, cc_email='')
        except Exception as e:
            subject = "Automated ENS script error"
            sender_email = "bwimer@iso-ne.com"
            receiver_email = "opticalloutsupport@iso-ne.com"
            send_email_html(msg_fail, subject, sender_email, receiver_email, cc_email='')
        sys.exit(1)

# Function for initializing web driver
def get_driver(url, dir):
    # Set up Chrome options to specify the download directory for ENS report
    download_dir = dir
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--profile-directory=Default")
    # chrome_options.add_argument("--user-data-dir=/tmp/chrome_user_data")
    # set Chrome preferences
    chrome_prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True,
        "profile.default_content_settings.popups": 0,
        "profile.content_settings.exceptions.automatic_downloads": 1
    }
    chrome_options.add_experimental_option("prefs", chrome_prefs)
    # Navigate driver to url
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    return driver


# Function to input info
def input_info(driver, ids, info):
    for id in ids:
        try:
            element = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable((By.XPATH, id))
            )

            element.click()

            element.send_keys(str(info))

        except TimeoutException:
            print(f"Timeout while trying to interact with element {id}")


# Function to change info where it already exists
def change_info(driver, ids, info):
    action = ActionChains(driver)
    for id in ids:
        try:
            element = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable((By.XPATH, id))
            )

            element.click()
            # select all
            action.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
            element.send_keys(str(info))

        except TimeoutException:
            print(f"Timeout while trying to interact with element {id}")


# Function to handle button clicks
def click_button(driver, ids):
    for id in ids:
        try:
            element = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable((By.XPATH, id))
            )

            element.click()

        except TimeoutException:
            raise TimeoutException()

# Function for formatting phone number in CAMS format to match ENS formatting
def format_phone_ens(phone):
    if phone != None:
        phone = str(phone)
        split_phone = phone.split('-')
        if len(split_phone) == 3:
            formatted_phone = "+1 (" + split_phone[0] + ") " + split_phone[1] + "-" + split_phone[2]
            return formatted_phone.replace('ext ', 'x')
        else:
            return phone
    else:
        return phone


# Function for formatting phone number in ENS format to match CAMS formatting
def format_phone_cams(phone):
    if (phone != None) and (phone != 0):
        phone = str(phone)
        split_phone = phone.split('(')
        if len(split_phone) == 2:
            formatted_phone = split_phone[1].replace(") ", "-")
            # format for extension possibility as well
            formatted_phone = formatted_phone.replace(' x', ' ext ')
            return formatted_phone
        else:
            return phone
    else:
        return None

# Function for formatting phone numbers in ENS format to match CAMS formatting
def format_phones_cams(phones):
    formatted_phones = []

    for phone in phones:
        formatted_phones.append(format_phone_cams(phone))

    return formatted_phones


# function for sending an email
def send_csvs_as_html(csv_files, explanations, subject, sender_email, receiver_email, cc_email='', attachments=[]):
    # Start HTML content
    html_content = ""
    # Check if there are any CSV files to send
    if not csv_files:
        # If no CSV files, set a default message
        html_content = "<p>All data is up to date. No CSV files to send.</p>"
    else:
        # Loop through each file and its corresponding explanation
        for csv_path, explanation in zip(csv_files, explanations):
            formatted_explanation = explanation.replace("\r", "<br>")
            # Read the CSV file into a DataFrame
            df = pd.read_csv(csv_path)

            # Add a header and convert DataFrame to HTML
            html_content += f"<h3>{formatted_explanation}</h3>"
            html_content += df.to_html(index=False) + "<br><hr>"

    # Construct and send the email
    send_email_html(html_content, subject, sender_email, receiver_email, cc_email, attachments)


# Function to perform login
def login_ens(driver, username, password, company_name):
    # send username
    input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[1]/div/div[4]/input"], username)
    # send password
    input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[1]/div/div[5]/input"], password)
    # send company name
    input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[1]/div/div[6]/input"], company_name)
    # click login button to login
    click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[1]/div/div[8]/input"])
    # sleep to wait for popup
    time.sleep(3)


# function to perform logout
def logout_ens(driver):
    click_button(driver, ["/html/body/form/table/tbody/tr[2]/td[1]/table/tbody/tr/td[2]/a"])

# Function for getting and saving all the current data in ENS
def get_report(driver, dir):
    # set download directory for the report to be saved in
    download_dir = dir
    # set report file pattern to find the report
    file_pattern = re.compile(r"All_Contacts_all_info.*\.csv")
    # web page interactions
    try:
        # click on "reports" tab
        click_button(driver, ["/html/body/form/table/tbody/tr[1]/td/div[1]/div/div[6]/a"])
        # click on "run reports" tab
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[3]/table/tbody/tr[1]/td[8]/a"])
        # select "contacts" from "report category" dropdown
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[2]/div/select[1]/option[2]"])
        # select "all_contacts_all_info" from "report name" dropdown
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[2]/div/select[2]/option[2]"])
        # click on run report button
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[2]/div/input"])
    except Exception as e:
        error_protocol(driver, exception=e, action='report')
    else:
        # Wait for the file to be downloaded
        time.sleep(10)
        # Timeout after 60 seconds
        timeout = 60
        start_time = time.time()
        newest_file_path = ""
        while time.time() - start_time < timeout:
            matching_files = [os.path.join(download_dir, filename) for filename in os.listdir(download_dir) if
                              file_pattern.match(filename)]
            if matching_files:
                newest_file_path = max(matching_files, key=os.path.getctime)
                break
        if not newest_file_path:
            error_protocol(driver, exception="could not find report file", action='report')
        # Read and return the CSV file
        df = pd.read_csv(newest_file_path)
        return df

# Function for getting changed CAMS data over a specified time duration
def get_changed_cams_timerange(start_date, end_date):
    q = CAMS_Queries.CAMSchanges
    q_formatted = q.format(start_date, end_date)
    df, e = getQueryData("entdbp", q_formatted)
    return df, e

# Function for getting most up-to-date data from CAMS for all companies
def get_cams_today():
    q = CAMS_Queries.curCAMS
    current_date = datetime.now()
    formatted_date = current_date.strftime('%m/%d/%Y')
    q1 = q.format(formatted_date)
    df, error = getQueryData("entdbp", q1)
    return df, error

# Function for searching for a contact in ENS
def search_in_ens(driver, search_by, search_criteria):
    # searching by phone number
    if search_by == "phone":
        # click on contacts
        click_button(driver, ["/html/body/form/table/tbody/tr[1]/td/div[1]/div/div[1]/a"])
        # Click on By Device Tab to search by device
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[2]/table/tbody/tr[1]/td[6]/a"])
        # click on search bar
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[1]/input[1]"])
        # input phone into search bar
        input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[1]/input[1]"], search_criteria)
        # click on phone in Search By dropdown
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[1]/select/option[5]"])
        # click on find button to search for company name
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[1]/input[2]"])
        # try to get company name
        try:
            # click on phone to go into new page that contains phone number
            click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/table/tbody/tr[2]/td[6]/a"])
        except TimeoutException:
            print(f"Failed to find contact with {search_criteria}")
            raise TimeoutException
    # searching by name or id
    else:
        # click on contacts
        click_button(driver, ["/html/body/form/table/tbody/tr[1]/td/div[1]/div/div[1]/a"])
        # click on By Name Tab to search by device
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[2]/table/tbody/tr[1]/td[2]/a"])
        # click on search bar
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[2]/table/tbody/tr[1]/td[2]/a"])
        # input id into search bar
        input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[1]/input[1]"], search_criteria)
        # if searching by id click on id in Search By dropdown
        if search_by == "company id":
            click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[1]/select/option[4]"])
        # if searching by company name, click on first name in Search By dropdown
        elif search_by == "company name":
            click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[1]/select/option[2]"])
        # click on find button to search for company
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[1]/input[2]"])
        try:
            # click on id to go into new page that contains phone number
            click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/table/tbody/tr[2]/td[5]/a"])
        except TimeoutException:
            print(f"Failed to find contact with {search_criteria}")
            raise TimeoutException

# Function for getting all contact details in ENS contact page
def get_ens_data(driver, ens_dic):
    # declare phone number variables
    phone_numbers = [None] * 4

    # Extracting phone numbers
    for i in range(1, 5):
        try:
            phone_numbers[i - 1] = WebDriverWait(driver, 1).until(
                EC.visibility_of_element_located(
                    (By.XPATH,
                     f"/html/body/form/table/tbody/tr[3]/td[2]/table[1]/tbody/tr[{i + 1}]/td[4]/span[1]"))
            ).text

        except TimeoutException:
            break

    # add phone numbers to the dictionary
    ens_dic["Primary Phone"].append(phone_numbers[0])
    ens_dic["Alt Phone 1"].append(phone_numbers[1])
    ens_dic["Alt Phone 2"].append(phone_numbers[2])
    ens_dic["Alt Phone 3"].append(phone_numbers[3])

    # get company name
    try:
        company_name_field = WebDriverWait(driver, 1).until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "/html/body/form/table/tbody/tr[3]/td[2]/div[1]/div[1]/table[1]/tbody/tr[2]/td[2]/input"))
        )
        company_name = company_name_field.get_attribute('value')
        ens_dic["Company Name"].append(company_name)
    except TimeoutException:
        print("failed to get company name")

    # get company id
    try:
        company_id_field = WebDriverWait(driver, 1).until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "/html/body/form/table/tbody/tr[3]/td[2]/div[1]/div[1]/table[1]/tbody/tr[6]/td[2]/input"))
        )
        company_id = company_id_field.get_attribute('value')
        ens_dic["Company ID"].append(company_id)
    except TimeoutException:
        print("failed to get company id")

    # get company last name
    try:
        company_last_name_field = WebDriverWait(driver, 1).until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "/html/body/form/table/tbody/tr[3]/td[2]/div[1]/div[1]/table[1]/tbody/tr[4]/td[2]/input"))
        )
        company_last_name = company_last_name_field.get_attribute('value')
        ens_dic["Last Name"].append(company_last_name)
    except TimeoutException:
        print("failed to get company last name")

    return ens_dic

# Function for updating all contact details in ENS contact page
def make_general_ens_update(driver, company_name, company_id, last_name, new_numbers, auto_delete):
    # input first name
    change_info(driver,
                ["/html/body/form/table/tbody/tr[3]/td[2]/div/div[1]/table[1]/tbody/tr[2]/td[2]/input"],
                company_name)
    # input user id
    change_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div/div[1]/table[1]/tbody/tr[6]/td[2]/input"],
                company_id)
    # input last name
    change_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[1]/div[1]/table[1]/tbody/tr[4]/td[2]/input"],
                last_name)
    # click on save
    click_button(driver,
                 ["/html/body/form/table/tbody/tr[3]/td[2]/div[1]/div[2]/input[1]"])
    # update phone numbers
    update_ens_phones(driver, new_numbers, auto_delete)

# Function for updating ENS phone numbers in ENS contact page
def update_ens_phones(driver, new_numbers, auto_delete):
    y = 0
    # loop through new numbers
    for i in range(1, 5):
        new_number = new_numbers[i - 1]
        # Check if phone number i exists in CAMS
        if (type(new_number) == str):
            # try and edit number i in ENS
            try:
                # click on change button for phone i
                click_button(driver, [f"/html/body/form/table/tbody/tr[3]/td[2]/table[1]/tbody/tr[{i + 1}]/td[7]/a"])
                # input new phone number for phone i
                change_info(driver, [f"/html/body/form/table/tbody/tr[3]/td[2]/table[1]/tbody/tr[{i + 1}]/td[4]/input"],
                            new_number)
                # save new number
                click_button(driver, [f"/html/body/form/table/tbody/tr[3]/td[2]/table[1]/tbody/tr[{i + 1}]/td[7]/a[1]"])
            # if phone i doesn't exist in ENS, need to add it
            except:
                # click on phone tab
                click_button(driver,
                             ["/html/body/form/table/tbody/tr[3]/td[2]/div[3]/table/tbody/tr[1]/td[4]/a"])
                # select phone type (work)
                click_button(driver,
                             ["/html/body/form/table/tbody/tr[3]/td[2]/div[4]/div[1]/select/option[2]"])
                # split to get extension if it exists
                split_num = new_number.split("ext")
                # if extension does exist, add phone with extension number
                if len(split_num) == 2:
                    # input phone number into text field
                    input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[4]/div[1]/input[1]"],
                               split_num[0])
                    # input extension number into text field
                    input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[4]/div[1]/input[2]"],
                               split_num[1])
                # if extension does not exist, just add phone number
                else:
                    # input phone number into text field
                    input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[4]/div[1]/input[1]"],
                               new_number)
                # click on add button to add phone number
                click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[4]/div[2]/input"])
        # if no more phone numbers, break out of loop
        else:
            y = i
            break
    if y == 0:
        y = 5
    # if auto_delete is true, then delete additional contacts if they exist
    if auto_delete:
        # check and see if phone number i exists, if so delete it
        # click on phone tab
        click_button(driver,
                     ["/html/body/form/table/tbody/tr[3]/td[2]/div[3]/table/tbody/tr[1]/td[4]/a"])
        while True:
            # try to click on change button for phone y
            try:
                click_button(driver, [f"/html/body/form/table/tbody/tr[3]/td[2]/table[1]/tbody/tr[{y + 1}]/td[5]/a"])
            # if it doesn't exist, break the loop
            except TimeoutException:
                break
            # if it does exist, delete it
            else:
                # click on cancel
                click_button(driver, [f"/html/body/form/table/tbody/tr[3]/td[2]/table[1]/tbody/tr[{y + 1}]/td[5]/a[2]"])
                # select phone number for deletion
                click_button(driver,
                             [f"/html/body/form/table/tbody/tr[3]/td[2]/table[1]/tbody/tr[{y + 1}]/td[1]/span/input"])
                # click on "remove device" to delete phone number
                click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[1]/div[1]/div[13]/span/a"])
                # wait for alert
                driver.implicitly_wait(5)
                try:
                    # try to switch to alert and accept it
                    alert = driver.switch_to.alert
                    # try to accept alert
                    alert.accept()
                except Exception as e:
                    company_name_field = WebDriverWait(driver, 1).until(
                        EC.visibility_of_element_located(
                            (By.XPATH,
                             "/html/body/form/table/tbody/tr[3]/td[2]/div[1]/div[1]/table[1]/tbody/tr[2]/td[2]/input"))
                    )
                    company_name = company_name_field.get_attribute('value')
                    company_id_field = WebDriverWait(driver, 1).until(
                        EC.visibility_of_element_located(
                            (By.XPATH,
                             "/html/body/form/table/tbody/tr[3]/td[2]/div[1]/div[1]/table[1]/tbody/tr[6]/td[2]/input"))
                    )
                    company_id = company_id_field.get_attribute('value')

                    error_protocol(driver, exception=e, action="delete_device", company_id=company_id,
                                   company_name=company_name)

# Function for deleting contact in ENS
def delete_contact_ens(driver, company_id):
    try:
        # find company
        search_in_ens(driver, "company id", company_id)

    except TimeoutException:
        print(f"company with id # {company_id} could not be found to be deleted")
    else:
        # click on contacts to return to wider view
        click_button(driver, ["/html/body/form/table/tbody/tr[1]/td/div[1]/div/div[1]/a"])
        # select company to be deleted, we assume it is top company at the search
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/table/tbody/tr[2]/td[1]/input"])
        # click on "remove contact(s)"
        click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[1]/div[1]/div[5]/span/a"])
        # try to bypass popup
        try:
            # try to switch to alert
            alert = driver.switch_to.alert
            # try to accept alert
            alert.accept()
        except Exception as e:
            error_protocol(driver, action="delete_contact", exception=e, company_id=company_id)

# Function for adding contact in ENS
def add_new_contact_ens(driver, firstName, userID, loginName, phoneNumbers, lastName):
    # click on contacts
    click_button(driver, ["/html/body/form/table/tbody/tr[1]/td/div[1]/div/div[1]/a"])
    # click on add contact
    click_button(driver, ["/html/body/form/table/tbody/tr[3]/td[1]/div[1]/div[3]/span/a"])
    # input first name
    input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div/div[1]/table[1]/tbody/tr[2]/td[2]/input"],
               firstName)
    # input last name
    input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div/div[1]/table[1]/tbody/tr[4]/td[2]/input"],
               lastName)
    # input user id
    input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div/div[1]/table[1]/tbody/tr[6]/td[2]/input"],
               userID)
    # input login name
    input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div/div[1]/table[1]/tbody/tr[8]/td[2]/input"],
               loginName)

    # click on save
    click_button(driver,
                 ["/html/body/form/table/tbody/tr[3]/td[2]/div[1]/div[2]/input[1]"])

    # click on phone tab
    click_button(driver,
                 ["/html/body/form/table/tbody/tr[3]/td[2]/div[3]/table/tbody/tr[1]/td[4]/a"])

    # add phone numbers
    for phone in phoneNumbers:
        if phone != None:
            # split if it has an extension
            split_num = phone.split("ext")
            if len(split_num) == 2:
                # input phone number into text field
                input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[4]/div[1]/input[1]"],
                           split_num[0])
                # input extension number into text field
                input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[4]/div[1]/input[2]"],
                           split_num[1])
                # select phone type (work)
                click_button(driver,
                             ["/html/body/form/table/tbody/tr[3]/td[2]/div[4]/div[1]/select/option[2]"])

                # click on add button to add phone number
                click_button(driver,
                             ["/html/body/form/table/tbody/tr[3]/td[2]/div[4]/div[2]/input"])
            else:
                # input phone number into text field
                input_info(driver, ["/html/body/form/table/tbody/tr[3]/td[2]/div[4]/div[1]/input[1]"],
                           phone)
                # select phone type (work)
                click_button(driver,
                             ["/html/body/form/table/tbody/tr[3]/td[2]/div[4]/div[1]/select/option[2]"])
                # click on add button to add phone number
                click_button(driver,
                             ["/html/body/form/table/tbody/tr[3]/td[2]/div[4]/div[2]/input"])

from Shared_Functions import *


# Function for getting CAMS data that changed from yesterday to today
def get_changed_cams_yesterday_today():
    q = CAMS_Queries.CAMSchanges
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    formatted_end_date = today.strftime('%m/%d/%Y')
    formatted_start_date = yesterday.strftime('%m/%d/%Y')
    q_formatted = q.format(formatted_start_date, formatted_end_date)
    df, e = getQueryData("entdbp", q_formatted)
    return df, e

# Function for updating ENS to match daily CAMS updates
def update_ens_with_changed_data(url, delete_devices, delete_contacts, dir, start=None, end=None):
    ####### collecting CAMS data ########
    if start == None:
        # get changed cams data
        changed_df, error = get_changed_cams_yesterday_today()
    else:
        changed_df, error = get_changed_cams_timerange(start, end)
    # make sure no error
    if error != "":
        error_protocol(driver='', action='cams')
    # get cams data for today
    today_df, error = get_cams_today()
    # make sure no error
    if error != "":
        error_protocol(driver='', action='cams')

    ############ Initialize driver and login #############
    # initialize driver
    try:
        driver = get_driver(url, dir=dir)
    except Exception as e:
        # if it did not work, call error protocol and exit program
        error_protocol(driver='', action='driver', exception=e)
        # this has no effect just silences the warnings that the driver might not be initialized
        driver = False
    else:
        # login
        login_ens(driver, "bwimer", "Kenel-lax22", "isone")
        # check if login was successful
        error_protocol(driver=driver, action='login')

    # get report
    get_report(driver, dir=dir)


    ############# create data objects for collecting ENS data ############
    # initialize data object for deleted contacts
    deleted_dic = {"Primary Phone": [], "Company Name": [], "Last Name": [], "Company ID": [], "Alt Phone 1": [],
                   "Alt Phone 2": [], "Alt Phone 3": []}
    # initialize dic for changed data in ENS
    changed_data_ens = {"Primary Phone": [], "Company Name": [], "Last Name": [], "Company ID": [], "Alt Phone 1": [],
               "Alt Phone 2": [], "Alt Phone 3": []}
    # initialize dic for added data in ENS
    added_data_ens = {"Primary Phone": [], "Company Name": [], "Last Name": [], "Company ID": [], "Alt Phone 1": [],
                        "Alt Phone 2": [], "Alt Phone 3": []}


    ######### collect and update ENS data, main logic of function ##########
    # loop through changes and update ENS
    for index in range(len(changed_df)):
        diff_type = changed_df.loc[index, 'DIFF_TYPE']
        # if update to company data
        if (diff_type == "EDITED - New data"):
            # search for company in ENS
            try:
                search_in_ens(driver, search_by="company id", search_criteria=changed_df.loc[index, 'DE_ID'])
            except Exception as e:
                error_protocol(driver=driver, action='search', exception=e, company_id=changed_df.loc[index, 'DE_ID'],
                               company_name=changed_df.loc[index, 'DE_OPERATOR_ALIAS_NAME'])
            # update company contact info
            try:
                # get DE name from other CAMS query
                company_row = today_df[today_df['DE_ID'] == changed_df.loc[index, 'DE_ID']]
                company_last_name = company_row['DISPATCH_LOCATION_TYPE'].iloc[0]
                make_general_ens_update(driver, changed_df.loc[index, 'DE_OPERATOR_ALIAS_NAME'],
                                        changed_df.loc[index, 'DE_ID'], company_last_name,
                                        changed_df.loc[
                                            index, ['PRIMARY_DBL', 'ALTERNATIVE_PHONE_1', 'ALTERNATIVE_PHONE_2',
                                                    'ALTERNATIVE_PHONE_3']].to_list(), delete_devices)
            except Exception as e:
                error_protocol(driver=driver, action='update', company_id=changed_df.loc[index, 'DE_ID'],
                               company_name=changed_df.loc[index, 'DE_OPERATOR_ALIAS_NAME'], exception=e)
            # record updates made to ens
            changed_data_ens = get_ens_data(driver, changed_data_ens)

        # if new contact needs to be added, try to search for it. if it exists update phones, if not, add it.
        elif (diff_type == "ADDED"):
            try:
                search_in_ens(driver, search_by="company id", search_criteria=changed_df.loc[index, 'DE_ID'])
            except TimeoutException:
                # try to add company
                try:
                    # get DE name from other CAMS query
                    company_row = today_df[today_df['DE_ID'] == changed_df.loc[index, 'DE_ID']]
                    company_last_name = company_row['DISPATCH_LOCATION_TYPE'].iloc[0]
                    add_new_contact_ens(driver, changed_df.loc[index, 'DE_OPERATOR_ALIAS_NAME'],
                                        changed_df.loc[index, 'DE_ID'],
                                        changed_df.loc[index, 'DE_NAME'],
                                        changed_df.loc[
                                            index, ['PRIMARY_DBL', 'ALTERNATIVE_PHONE_1', 'ALTERNATIVE_PHONE_2',
                                                    'ALTERNATIVE_PHONE_3']].to_list(),
                                        company_last_name)
                except Exception as e:
                    error_protocol(driver, action='add', exception=e, company_name=changed_df.loc[index, 'DE_OPERATOR_ALIAS_NAME'],
                                           company_id=changed_df.loc[index, 'DE_ID'])
            else:
                try:
                    update_ens_phones(driver, changed_df.loc[index, ['PRIMARY_DBL', 'ALTERNATIVE_PHONE_1',
                                                                     'ALTERNATIVE_PHONE_2',
                                                                     'ALTERNATIVE_PHONE_3']].to_list(), delete_devices)
                except Exception as e:
                    error_protocol(driver=driver, action='update', company_id=changed_df.loc[index, 'DE_ID'],
                                   company_name=changed_df.loc[index, 'DE_OPERATOR_ALIAS_NAME'], exception=e)
            # record updates made to ens
            added_data_ens = get_ens_data(driver, added_data_ens)

        # if contact needs to be deleted
        elif (diff_type == "DELETED"):
            deleted_dic["Primary Phone"].append(changed_df.loc[index, 'PRIMARY_DBL'])
            deleted_dic["Company Name"].append(changed_df.loc[index, 'DE_OPERATOR_ALIAS_NAME'])
            company_row = today_df[today_df['DE_ID'] == changed_df.loc[index, 'DE_ID']]
            company_last_name = company_row['DISPATCH_LOCATION_TYPE'].iloc[0]
            deleted_dic["Last Name"].append(company_last_name)
            deleted_dic["Company ID"].append(changed_df.loc[index, 'DE_ID'])
            deleted_dic["Alt Phone 1"].append(changed_df.loc[index, 'ALTERNATIVE_PHONE_1'])
            deleted_dic["Alt Phone 2"].append(changed_df.loc[index, 'ALTERNATIVE_PHONE_2'])
            deleted_dic["Alt Phone 3"].append(changed_df.loc[index, 'ALTERNATIVE_PHONE_3'])
            ########### uncomment if you want to automatically delete companies #########
            if delete_contacts:
                try:
                    delete_contact_ens(driver, changed_df.loc[index, 'DE_ID'])
                except Exception as e:
                    error_protocol(driver=driver, action='delete_contact', company_id=changed_df.loc[index, 'DE_ID'],
                                   company_name=changed_df.loc[index, 'DE_OPERATOR_ALIAS_NAME'], exception=e)

    ############ logout and close driver #########
    # logout
    logout_ens(driver)
    # test to see if logout successful, if successful, close driver
    error_protocol(driver, 'logout')

    ########## format data and send email #############
    ####### getting CAMS data for reference in email ########
    # isolate added data for comparison
    added_data_cams = changed_df[changed_df["DIFF_TYPE"] == "ADDED"]
    # isolate new data for comparison
    new_data_cams = changed_df[changed_df["DIFF_TYPE"] == "EDITED - New data"]
    # isolate old data for comparison
    old_data_cams = changed_df[changed_df["DIFF_TYPE"] == "EDITED - Old data"]



    ########## sending email #########
    # format csv files in email
    if ((len(deleted_dic['Primary Phone']) == 0) and (len(changed_data_ens['Primary Phone']) == 0) and
            (len(added_data_ens['Primary Phone']) == 0)):
        send_csvs_as_html([], [], f'ENS update with data from yesterday to today',
                          'bwimer@iso-ne.com',
                          'opticalloutsupport@iso-ne.com')
    else:
        ######## making csv files for collected and changed data ###########
        # get time to make unique csv file name
        num = datetime.now().strftime("%Y-%m-%d_%H-%M")
        # convert dictionaries to dataframes for saving
        deleted_df = pd.DataFrame.from_dict(deleted_dic)
        changed_df_ens = pd.DataFrame.from_dict(changed_data_ens)
        added_df_ens = pd.DataFrame.from_dict(added_data_ens)
        # save df's as csv's
        new_data_cams.to_csv(rf"csv_reports\new_data_cams_{num}.csv", index=False)
        old_data_cams.to_csv(rf"csv_reports\old_data_cams_{num}.csv", index=False)
        changed_df_ens.to_csv(rf"csv_reports\changed_df_ens_{num}.csv", index=False)
        added_data_cams.to_csv(rf"csv_reports\added_data_cams_{num}.csv", index=False)
        added_df_ens.to_csv(rf"csv_reports\added_df_ens_{num}.csv", index=False)
        deleted_df.to_csv(rf"csv_reports\deleted_df_{num}.csv", index=False)
        # save them in a list for the email
        email_csvs = [rf"{dir}\deleted_df_{num}.csv",
                      rf"{dir}\added_df_ens_{num}.csv",
                      rf"{dir}\changed_df_ens_{num}.csv",
                      rf"{dir}\added_data_cams_{num}.csv",
                      rf"{dir}\old_data_cams_{num}.csv",
                      rf"{dir}\new_data_cams_{num}.csv"
                      ]
        # text explaining csv's in email
        explanations = ["""Here is the report for the daily automated ENS update. If anything seems incorrect and changes need to be restored,
                               the attached csv contains all the ENS data before updates were made. Please review the items below. \r \r \r
                               ACTION ITEM:
                               Companies that should be MANUALLY deleted according to CAMS""",
                        """AUTOMATED ENS UPDATES (please review):
                        Companies that have been added to ENS""",
                        "AUTOMATED ENS UPDATES (please review): ENS companies after updates have been made",
                        """REFERENCE MATERIAL:
                        Companies that should be added according to CAMS""",
                        "REFERENCE MATERIAL: Companies that should be updated according to CAMS (old data)",
                        "REFERENCE MATERIAL: Companies that should be updated according to CAMS (new data)"
                    ]
        if delete_contacts:
            explanations[0] = "Companies that have been automatically deleted in ENS"

        # get report csv to send in email in case of error
        # Wait for the file to be downloaded
        file_pattern = re.compile(r"All_Contacts_all_info.*\.csv")
        download_dir = fr"{dir}"
        timeout = 5  # Timeout after 60 seconds
        start_time = time.time()
        newest_file_path = ""
        while time.time() - start_time < timeout:
            matching_files = [os.path.join(download_dir, filename) for filename in os.listdir(download_dir) if
                              file_pattern.match(filename)]
            if matching_files:
                newest_file_path = max(matching_files, key=os.path.getctime)
                break

        if not newest_file_path:
            print("file path not found")
        # send email
        send_csvs_as_html(email_csvs, explanations, f'ENS update with data from yesterday to today', 'bwimer@iso-ne.com',
                          'opticalloutsupport@iso-ne.com', attachments=[newest_file_path])
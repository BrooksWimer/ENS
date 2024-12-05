from Shared_Functions import *




def full_clean(url, delete_devices, delete_contacts, dir):
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


    ######## collecting ENS data ########
    report_df = get_report(driver, dir=dir)


    ####### collecting CAMS data ########
    cams_df_full, error = get_cams_today()
    # check if query was successful
    if error != "":
        error_protocol(driver='', action='cams')
    # isolate the columns we care about
    cams_df = cams_df_full.loc[:,
              ['DE_OPERATOR_ALIAS_NAME', 'DISPATCH_LOCATION_TYPE', 'DE_ID', 'PRIMARY_DBL', 'ALTERNATIVE_PHONE_1', 'ALTERNATIVE_PHONE_2',
               'ALTERNATIVE_PHONE_3']]
    # get unique data based on primary phone numbers
    unique_primary = cams_df.drop_duplicates(subset=['PRIMARY_DBL'], ignore_index=True)




    ########### main logic of the function ############
    ens_dictionary_template = {"Primary Phone": [], "Company Name": [], "Last Name": [], "Company ID": [],
                       "Alt Phone 1": [],
                       "Alt Phone 2": [], "Alt Phone 3": []}
    # create dictionary, for inspecting ens data after changes have been made
    updated_ens_dic = copy.deepcopy(ens_dictionary_template)
    # create dictionary, for inspecting ens data after changes have been made
    up_to_date_dic = copy.deepcopy(ens_dictionary_template)
    # create dictionary for companies not in cams
    ens_companies_not_in_cams_dic = copy.deepcopy(ens_dictionary_template)
    # create dictionary to capture contacts that are not in CAMS and not a DE or DDE
    ens_contacts_not_in_cams_dic = copy.deepcopy(ens_dictionary_template)
    # loop through contacts
    for index in range(len(report_df)):
        print(f"we are at row {index} in report df loop")
        # set values
        user_id = report_df.loc[index, 'UserID']
        ens_company_name = report_df.loc[index, 'First Name']
        ens_last_name = report_df.loc[index, 'Last Name']

        # click on "contacts" tab
        click_button(driver, ["/html/body/form/table/tbody/tr[1]/td/div[1]/div/div[1]/a"])
        # search for company in ENS
        try:
            search_in_ens(driver, search_by='company id', search_criteria=user_id)
        except Exception as e:
            error_protocol(driver=driver, action='search', exception=e, company_id=user_id,
                                      company_name=ens_company_name)
        else:
            # get ENS data from ENS page
            try:
                # initialize data object to hold ENS information for the current company
                company_dict = copy.deepcopy(ens_dictionary_template)
                # collect the data from the ENS page
                company_dict = get_ens_data(driver, company_dict)
            except Exception as e:
                error_protocol(driver=driver, action='data', company_id=user_id, company_name=ens_company_name, exception=e)
            else:
                formatted_phones_from_page = format_phones_cams(
                    [company_dict["Primary Phone"][0], company_dict['Alt Phone 1'][0],
                     company_dict['Alt Phone 2'][0], company_dict['Alt Phone 3'][0]])

                # set boolean flag to see if contact match was found
                match_found = False
                #make this class for breaking out of double loop
                class ExitLoop(Exception):
                    pass
                # compare all CAMS phone cols to all ENS phone cols
                try:
                    for cams_column in ['PRIMARY_DBL', 'ALTERNATIVE_PHONE_1', 'ALTERNATIVE_PHONE_2','ALTERNATIVE_PHONE_3']:
                        for phone in formatted_phones_from_page:
                            for i in range(2):
                                if (i == 1) and (phone != None):
                                    phone = phone.split(' ext')[0]
                                # if contact is in CAMS, update ens and save updated ens
                                if (phone != None) and (phone in unique_primary[cams_column].tolist()):
                                    # locate company row in cams df
                                    company_row = unique_primary[unique_primary[cams_column] == phone]
                                    # get cams data from data frame
                                    company_name = company_row['DE_OPERATOR_ALIAS_NAME'].iloc[0]
                                    last_name = company_row['DISPATCH_LOCATION_TYPE'].iloc[0]
                                    company_id = company_row["DE_ID"].iloc[0]
                                    new_numbers = company_row[['PRIMARY_DBL', 'ALTERNATIVE_PHONE_1',
                                                               'ALTERNATIVE_PHONE_2', 'ALTERNATIVE_PHONE_3']].iloc[0,:].tolist()

                                    # make sure this company ID has not already been used
                                    if index > 0 and ((str(company_id) in updated_ens_dic['Company ID']) or
                                                      (str(company_id) in report_df.loc[:index-1,'UserID'].tolist())):
                                        print(f"this company has been seen twice {company_name}")
                                        match_found = False
                                        raise ExitLoop
                                    else:
                                        # set match_found boolean to true
                                        match_found = True
                                        # check if ENS data already aligns with CAMS
                                        # if it does break out of loop
                                        print(company_dict["Company Name"][0])
                                        print(company_name)
                                        print(f"names are equal: {company_dict['Company Name'][0] == company_name}")
                                        print(company_dict["Last Name"][0])
                                        print(last_name)
                                        print(f"last names are equal: {company_dict['Last Name'][0]== last_name}")
                                        print(company_dict['Company ID'][0])
                                        print(str(company_id))
                                        print(f"ids are equal: {company_dict['Company ID'][0] == str(company_id)}")
                                        print(formatted_phones_from_page)
                                        print(new_numbers)
                                        print(f"#s are equal: {formatted_phones_from_page == new_numbers}")
                                        if ((company_dict["Company Name"][0] == company_name) and (
                                                company_dict["Last Name"][0] == last_name) and
                                                (company_dict['Company ID'][0] == str(company_id)) and
                                                (formatted_phones_from_page == new_numbers)):
                                            print(f"{company_name} already matches with CAMS")
                                            up_to_date_dic = get_ens_data(driver, up_to_date_dic)
                                            raise ExitLoop

                                        # if ENS doesn't align with CAMS update it
                                        else:
                                            try:
                                                # update all relevant contact information
                                                make_general_ens_update(driver, company_name, company_id, last_name,
                                                                        new_numbers, auto_delete=delete_devices)
                                            except Exception as e:
                                                # send error report because company was not updated appropriately
                                                error_protocol(driver=driver, action='update', company_id=user_id,
                                                               company_name=ens_company_name, exception=e)
                                            else:
                                                # collect ens data after changes have been made
                                                updated_ens_dic = get_ens_data(driver, updated_ens_dic)
                                                print(f"{company_name} has been successfully updated")
                                                raise ExitLoop
                except ExitLoop:
                    print(f"match found boolean: {match_found}")

        # if contact not in CAMS but is labeled as a company, collect it for deletion
        if (not match_found) and (ens_last_name in ["DDE", "DE", "DE & DDE"]):
            print(f"{ens_company_name} does not match with any CAMS number")
            ens_companies_not_in_cams_dic["Primary Phone"].append(company_dict["Primary Phone"][0])
            ens_companies_not_in_cams_dic["Company Name"].append(company_dict["Company Name"][0])
            ens_companies_not_in_cams_dic["Last Name"].append(company_dict["Last Name"][0])
            ens_companies_not_in_cams_dic["Company ID"].append(company_dict["Company ID"][0])
            ens_companies_not_in_cams_dic["Alt Phone 1"].append(company_dict["Alt Phone 1"][0])
            ens_companies_not_in_cams_dic["Alt Phone 2"].append(company_dict["Alt Phone 2"][0])
            ens_companies_not_in_cams_dic["Alt Phone 3"].append(company_dict["Alt Phone 3"][0])



        # collect contacts that don't fall into these categories for reference
        elif not match_found:
            print(f"{ens_company_name} number does not match with any CAMS number")
            ens_contacts_not_in_cams_dic["Primary Phone"].append(company_dict["Primary Phone"][0])
            ens_contacts_not_in_cams_dic["Company Name"].append(company_dict["Company Name"][0])
            ens_contacts_not_in_cams_dic["Last Name"].append(company_dict["Last Name"][0])
            ens_contacts_not_in_cams_dic["Company ID"].append(company_dict["Company ID"][0])
            ens_contacts_not_in_cams_dic["Alt Phone 1"].append(company_dict["Alt Phone 1"][0])
            ens_contacts_not_in_cams_dic["Alt Phone 2"].append(company_dict["Alt Phone 2"][0])
            ens_contacts_not_in_cams_dic["Alt Phone 3"].append(company_dict["Alt Phone 3"][0])

        print()
        print()

    ########## automatically deletes companies that are in ENS but not in CAMS #############
    if delete_contacts:
        for company_id in ens_companies_not_in_cams_dic["Company ID"]:
            try:
                delete_contact_ens(driver, company_id)
            except Exception as e:
                error_protocol(driver=driver, action='delete_contact', company_id=company_id, exception=e)



    ######### initialize date identifier for csvs, csv list, abd explanations list for email #########
    num = datetime.now().strftime("%Y-%m-%d_%H-%M")
    email_csvs = []
    explanations = []

    ###### find multiple occurances of a phone number in ENS data frame ######
    numbers = report_df[['Work Phone Number1', 'Work Phone Number2', 'Work Phone Number3']]
    melted = numbers.melt(var_name='PhonesColumn', value_name='PhoneNumber', ignore_index=False)
    phone_counts = melted.groupby('PhoneNumber').size()
    duplicate_phone_numbers = phone_counts[phone_counts > 1].index
    mask = report_df.apply(lambda row: any(phone in duplicate_phone_numbers for phone in row), axis=1)
    duplicate_result = report_df[mask]
    seen_twice = duplicate_result[
    ['Work Phone Number1', 'First Name', 'Last Name', 'UserID', 'Work Phone Number2', 'Work Phone Number3']]

    ###### check to see if there is CAMS data that has the same primary phone number but other data that differs ######
    # replace null vals for duplicate check
    cams_df_replaced_nulls = cams_df.replace({None: "None", np.nan: "NaN"})
    # get unique values across all columns
    unique_all_replaced_nulls = cams_df_replaced_nulls.drop_duplicates(ignore_index=True)
    # get unique values for primary phone
    unique_primary_replaced_nulls = cams_df_replaced_nulls.drop_duplicates(subset=['PRIMARY_DBL'], ignore_index=True)
    # collect data that is in unique all but not in unique primary
    different_data = unique_all_replaced_nulls[~unique_all_replaced_nulls.apply(tuple, 1).isin(unique_primary_replaced_nulls.apply(tuple, 1))]
    # initialize data objects
    data_discrepencies = pd.DataFrame(
        columns=['DE_OPERATOR_ALIAS_NAME', 'DISPATCH_LOCATION_TYPE', 'DE_ID', 'PRIMARY_DBL', 'ALTERNATIVE_PHONE_1', 'ALTERNATIVE_PHONE_2',
                 'ALTERNATIVE_PHONE_3'])
    data_used = pd.DataFrame(
        columns=['DE_OPERATOR_ALIAS_NAME', 'DISPATCH_LOCATION_TYPE', 'DE_ID', 'PRIMARY_DBL', 'ALTERNATIVE_PHONE_1', 'ALTERNATIVE_PHONE_2',
                 'ALTERNATIVE_PHONE_3'])
    # if there are data discrepencies add them to the email report
    if not different_data.empty:
        for primary_phone in different_data['PRIMARY_DBL'].tolist():
            print(unique_all_replaced_nulls[unique_all_replaced_nulls['PRIMARY_DBL'] == primary_phone])
            data_discrepencies = data_discrepencies._append(unique_all_replaced_nulls[unique_all_replaced_nulls['PRIMARY_DBL'] == primary_phone],
                                                            ignore_index=True)
            data_used = data_used._append(unique_primary_replaced_nulls[unique_primary_replaced_nulls['PRIMARY_DBL'] == unique_primary_replaced_nulls],
                                          ignore_index=True)
        data_discrepencies.to_csv(fr'CSV_reports\data_discrepencies_cams{num}.csv')
        email_csvs.append(rf"{dir}\data_discrepencies_cams{num}.csv")
        explanations.append(
            "CAMS data that has same primary phone number, but has other data that differs. See below for what was used in ENS.")
        data_used.to_csv(fr'CSV_reports\data_used_in_ens{num}.csv')
        email_csvs.append(rf"{dir}\data_used_in_ens{num}.csv")
        explanations.append(
            "This is the data that was used in ENS for differing CAMS data with the same primary phone numbers.")


    ############## check and see if there is data in CAMS that is not in ENS ###################
    # initialize data object
    data_in_cams_not_ens = pd.DataFrame(
        columns=['DE_OPERATOR_ALIAS_NAME', 'DISPATCH_LOCATION_TYPE', 'DE_ID', 'PRIMARY_DBL', 'ALTERNATIVE_PHONE_1', 'ALTERNATIVE_PHONE_2',
                 'ALTERNATIVE_PHONE_3'])
    # loop through primary phone numbers in CAMS
    for primary_phone in unique_primary['PRIMARY_DBL'].tolist():
        # format phone for searching against ENS data collected
        formatted = format_phone_ens(primary_phone)
        # if its in CAMS but not in ENS, make sure it's not in ENS and then update email
        if (formatted not in updated_ens_dic['Primary Phone']) and (formatted not in report_df['Work Phone Number1'].tolist()):
            # double check to make sure initial pass did not miss it
            try:
                search_in_ens(driver, search_by='phone', search_criteria=formatted)
            # if it still does not show up, add it to the report data
            except TimeoutException:
                data_in_cams_not_ens = data_in_cams_not_ens._append(
                    unique_primary[unique_primary['PRIMARY_DBL'] == primary_phone])
            # if you were able to find it, then update the information in ENS
            else:
                company_row = unique_primary[unique_primary['PRIMARY_DBL'] == primary_phone]
                print(company_row[['PRIMARY_DBL', 'ALTERNATIVE_PHONE_1', 'ALTERNATIVE_PHONE_2',
                                                         'ALTERNATIVE_PHONE_3']].iloc[0, :].tolist())
                try:
                    make_general_ens_update(driver, company_row['DE_OPERATOR_ALIAS_NAME'].iloc[0],
                                            company_row['DE_ID'].iloc[0], company_row['DISPATCH_LOCATION_TYPE'].iloc[0],
                                            company_row[['PRIMARY_DBL', 'ALTERNATIVE_PHONE_1', 'ALTERNATIVE_PHONE_2',
                                                         'ALTERNATIVE_PHONE_3']].iloc[0, :].tolist(), delete_devices)
                except Exception as e:
                    error_protocol(driver, action='update', exception=e, company_name=company_row['DE_OPERATOR_ALIAS_NAME'].iloc[0],
                                              company_id=company_row['DE_ID'].iloc[0])
                else:
                    updated_ens_dic = get_ens_data(driver, updated_ens_dic)

    ############### add companies that are in ENS but not in CAMS to email ############
    ens_companies_not_in_cams_df = pd.DataFrame.from_dict(ens_companies_not_in_cams_dic)
    if (len(ens_companies_not_in_cams_df['Company Name']) != 0):
        ens_companies_not_in_cams_df.to_csv(fr"CSV_reports\ens_companies_not_in_cams{num}.csv")
        email_csvs.append(rf"{dir}\ens_companies_not_in_cams{num}.csv")
        if delete_contacts:
            explanations.append("""
               Here is the report for the weekly automated ENS update. If anything seems incorrect and changes need to be restored,
                           the attached csv contains all the ENS data before updates were made. Please review the items below. \r \r
               ENS companies that are not in CAMS. They have all been deleted from ENS.""")
        else:
            explanations.append(""""Here is the report for the weekly automated ENS update. If anything seems incorrect and changes need to be restored,
                                       the attached csv contains all the ENS data before updates were made. Please review the items below. 
                                       \r \r ENS companies that are not in CAMS""")

    ############### add data that is in CAMS but not in ENS to email ############
    if (len(data_in_cams_not_ens['DE_ID']) != 0):
        data_in_cams_not_ens.to_csv(fr'CSV_reports\data_in_cams_not_ens{num}.csv')
        email_csvs.append(rf"{dir}\data_in_cams_not_ens{num}.csv")
        explanations.append("Data that exists in CAMS but not in ENS.")

    ############### add contacts that are in ENS but not in CAMS to email ############
    ens_contacts_not_in_cams_df = pd.DataFrame.from_dict(ens_contacts_not_in_cams_dic)
    if (len(ens_contacts_not_in_cams_df["Company Name"]) != 0):
        ens_contacts_not_in_cams_df.to_csv(fr"CSV_reports\ens_contact_not_in_cams{num}.csv")
        email_csvs.append(rf"{dir}\ens_contact_not_in_cams{num}.csv")
        explanations.append("ENS contacts that are not in CAMS")

    ############### add contacts that appear twice in ENS to email ############
    seen_twice_df = pd.DataFrame.from_dict(seen_twice)
    if (len(seen_twice_df['First Name']) != 0):
        seen_twice_df.to_csv(fr"CSV_reports\seen_twice_df{num}.csv")
        email_csvs.append(rf"{dir}\seen_twice_df{num}.csv")
        explanations.append(
            "Companies in ENS that share a phone number. One was deleted because they have the same CAMS data")


    ############ add updated ENS data to email ########################
    updated_ens_df = pd.DataFrame.from_dict(updated_ens_dic)
    if (len(updated_ens_df["Company Name"]) != 0):
        updated_ens_df.to_csv(fr"CSV_reports\updated_ens_data{num}.csv")
        email_csvs.append(rf"{dir}\updated_ens_data{num}.csv")
        explanations.append('Here are the ENS companies that have been updated')

    ############ add up to date ENS data to email ########################
    up_to_date_df = pd.DataFrame.from_dict(up_to_date_dic)
    if (len(up_to_date_df["Company Name"]) != 0):
        up_to_date_df.to_csv(fr"CSV_reports\up_to_date_ens_data{num}.csv")
        email_csvs.append(rf"{dir}\up_to_date_ens_data{num}.csv")
        explanations.append('Here are the ENS companies that are up to date with CAMS')


    ########### get report to attach as a csv to email #############
    file_pattern = re.compile(r"All_Contacts_all_info.*\.csv")
    download_dir = fr"{dir}"
    timeout = 5
    start_time = time.time()
    newest_file_path = ""
    while time.time() - start_time < timeout:
        matching_files = [os.path.join(download_dir, filename) for filename in os.listdir(download_dir) if
                          file_pattern.match(filename)]
        if matching_files:
            newest_file_path = max(matching_files, key=os.path.getctime)
            break

    if not newest_file_path:
        error_protocol(driver, action='report')


    #################### send email ####################
    send_csvs_as_html(email_csvs, explanations, 'Full ENS clean', 'bwimer@iso-ne.com',
                      'opticalloutsupport@iso-ne.com', attachments=[newest_file_path])


    ########### logout and close driver #########
    # logout
    logout_ens(driver)
    # test to see if logout successful, if successful, close driver
    error_protocol(driver, action='logout')
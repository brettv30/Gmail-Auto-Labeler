# Gmail Auto Labeler
A script that automatically labels emails in your Gmail inbox based on their sender. 

## How to get started
1. Ensure you have python and git installed on your local machine.
2. Clone the repository to your local machine.
3. Create a virtual environment (.venv) within the repository and activate it
4. Within the virtual environment install the required dependencies by running `pip install -r requirements.txt`.
5. Create a file named `Config.json` in the root directory of the project.
6. Create the folders `creds` and `logs` in the root directory of the project.
7. Open the `Config.json` file and indicate the sender-label pairs you want to use as well as the number of days you want the script to look back. See `example-config.json` for an example.
8. Go to the [Google Cloud Console](https://console.cloud.google.com/welcome)
9. Create a new project titled `Gmail-Auto-Labeler`
10. Enable the Gmail API within the project
11. Create Oauth 2.0 credentials and download the credentials json file
12. Ensure the email address you want to use is added as a Test user on the `OAuth Consent Screen` tab of the APIs & Services section of the project
13. Move the file with the credentials into the `creds` folder and rename the file to `credentials.json`
14. Run the `Gmail_Auto_Labeler.py` script

## How to automatically run the script (Task Scheduler)
1. Open the Task Scheduler
2. Click `Create Task...`
3. Give the task a name and description
4. On the Triggers tab, click `New...`
5. Select the type of trigger you want to start the script. This can be on a daily schedule, on workstation unlock, etc. 
6. Click `OK`
7. On the Actions tab, click `New...`
8. Select `Start a program`
9. In the `Program/script` field, enter the path to the python executable in your virtual environment (.venv). This should be the full path to the python.exe file in the Scripts folder. 
10. In the `Add arguments (optional)` field, enter `Gmail_Auto_Labeler.py`
11. In the `Start in (optional)` field, enter the path to the root directory of the project. Ex. C:\Users\{username}\Desktop\Gmail-Auto-Labeler\
12. Click `OK`
13. Click `OK`
14. Test that the script works based on the trigger set in steps 4-6. If it doesn't, repeat this process until you find a trigger that you are happy with. If it does, then you are all set and should see your new emails with the proper labels attached after the script executes. 

## General Notes
- A token.json file will be generated in the `creds` folder. This file is used to store the access token for the user and is reset on a regular cadence. If you run the script and find that you need to authorize this project through Gmail, simply authorize the project on Gmail and the token.json file will be updated.
- The logs folder contains the logs generated from each run of the script
- SENDER_LABELS is the json variable that holds the sender emails you want to label and the label you want to apply to all emails received from those senders. Ex. If I want to label everything from venmo@venmo.com with the label 'Venmo' then I would set it up in the config like "venmo@venmo.com":"Venmo". 
- DAYS_TO_LOOK_BACK is the number of days you want the script to look back in your inbox for emails to label. Ex. If I want to look back at the most recent 30 days, then I would set the value like "Days":"30".

## Potential Improvements
- Add parallel processing for all emails from a given sender
- Add parallel processing for all senders
- Add functionality to add labels to emails based on the subject line
- Increase the amount of time before requesting a new access token
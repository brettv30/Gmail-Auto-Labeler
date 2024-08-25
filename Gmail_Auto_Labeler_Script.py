import os
import json
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

# Setup logging
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f"{current_time}-gmail-auto-labeler.log"

# Ensure the 'logs' & 'creds' directories exists
os.makedirs("logs", exist_ok=True)
os.makedirs("creds", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join("logs", log_filename)),
        logging.StreamHandler(),
    ],
)

# If modifying these SCOPES, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def load_config(config_path: str) -> Dict:
    """
    Load the configuration from the specified JSON file.

    This function reads the contents of a JSON configuration file located at the
    specified `config_path` and returns the parsed configuration as a dictionary.
    If the file is not found or the JSON content is invalid, the function will log
    the error and raise the corresponding exception.

    Args:
        config_path (str): The file path of the JSON configuration file.

    Returns:
        Dict: The configuration loaded from the JSON file.

    Raises:
        FileNotFoundError: If the configuration file is not found.
        json.JSONDecodeError: If there is an error parsing the JSON content.
    """
    try:
        with open(config_path, "r") as config_file:
            config = json.load(config_file)
        logging.info("Configuration loaded successfully.")
        return config
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing the configuration file: {e}")
        raise


def authenticate_gmail() -> Resource:
    """
    Authenticate the user with Gmail API and return the service resource.

    This function handles the authentication process for the Gmail API. It first
    checks if there are valid credentials stored in the 'token.json' file. If the
    credentials are expired, it refreshes them. If no valid credentials are found,
    it initiates an OAuth flow to obtain new credentials and saves them to the
    'token.json' file.

    Once the credentials are obtained, the function builds the Gmail API service
    and returns it.

    Returns:
        Resource: The Gmail API service resource.
    """
    logging.info("Starting Gmail authentication process.")

    creds: Optional[Credentials] = None
    try:
        if os.path.exists("creds\\token.json"):
            logging.info("Loading credentials from creds\\token.json.")
            creds = Credentials.from_authorized_user_file("creds\\token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logging.info("Refreshing expired credentials.")
                creds.refresh(Request())
            else:
                logging.info("No valid credentials available, initiating OAuth flow.")
                flow = InstalledAppFlow.from_client_secrets_file(
                    "creds\\credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open("creds\\token.json", "w") as token:
                token.write(creds.to_json())
                logging.info("Credentials saved to creds\\token.json.")
        else:
            logging.info("Valid credentials found.")

        service = build("gmail", "v1", credentials=creds)
        logging.info("Gmail API service built successfully.")
        return service

    except Exception as e:
        logging.error(f"An error occurred during Gmail authentication: {e}")
        raise


def get_or_create_label(service: Resource, label_name: str) -> str:
    """
    Retrieve a label ID if it exists, or create the label if it doesn't.

    This function checks if a Gmail label with the given name already exists. If the label
    is found, it returns the label's ID. If the label is not found, it creates a new label
    with the given name and returns the new label's ID.

    Args:
        service (Resource): The Gmail API service resource.
        label_name (str): The name of the label to retrieve or create.

    Returns:
        str: The ID of the retrieved or created label.

    Raises:
        HttpError: If an error occurs while interacting with the Gmail API.
    """
    try:
        labels = service.users().labels().list(userId="me").execute()
        label_map = {label["name"]: label["id"] for label in labels["labels"]}

        if label_name in label_map:
            logging.info(f"Label '{label_name}' already exists.")
            return label_map[label_name]
        else:
            logging.info(f"Label '{label_name}' not found. Creating new label.")
            label_body = {
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
                "name": label_name,
            }
            label = (
                service.users().labels().create(userId="me", body=label_body).execute()
            )
            logging.info(f"Label '{label_name}' created successfully.")
            return label["id"]

    except HttpError as error:
        logging.error(
            f"An error occurred while retrieving or creating label '{label_name}': {error}"
        )
        raise


def label_emails(
    service: Resource, sender_label_map: Dict[str, str], days_to_look_back: int
) -> None:
    """
    Label all emails from the specified senders with the given labels, only if the emails don't already have the label.

    This function retrieves all Gmail labels, then for each sender-label mapping,
    it searches for emails from the sender within the last specified number of days.
    If the email doesn't already have the label, it applies the label to the email.

    Args:
        service (Resource): The Gmail API service resource.
        sender_label_map (Dict[str, str]): A dictionary mapping sender email addresses to label names.
        days_to_look_back (int): The number of days to look back when searching for emails.

    Raises:
        HttpError: If an error occurs while interacting with the Gmail API.
    """
    try:
        for sender_email, label_name in sender_label_map.items():
            label_id = get_or_create_label(service, label_name)

            if not label_id:
                logging.warning(
                    f"Label '{label_name}' not found for sender {sender_email}."
                )
                continue

            # Calculate the date 'days_to_look_back' days ago
            date_n_days_ago = (
                datetime.now() - timedelta(days=days_to_look_back)
            ).strftime("%Y/%m/%d")

            # Search for all messages from the specified sender within the last 'days_to_look_back' days
            query: str = f"from:{sender_email} after:{date_n_days_ago}"
            results = service.users().messages().list(userId="me", q=query).execute()
            messages = results.get("messages", [])

            if not messages:
                logging.info(
                    f"No emails found from {sender_email} in the last {days_to_look_back} days."
                )
                continue

            # Apply the label to messages that don't already have it
            for message in messages:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=message["id"], format="metadata")
                    .execute()
                )
                existing_labels = msg.get("labelIds", [])

                if label_id not in existing_labels:
                    service.users().messages().modify(
                        userId="me", id=message["id"], body={"addLabelIds": [label_id]}
                    ).execute()
                    logging.info(
                        f"Labeled email ID {message['id']} from {sender_email} with label '{label_name}'"
                    )
                else:
                    logging.info(
                        f"Email ID {message['id']} from {sender_email} already has the label '{label_name}'"
                    )

    except HttpError as error:
        logging.error(f"An error occurred: {error}")


def main() -> None:
    """
    Entrypoint for the Gmail Auto Labeler script.

    This function reads the sender-label mapping and the number of days to look back from the config file,
    authenticates with the Gmail API, and then labels emails from the specified senders based on the corresponding labels.
    """
    # Load the configuration from the JSON file
    config_path = "config.json"
    config = load_config(config_path)

    sender_labels = config.get("SENDER_LABELS", {})
    days_to_look_back_str = config.get("DAYS_TO_LOOK_BACK", {}).get("Days", "30")

    if not sender_labels:
        logging.warning("No sender-label mappings found in SENDER_LABELS.")
        return

    try:
        days_to_look_back: int = int(days_to_look_back_str)
    except ValueError:
        logging.error(
            f"Invalid value for DAYS_TO_LOOK_BACK: {days_to_look_back_str}. Must be an integer."
        )
        return

    service: Resource = authenticate_gmail()
    label_emails(service, sender_labels, days_to_look_back)


if __name__ == "__main__":
    main()

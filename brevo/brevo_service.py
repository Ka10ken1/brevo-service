import csv
import requests
import logging
import io
import os
from dotenv import load_dotenv


load_dotenv()

SENDER_NAME = os.getenv("SENDER_NAME")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
CAMPAIGN_LIST_ID = os.getenv("CAMPAIGN_LIST_ID")

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more details
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

API_KEY = os.getenv("BREVO_API_KEY")

HEADERS = {
    "api-key": API_KEY,
    "accept": "application/json",
    "content-type": "application/json",
}


def get_existing_contacts():
    url = "https://api.brevo.com/v3/contacts"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    logging.info("Fetched existing contacts from Brevo API.")
    return {contact["email"].lower() for contact in data.get("contacts", [])}


def add_contact(email: str, existing_contacts: set, list_ids=None):

    if email in existing_contacts:
        logging.info(f"[-] {email} is already a contact.")
        return

    url = "https://api.brevo.com/v3/contacts"

    payload = {
        "email": email,
        "updateEnabled": True,  # Update if contact already exists
    }

    if list_ids:
        payload["listIds"] = list_ids
    elif CAMPAIGN_LIST_ID:
        payload["listIds"] = [CAMPAIGN_LIST_ID]

    response: requests.Response = requests.post(url, json=payload, headers=HEADERS)

    if response.status_code not in (201, 204):
        logging.warning(
            f"Failed to add contact {email}: {response.status_code} {response.text}"
        )
    else:
        logging.info(f"Added contact {email}")

    return response


def send_info_email_campaign():
    url = "https://api.brevo.com/v3/emailCampaigns"
    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "name": "Winner Announcement",
        "subject": "🎉 You've Won Something!",
        "htmlContent": """
            <html>
                <body>
                    <h1>Congratulations!</h1>
                    <p>You have won something amazing. Stay tuned!</p>
                </body>
            </html>
        """,
        "recipients": {"listIds": [CAMPAIGN_LIST_ID]},
        # Optional: Schedule the email for later
        # "scheduledAt": "2025-07-18T18:00:00+04:00"
    }

    response = requests.post(url, json=payload, headers=HEADERS)

    if response.status_code not in (201, 202):
        logging.warning(
            f"Failed to create campaign: {response.status_code} {response.text}"
        )
    else:
        logging.info("Campaign email created and scheduled/sent.")
    return response


def send_info_email(email: str):
    url = "https://api.brevo.com/v3/smtp/email"
    payload = {
        "to": [{"email": email}],
        "subject": "Here's what you need to know",
        "htmlContent": "<p>Dear user, here is the information you requested.</p>",
        "sender": {"name": "Brevo Bot", "email": "your@email.com"},
    }

    resp: requests.Response = requests.post(url, json=payload, headers=HEADERS)
    if resp.status_code not in (200, 201):
        logging.warning(
            f"Failed to send email to {email}: {resp.status_code} {resp.text}"
        )
    else:
        logging.info(f"Info email sent to {email}")
    return resp


def handle_csv(file_bytes: bytes):
    decoded = file_bytes.decode("utf-8")

    reader = csv.DictReader(io.StringIO(decoded))

    existing_contacts = get_existing_contacts()
    results = {"added_contacts": [], "info_sent": [], "errors": []}

    for row in reader:
        email = row.get("email") or row.get("Email", "")
        email = email.strip().lower()
        if not email:
            continue

        try:
            if email in existing_contacts:
                resp = send_info_email(email)
                if resp.status_code in (200, 201, 202):
                    results["info_sent"].append(email)
                else:
                    results["errors"].append({"email": email, "error": resp.text})
            else:
                resp = add_contact(email, existing_contacts)
                if resp and resp.status_code in (201, 204):
                    results["added_contacts"].append(email)
                    existing_contacts.add(email)
                else:
                    results["errors"].append(
                        {
                            "email": email,
                            "error": (resp.text if resp else "No response"),
                        }
                    )
        except Exception as e:
            results["errors"].append({"email": email, "error": str(e)})

    return results

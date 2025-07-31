import csv
import requests
import logging
import io
import os
from datetime import datetime
import time
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

SENDER_NAME = os.getenv("SENDER_NAME")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

API_KEY = os.getenv("BREVO_API_KEY")

HEADERS = {
    "api-key": API_KEY,
    "accept": "application/json",
    "content-type": "application/json",
}


class MockResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


def get_existing_contacts_email():
    all_contacts = set()
    offset = 0
    limit = 1000

    logging.info("Starting to fetch all existing contacts...")

    while True:
        url = f"https://api.brevo.com/v3/contacts?limit={limit}&offset={offset}"

        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()

            contacts = data.get("contacts", [])

            if not contacts:
                break

            for contact in contacts:
                email = contact.get("email")
                if email:
                    all_contacts.add(email.lower())

            logging.info(
                f"Fetched {len(contacts)} contacts (offset: {offset}). Total so far: {len(all_contacts)}"
            )

            if len(contacts) < limit:
                break

            offset += limit

            time.sleep(0.1)

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching contacts at offset {offset}: {str(e)}")
            break
        except Exception as e:
            logging.error(
                f"Unexpected error fetching contacts at offset {offset}: {str(e)}"
            )
            break

    logging.info(
        f"Finished fetching contacts. Total: {len(all_contacts)} unique emails found"
    )
    return all_contacts


def get_detailed_contacts():
    all_contacts = []
    offset = 0
    limit = 1000  # Maximum allowed by Brevo for contacts endpoint

    logging.info("Starting to fetch all detailed contacts...")

    while True:
        url = f"https://api.brevo.com/v3/contacts?limit={limit}&offset={offset}"

        try:
            response = requests.get(url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()

            contacts = data.get("contacts", [])

            if not contacts:
                break

            for contact in contacts:
                contact_info = {
                    "id": contact.get("id"),
                    "email": contact.get("email"),
                    "emailBlacklisted": contact.get("emailBlacklisted", False),
                    "smsBlacklisted": contact.get("smsBlacklisted", False),
                    "createdAt": contact.get("createdAt"),
                    "modifiedAt": contact.get("modifiedAt"),
                    "listIds": contact.get("listIds", []),
                    "attributes": contact.get("attributes", {}),
                }
                all_contacts.append(contact_info)

            logging.info(
                f"Fetched {len(contacts)} detailed contacts (offset: {offset}). Total so far: {len(all_contacts)}"
            )

            if len(contacts) < limit:
                break

            offset += limit

            time.sleep(0.1)

        except requests.exceptions.RequestException as e:
            logging.error(
                f"Error fetching detailed contacts at offset {offset}: {str(e)}"
            )
            break
        except Exception as e:
            logging.error(
                f"Unexpected error fetching detailed contacts at offset {offset}: {str(e)}"
            )
            break

    logging.info(
        f"Finished fetching detailed contacts. Total: {len(all_contacts)} contacts found"
    )
    return all_contacts


def add_contact(email: str, existing_contacts: set, list_ids=None, contact_data=None):
    if not API_KEY:
        logging.error("BREVO_API_KEY is not configured in environment variables")
        return MockResponse(500, "BREVO_API_KEY not configured")

    logging.info(f"users list: {len(existing_contacts)} contacts found")
    contact_exists = email in existing_contacts
    if contact_exists:
        logging.info(
            f"[-] {email} already exists. Will update with new data if provided."
        )

    payload = build_payload(email, list_ids, contact_data)
    return send_contact_payload(email, payload, contact_exists)


def get_or_create_folder(name: str) -> int | None:
    url = "https://api.brevo.com/v3/contacts/folders"
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        folders = response.json().get("folders", [])

        for folder in folders:
            if folder.get("name") == name:
                logging.info(
                    f"Found existing folder '{name}' with ID: {folder.get('id')}"
                )
                return folder.get("id")

    except Exception as e:
        logging.error(f"Error checking existing folders: {str(e)}")
        return None

    logging.info(f"Folder '{name}' not found. Creating new one...")
    return create_folder(name)


def create_folder(name: str) -> int | None:
    url = "https://api.brevo.com/v3/contacts/folders"
    payload = {"name": name}

    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        if response.status_code in (201, 202):
            folder_id = response.json().get("id")
            logging.info(f"Created new folder '{name}' with ID: {folder_id}")
            return folder_id
        else:
            logging.error(f"Failed to create folder '{name}': {response.text}")
            return None
    except Exception as e:
        logging.error(f"Exception creating folder '{name}': {str(e)}")
        return None


def create_new_contact_list(csv_name: str) -> int | None:
    folder_id = get_or_create_folder("Winners")  # One folder to rule them all

    if not folder_id:
        logging.error("Failed to get or create folder for contact lists")
        return None

    url = "https://api.brevo.com/v3/contacts/lists"

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    payload = {
        "name": f"Imported List - {csv_name} - {now_str}",
        "folderId": folder_id,
    }

    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        if response.status_code in (201, 202):
            list_id = response.json().get("id")
            logging.info(f"Created new contact list with ID: {list_id}")
            return list_id
        else:
            logging.error(f"Failed to create contact list: {response.text}")
            return None
    except Exception as e:
        logging.error(f"Exception creating contact list: {str(e)}")
        return None


def rename_folder(folder_id: int, new_name: str) -> bool:
    url = f"https://api.brevo.com/v3/contacts/folders/{folder_id}"
    payload = {"name": new_name}

    try:
        response = requests.put(url, json=payload, headers=HEADERS)
        if response.status_code in (200, 204):
            logging.info(f"Renamed folder {folder_id} to '{new_name}'")
            return True
        else:
            logging.error(f"Failed to rename folder {folder_id}: {response.text}")
            return False
    except Exception as e:
        logging.error(f"Exception while renaming folder {folder_id}: {str(e)}")
        return False


def build_payload(email: str, list_ids, contact_data: dict | None) -> dict:
    payload = {
        "email": email,
        "updateEnabled": True,
    }

    attributes = build_attributes(contact_data)
    if attributes:
        payload["attributes"] = attributes
        logging.info(f"Adding contact with attributes: {attributes}")
    else:
        logging.info(
            "No attributes to add - contact_data was empty or had no valid fields"
        )

    if list_ids:
        payload["listIds"] = list_ids

    return payload


def build_attributes(contact_data: dict | None) -> dict:
    if not contact_data:
        return {}

    attributes = {}
    field_mapping = {
        "vendor_name": "COMPANY_NAME",
        "company_id": "COMPANY_ID",
        "phone": "SMS",
        "tender_code": "TENDER_CODE",
    }

    for key, value in contact_data.items():
        if value and key in field_mapping:
            attributes[field_mapping[key]] = value

    return attributes


def send_contact_payload(email: str, payload: dict, contact_exists: bool):
    url = "https://api.brevo.com/v3/contacts"

    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        logging.info(f"Brevo API response: {response.status_code} - {response.text}")

        if is_duplicate_sms_error(response):
            return retry_without_sms(email, payload)

        if response.status_code not in (201, 204):
            logging.warning(
                f"Failed to add/update contact {email}: {response.status_code} {response.text}"
            )
        else:
            action = "Updated" if contact_exists else "Added"
            logging.info(f"{action} contact {email} with additional data")

        return response

    except Exception as e:
        logging.error(
            f"Exception occurred while contacting Brevo API for {email}: {str(e)}"
        )
        return MockResponse(500, f"API Exception: {str(e)}")


def is_duplicate_sms_error(response: requests.Response) -> bool:
    return (
        response.status_code == 400
        and "SMS is already associated with another Contact" in response.text
    )


def retry_without_sms(email: str, payload: dict):
    logging.warning(
        f"SMS already exists for another contact. Retrying {email} without SMS field..."
    )

    attributes = payload.get("attributes", {})
    payload_without_sms = payload.copy()
    payload_without_sms["attributes"] = {
        k: v for k, v in attributes.items() if k != "SMS"
    }

    if payload_without_sms["attributes"]:
        logging.info(f"Retrying with payload: {payload_without_sms}")
        retry_response = requests.post(
            "https://api.brevo.com/v3/contacts",
            json=payload_without_sms,
            headers=HEADERS,
        )
        logging.info(
            f"Retry without SMS - Brevo API response: {retry_response.status_code} - {retry_response.text}"
        )
        return retry_response
    else:
        logging.info(f"No other attributes to update for {email}, treating as success")
        return MockResponse(204, "No attributes to update after removing duplicate SMS")


def load_html_template(filename: str) -> str:
    base_dir = Path(__file__).resolve().parent
    file_path = base_dir / "template" / filename

    logging.debug(f"Loading HTML template from: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def create_new_campaign(list_id: int) -> dict:
    url = "https://api.brevo.com/v3/emailCampaigns"

    html_content = load_html_template("message_template.html")

    timestamp = int(time.time())
    campaign_name = f"CSV Import Campaign - {timestamp}"

    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "name": campaign_name,
        "subject": "დოკუმენტაციის თარგმნა ნოტარიულად დამოწმებით",
        "htmlContent": html_content,
        "recipients": {"listIds": [list_id]},
    }

    try:
        response = requests.post(url, json=payload, headers=HEADERS)

        if response.status_code in (201, 202):
            campaign_data = response.json()
            logging.info(
                f"Campaign '{campaign_name}' created successfully with ID: {campaign_data.get('id')}"
            )
            return {
                "success": True,
                "campaign_id": campaign_data.get("id"),
                "campaign_name": campaign_name,
                "status_code": response.status_code,
            }
        else:
            logging.warning(
                f"Failed to create campaign: {response.status_code} {response.text}"
            )
            return {
                "success": False,
                "error": f"API Error: {response.status_code} - {response.text}",
                "status_code": response.status_code,
            }
    except Exception as e:
        logging.error(f"Exception occurred while creating campaign: {str(e)}")
        return {"success": False, "error": f"Exception: {str(e)}", "status_code": None}


def send_campaign_to_contacts(campaign_id: int) -> dict:
    url = f"https://api.brevo.com/v3/emailCampaigns/{campaign_id}/sendNow"

    try:
        response = requests.post(url, headers=HEADERS)

        if response.status_code in (200, 202, 204):
            logging.info(f"Campaign {campaign_id} sent successfully")
            return {
                "success": True,
                "message": f"Campaign {campaign_id} sent to all contacts",
                "status_code": response.status_code,
            }
        else:
            logging.warning(
                f"Failed to send campaign {campaign_id}: {response.status_code} {response.text}"
            )
            return {
                "success": False,
                "error": f"Send failed: {response.status_code} - {response.text}",
                "status_code": response.status_code,
            }
    except Exception as e:
        logging.error(
            f"Exception occurred while sending campaign {campaign_id}: {str(e)}"
        )
        return {"success": False, "error": f"Exception: {str(e)}", "status_code": None}


def send_info_email(email: str):
    if not SENDER_EMAIL:
        logging.error("SENDER_EMAIL not configured in environment variables")
        raise ValueError("SENDER_EMAIL is required for sending emails")

    url = "https://api.brevo.com/v3/smtp/email"

    html_content = load_html_template("message_template.html")

    payload = {
        "to": [{"email": email}],
        "subject": "დოკუმენტაციის თარგმნა ნოტარიულად დამოწმებით",
        "htmlContent": f"{html_content}",
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
    }

    resp: requests.Response = requests.post(url, json=payload, headers=HEADERS)
    if resp.status_code not in (200, 201):
        logging.warning(
            f"Failed to send email to {email}: {resp.status_code} {resp.text}"
        )
        try:
            error_details = resp.json()
            logging.error(f"Brevo API error details: {error_details}")
        except:
            logging.error(f"Raw error response: {resp.text}")
    else:
        logging.info(f"Info email sent to {email}")
    return resp


def get_campaign_details(campaign_id: int) -> dict:
    url = f"https://api.brevo.com/v3/emailCampaigns/{campaign_id}"

    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            campaign_data = response.json()
            logging.info(f"Campaign {campaign_id} details: {campaign_data}")
            return campaign_data
        else:
            logging.error(
                f"Failed to get campaign details: {response.status_code} {response.text}"
            )
            return {}
    except Exception as e:
        logging.error(f"Exception getting campaign details: {str(e)}")
        return {}


def extract_email(row: dict) -> str:
    email = row.get("email") or row.get("Email") or row.get("EMAIL", "")
    return email.strip().lower() if email else ""


def extract_contact_data(row: dict) -> dict:
    csv_field_mapping = {
        "VendorName": "vendor_name",
        "IdCode": "company_id",
        "Phone": "phone",
        "CATEGORY": "tender_code",
    }
    contact_data = {}
    for csv_col, field_name in csv_field_mapping.items():
        value = row.get(csv_col, "").strip()
        if value and value not in ("", "http://"):
            contact_data[field_name] = value
    return contact_data


def process_contact(
    email: str,
    contact_data: dict,
    existing_emails: set,
    results: dict,
    campaign_list_id: int,
    detailed_contacts_by_email: dict,
):
    if email in existing_emails:
        update_existing_contact(
            email,
            campaign_list_id,
            contact_data,
            results,
            existing_emails,
            detailed_contacts_by_email,
        )
    else:
        create_new_contact_for_campaign(
            email, contact_data, existing_emails, results, campaign_list_id
        )


def check_contact_status(email: str):
    url = f"https://api.brevo.com/v3/contacts/{email}"

    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            contact_data = response.json()
            logging.info(f"Contact {email} status:")
            logging.info(
                f"  - Email Blacklisted: {contact_data.get('emailBlacklisted', False)}"
            )
            logging.info(
                f"  - SMS Blacklisted: {contact_data.get('smsBlacklisted', False)}"
            )
            logging.info(f"  - List IDs: {contact_data.get('listIds', [])}")
            return contact_data
        else:
            logging.error(
                f"Failed to get contact status: {response.status_code} {response.text}"
            )
            return None
    except Exception as e:
        logging.error(f"Exception checking contact status: {str(e)}")
        return None


def update_existing_contact(
    email: str,
    campaign_list_id: int,
    contact_data: dict,
    results: dict,
    existing_emails: set,
    detailed_contacts_by_email: dict,
):
    existing = detailed_contacts_by_email.get(email)

    if existing:
        if existing.get("emailBlacklisted", False):
            logging.warning(
                f"Contact {email} is EMAIL BLACKLISTED - will not receive emails!"
            )
        if existing.get("smsBlacklisted", False):
            logging.warning(f"Contact {email} is SMS BLACKLISTED")

        old_code = existing.get("attributes", {}).get("TENDER_CODE", "")
        new_code = contact_data.get("tender_code", "")
        if new_code and old_code and new_code != old_code:
            contact_data["tender_code"] = f"{new_code};{old_code}"
            logging.info(
                f"Updated tender_code for {email}: {contact_data['tender_code']}"
            )

    if existing:
        old_code = existing.get("attributes", {}).get("TENDER_CODE", "")
        new_code = contact_data.get("tender_code", "")
        if new_code and old_code and new_code != old_code:
            contact_data["tender_code"] = f"{new_code};{old_code}"
            logging.info(
                f"Updated tender_code for {email}: {contact_data['tender_code']}"
            )

    resp = add_contact(
        email, existing_emails, list_ids=[campaign_list_id], contact_data=contact_data
    )

    if resp and resp.status_code in (201, 204):
        results["updated_contacts"].append({"email": email, "data": contact_data})
        logging.info(
            f"Existing contact {email} updated and added to campaign list {campaign_list_id}"
        )
    else:
        results["errors"].append(
            {
                "email": email,
                "error": f"Failed to update contact: {resp.text if resp else 'No response'}",
            }
        )


def create_new_contact_for_campaign(
    email: str,
    contact_data: dict,
    existing_emails: set,
    results: dict,
    campaign_list_id: int,
):
    resp = add_contact(
        email, existing_emails, list_ids=[campaign_list_id], contact_data=contact_data
    )
    if resp and resp.status_code in (201, 204):
        action = "updated" if resp.status_code == 204 else "created"
        results["added_to_campaign"].append(
            {"email": email, "data": contact_data, "action": action}
        )
        existing_emails.add(email)
        logging.info(
            f"New contact {email} {action} and added to campaign list {campaign_list_id}"
        )
    else:
        results["errors"].append(
            {"email": email, "error": (resp.text if resp else "No response")}
        )


def _get_csv_reader(file_bytes: bytes):
    decoded = file_bytes.decode("utf-8")
    return csv.DictReader(io.StringIO(decoded))


def _fetch_existing_contacts():
    logging.info("Fetching all existing contacts from Brevo...")
    existing_contacts_email = get_existing_contacts_email()
    detailed_contacts = get_detailed_contacts()

    detailed_contacts_by_email = {
        c["email"].lower(): c for c in detailed_contacts if c.get("email")
    }

    logging.info(
        f"Found {len(existing_contacts_email)} existing contacts in your Brevo account"
    )

    return existing_contacts_email, detailed_contacts_by_email


def _init_results(total_existing: int):
    return {
        "added_to_campaign": [],
        "updated_contacts": [],
        "errors": [],
        "campaign_info": {},
        "total_existing_contacts": total_existing,
    }


def _ensure_folder(name: str):
    folder_id = get_or_create_folder(name)
    if not folder_id:
        logging.error(f"Failed to find or create '{name}' folder. Aborting.")
    return folder_id


def _process_all_rows(
    reader,
    existing_emails: set,
    detailed_contacts_by_email: dict,
    results: dict,
    campaign_list_id: int,
):
    for row in reader:
        email = extract_email(row)
        if not email:
            logging.warning(f"Skipping row with missing/invalid email: {row}")
            continue

        contact_data = extract_contact_data(row)

        try:
            process_contact(
                email,
                contact_data,
                existing_emails,
                results,
                campaign_list_id,
                detailed_contacts_by_email,
            )
        except Exception as e:
            results["errors"].append({"email": email, "error": str(e)})


def handle_csv(file_bytes: bytes):
    reader = _get_csv_reader(file_bytes)
    existing_emails, detailed_by_email = _fetch_existing_contacts()

    results = _init_results(len(existing_emails))

    folder_id = _ensure_folder("Winners")
    if not folder_id:
        return {"errors": [{"error": "Folder setup failed"}]}

    csv_list_id = create_new_contact_list("csv_import")
    if not csv_list_id:
        return {"errors": [{"error": "Failed to create contact list"}]}

    campaign_result = create_new_campaign(csv_list_id)

    logging.info(campaign_result)

    results["campaign_info"] = campaign_result

    if not campaign_result["success"]:
        results["errors"].append(
            {"error": "Failed to create campaign", "details": campaign_result["error"]}
        )
        return results

    _process_all_rows(
        reader,
        existing_emails,
        detailed_by_email,
        results,
        csv_list_id,
    )

    campaign_id = campaign_result["campaign_id"]

    # Debug: Check campaign details before sending
    # logging.info("=== DEBUGGING CAMPAIGN BEFORE SENDING ===")
    # campaign_details = get_campaign_details(campaign_id)

    # logging.info("=== CHECKING CONTACT STATUS ===")
    # check_contact_status("matekopaliani12@gmail.com")
    # logging.info("=== END CONTACT STATUS ===")

    # Debug: Check list contents
    # list_details_url = f"https://api.brevo.com/v3/contacts/lists/{csv_list_id}"
    # try:
    #     list_response = requests.get(list_details_url, headers=HEADERS)
    #     if list_response.status_code == 200:
    #         list_data = list_response.json()
    #         logging.info(
    #             f"List {csv_list_id} has {list_data.get('totalSubscribers', 0)} subscribers"
    #         )
    #         logging.info(f"List details: {list_data}")
    #     else:
    #         logging.error(
    #             f"Failed to get list details: {list_response.status_code} {list_response.text}"
    #         )
    # except Exception as e:
    #     logging.error(f"Exception getting list details: {str(e)}")
    #
    # logging.info("=== END DEBUGGING ===")
    #
    send_result = send_campaign_to_contacts(campaign_id)
    results["campaign_info"]["send_result"] = send_result

    if send_result["success"]:
        logging.info("Campaign sent successfully to all contacts in the CSV list!")
    else:
        logging.error(f"Failed to send campaign: {send_result['error']}")

    return results

import csv
import requests
import logging
import io
import os
import time
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()

SENDER_NAME = os.getenv("SENDER_NAME")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
CAMPAIGN_LIST_ID = int(os.getenv("CAMPAIGN_LIST_ID"))

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
            
            logging.info(f"Fetched {len(contacts)} contacts (offset: {offset}). Total so far: {len(all_contacts)}")
            
            if len(contacts) < limit:
                break
                
            offset += limit
            
            time.sleep(0.1)
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching contacts at offset {offset}: {str(e)}")
            break
        except Exception as e:
            logging.error(f"Unexpected error fetching contacts at offset {offset}: {str(e)}")
            break
    
    logging.info(f"Finished fetching contacts. Total: {len(all_contacts)} unique emails found")
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
            
            logging.info(f"Fetched {len(contacts)} detailed contacts (offset: {offset}). Total so far: {len(all_contacts)}")
            
            if len(contacts) < limit:
                break
                
            offset += limit
            
            time.sleep(0.1)
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching detailed contacts at offset {offset}: {str(e)}")
            break
        except Exception as e:
            logging.error(f"Unexpected error fetching detailed contacts at offset {offset}: {str(e)}")
            break
    
    logging.info(f"Finished fetching detailed contacts. Total: {len(all_contacts)} contacts found")
    return all_contacts


def add_contact(email: str, existing_contacts: set, list_ids=None, contact_data=None):
    if not API_KEY:
        logging.error("BREVO_API_KEY is not configured in environment variables")
        return MockResponse(500, "BREVO_API_KEY not configured")

    logging.info(f"users list: {len(existing_contacts)} contacts found")
    contact_exists = email in existing_contacts
    if contact_exists:
        logging.info(f"[-] {email} already exists. Will update with new data if provided.")

    payload = build_payload(email, list_ids, contact_data)
    return send_contact_payload(email, payload, contact_exists)

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
        logging.info("No attributes to add - contact_data was empty or had no valid fields")

    if list_ids:
        payload["listIds"] = list_ids
    elif CAMPAIGN_LIST_ID:
        payload["listIds"] = [CAMPAIGN_LIST_ID]

    return payload

def build_attributes(contact_data: dict | None) -> dict:
    if not contact_data:
        return {}

    attributes = {}
    field_mapping = {
        "vendor_name": "COMPANY_NAME",
        "company_id": "COMPANY_ID",
        "phone": "SMS",
        "tender_code": "TENDER_CODE"
    }

    for key, value in contact_data.items():
        if value and key in field_mapping:
            if key == "phone":
                phone = normalize_georgian_phone(value)
                if phone:
                    attributes[field_mapping[key]] = phone
            else:
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
            logging.warning(f"Failed to add/update contact {email}: {response.status_code} {response.text}")
        else:
            action = "Updated" if contact_exists else "Added"
            logging.info(f"{action} contact {email} with additional data")

        return response

    except Exception as e:
        logging.error(f"Exception occurred while contacting Brevo API for {email}: {str(e)}")
        return MockResponse(500, f"API Exception: {str(e)}")

def is_duplicate_sms_error(response: requests.Response) -> bool:
    return response.status_code == 400 and "SMS is already associated with another Contact" in response.text

def retry_without_sms(email: str, payload: dict):
    logging.warning(f"SMS already exists for another contact. Retrying {email} without SMS field...")

    attributes = payload.get("attributes", {})
    payload_without_sms = payload.copy()
    payload_without_sms["attributes"] = {k: v for k, v in attributes.items() if k != "SMS"}

    if payload_without_sms["attributes"]:
        logging.info(f"Retrying with payload: {payload_without_sms}")
        retry_response = requests.post("https://api.brevo.com/v3/contacts", json=payload_without_sms, headers=HEADERS)
        logging.info(f"Retry without SMS - Brevo API response: {retry_response.status_code} - {retry_response.text}")
        return retry_response
    else:
        logging.info(f"No other attributes to update for {email}, treating as success")
        return MockResponse(204, "No attributes to update after removing duplicate SMS")


def normalize_georgian_phone(phone: str) -> str | None:
    phone = str(phone).strip()

    if phone.startswith("+995"):
        national_part = phone[4:]
        if len(national_part) == 9 and national_part[0] == "5":
            return phone
        else:
            logging.warning(
                f"Invalid Georgian phone number format: {phone}. Expected +995 followed by 9 digits starting with 5"
            )
            return None

    elif phone.startswith("995"):
        national_part = phone[3:]
        if len(national_part) == 9 and national_part[0] == "5":
            return "+" + phone
        else:
            logging.warning(
                f"Invalid Georgian phone number format: {phone}. Expected 995 followed by 9 digits starting with 5"
            )
            return None

    elif phone.startswith("5") and len(phone) == 9:
        return "+995" + phone

    elif phone.startswith("0") and len(phone) == 10:
        return "+995" + phone[1:]

    elif phone.startswith("+"):
        return phone  # Trust it for now

    else:
        logging.warning(
            f"Unrecognized phone number format: {phone}. Unable to format for Georgian standards"
        )
        return None

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
        "recipients": {"listIds": [list_id]}
    }

    try:
        response = requests.post(url, json=payload, headers=HEADERS)
        
        if response.status_code in (201, 202):
            campaign_data = response.json()
            logging.info(f"Campaign '{campaign_name}' created successfully with ID: {campaign_data.get('id')}")
            return {
                "success": True,
                "campaign_id": campaign_data.get("id"),
                "campaign_name": campaign_name,
                "status_code": response.status_code
            }
        else:
            logging.warning(f"Failed to create campaign: {response.status_code} {response.text}")
            return {
                "success": False,
                "error": f"API Error: {response.status_code} - {response.text}",
                "status_code": response.status_code
            }
    except Exception as e:
        logging.error(f"Exception occurred while creating campaign: {str(e)}")
        return {
            "success": False,
            "error": f"Exception: {str(e)}",
            "status_code": None
        }


def send_campaign_to_contacts(campaign_id: int) -> dict:
    url = f"https://api.brevo.com/v3/emailCampaigns/{campaign_id}/sendNow"
    
    try:
        response = requests.post(url, headers=HEADERS)
        
        if response.status_code in (200, 202, 204):
            logging.info(f"Campaign {campaign_id} sent successfully")
            return {
                "success": True,
                "message": f"Campaign {campaign_id} sent to all contacts",
                "status_code": response.status_code
            }
        else:
            logging.warning(f"Failed to send campaign {campaign_id}: {response.status_code} {response.text}")
            return {
                "success": False,
                "error": f"Send failed: {response.status_code} - {response.text}",
                "status_code": response.status_code
            }
    except Exception as e:
        logging.error(f"Exception occurred while sending campaign {campaign_id}: {str(e)}")
        return {
            "success": False,
            "error": f"Exception: {str(e)}",
            "status_code": None
        }


def send_info_email_campaign():
    url = "https://api.brevo.com/v3/emailCampaigns"

    html_content = load_html_template("message_template.html")

    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "name": "Business Partnership Opportunity",
        "subject": "დოკუმენტაციის თარგმნა ნოტარიულად დამოწმებით",
        "htmlContent": f"{html_content}",
        "recipients": {"listIds": [CAMPAIGN_LIST_ID]}
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

def extract_email(row: dict) -> str:
    email = row.get("email") or row.get("Email") or row.get("EMAIL", "")
    return email.strip().lower() if email else ""

def extract_contact_data(row: dict) -> dict:
    csv_field_mapping = {
        "VendorName": "vendor_name",
        "IdCode": "company_id",
        "Phone": "phone",
        "CATEGORY": "tender_code"
    }
    contact_data = {}
    for csv_col, field_name in csv_field_mapping.items():
        value = row.get(csv_col, "").strip()
        if value and value not in ("", "http://"):
            contact_data[field_name] = value
    return contact_data

def process_contact(email: str, contact_data: dict, existing_emails: set, results: dict, campaign_list_id: int):
    if email in existing_emails:
        update_existing_contact(email, contact_data, results, existing_emails)
    else:
        create_new_contact_for_campaign(email, contact_data, existing_emails, results, campaign_list_id)


def update_existing_contact(email: str, contact_data: dict, results: dict, existing_emails: set):
    detailed_contacts = get_detailed_contacts()
    existing = next((c for c in detailed_contacts if c["email"].lower() == email), None)

    if existing:
        old_code = existing.get("attributes", {}).get("CATEGORY", "")
        new_code = contact_data.get("vendor_code", "")
        if new_code and old_code and new_code != old_code:
            contact_data["vendor_code"] = f"{new_code};{old_code}"
            logging.info(f"Updated vendor_code for {email}: {contact_data['vendor_code']}")

    resp = add_contact(email, existing_emails, contact_data=contact_data)
    if resp and resp.status_code in (201, 204):
        results["updated_contacts"].append({"email": email, "data": contact_data})
        logging.info(f"Existing contact {email} updated but not added to campaign")
    else:
        results["errors"].append({
            "email": email, 
            "error": f"Failed to update contact: {resp.text if resp else 'No response'}"
        })


def create_new_contact_for_campaign(email: str, contact_data: dict, existing_emails: set, results: dict, campaign_list_id: int):
    resp = add_contact(email, existing_emails, list_ids=[campaign_list_id], contact_data=contact_data)
    if resp and resp.status_code in (201, 204):
        action = "updated" if resp.status_code == 204 else "created"
        results["added_to_campaign"].append({"email": email, "data": contact_data, "action": action})
        existing_emails.add(email)
        logging.info(f"New contact {email} {action} and added to campaign list {campaign_list_id}")
    else:
        results["errors"].append({"email": email, "error": (resp.text if resp else "No response")})


def handle_csv(file_bytes: bytes):
    decoded = file_bytes.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    
    logging.info("Fetching all existing contacts from Brevo...")
    
    existing_contacts_email = get_existing_contacts_email()
    
    logging.info(f"Found {len(existing_contacts_email)} existing contacts in your Brevo account")
    
    results = {
        "added_to_campaign": [], 
        "updated_contacts": [], 
        "errors": [],
        "campaign_info": {},
        "total_existing_contacts": len(existing_contacts_email) 
    }

    logging.info("Creating new campaign for CSV import...")
    
    campaign_result = create_new_campaign(CAMPAIGN_LIST_ID)
    
    results["campaign_info"] = campaign_result
    
    if not campaign_result["success"]:
        logging.error("Failed to create campaign. Aborting CSV processing.")
        results["errors"].append({"error": "Failed to create campaign", "details": campaign_result["error"]})
        return results

    campaign_id = campaign_result["campaign_id"]
    
    logging.info(f"Campaign created with ID: {campaign_id}")

    for row in reader:
        email = extract_email(row)
        if not email:
            continue

        contact_data = extract_contact_data(row)

        try:
            process_contact(email, contact_data, existing_contacts_email, results, CAMPAIGN_LIST_ID)
        except Exception as e:
            results["errors"].append({"email": email, "error": str(e)})

        logging.info(f"Sending campaign to {len(results['added_to_campaign'])} new contacts...")
        time.sleep(2)
        send_result = send_campaign_to_contacts(campaign_id)
        results["campaign_info"]["send_result"] = send_result
        
        if send_result["success"]:
            logging.info("Campaign sent successfully to all new contacts!")
        else:
            logging.error(f"Failed to send campaign: {send_result['error']}")
    else:
        logging.info("No new contacts were added, so campaign was not sent.")
        results["campaign_info"]["send_result"] = {"success": False, "message": "No new contacts to send to"}

    return results


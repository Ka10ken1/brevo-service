import csv
import requests
import logging
import io
import os
from dotenv import load_dotenv


load_dotenv()

SENDER_NAME = os.getenv("SENDER_NAME")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
CAMPAIGN_LIST_ID = int(os.getenv("CAMPAIGN_LIST_ID", "1"))

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


def get_detailed_contacts():
    """Get detailed contact information from Brevo"""
    url = "https://api.brevo.com/v3/contacts"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    logging.info("Fetched detailed contacts from Brevo API.")

    contacts = []
    for contact in data.get("contacts", []):
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
        contacts.append(contact_info)

    return contacts


def add_contact(email: str, existing_contacts: set, list_ids=None, contact_data=None):

    logging.info(f"users list: {len(existing_contacts)} contacts found")

    contact_exists = email in existing_contacts
    if contact_exists:
        logging.info(
            f"[-] {email} already exists. Will update with new data if provided."
        )

    url = "https://api.brevo.com/v3/contacts"

    payload = {
        "email": email,
        "updateEnabled": True,  # Update if contact already exists
    }

    if contact_data:
        attributes = {}
        field_mapping = {
            "nat": "NAT",
            "stop": "STOP",
            "contact_id": "COMPANY_ID",
            "contacts": "CONTACTS",
            "website": "WEBSITE",
            "vendor_name": "COMPANY_NAME",
            "address": "ADDRESS",
            "id_code": "COMPANY_ID",
            "phone": "SMS",
            "fax": "FAX",
            "city": "CITY",
            "country": "COUNTRY",
            "tender_code": "TENDER_CODE",
        }

        for key, value in contact_data.items():
            if value and key in field_mapping:
                if key == "phone" and value:
                    phone = str(value).strip()

                    if phone.startswith("+995"):
                        national_part = phone[4:]
                        if len(national_part) == 9 and national_part[0] == "5":
                            phone = phone
                        else:
                            logging.warning(
                                f"Invalid Georgian phone number format: {phone}. Expected +995 followed by 9 digits starting with 5"
                            )
                            continue
                    elif phone.startswith("995"):
                        national_part = phone[3:]
                        if len(national_part) == 9 and national_part[0] == "5":
                            phone = "+" + phone
                        else:
                            logging.warning(
                                f"Invalid Georgian phone number format: {phone}. Expected 995 followed by 9 digits starting with 5"
                            )
                            continue
                    elif phone.startswith("5") and len(phone) == 9:
                        phone = "+995" + phone
                    elif phone.startswith("0") and len(phone) == 10:
                        phone = "+995" + phone[1:]
                    elif phone.startswith("+"):
                        pass
                    else:
                        logging.warning(
                            f"Unrecognized phone number format: {phone}. Unable to format for Georgian standards"
                        )
                        continue

                    attributes[field_mapping[key]] = phone
                else:
                    attributes[field_mapping[key]] = value

        if attributes:
            payload["attributes"] = attributes
            logging.info(f"Adding contact with attributes: {attributes}")
        else:
            logging.info(
                "No attributes to add - contact_data was empty or had no valid fields"
            )

    if list_ids:
        payload["listIds"] = list_ids
    elif CAMPAIGN_LIST_ID:
        payload["listIds"] = [CAMPAIGN_LIST_ID]

    logging.info(f"Sending payload to Brevo: {payload}")

    response: requests.Response = requests.post(url, json=payload, headers=HEADERS)

    logging.info(f"Brevo API response: {response.status_code} - {response.text}")

    if response.status_code not in (201, 204):
        logging.warning(
            f"Failed to add/update contact {email}: {response.status_code} {response.text}"
        )
    else:
        action = "Updated" if contact_exists else "Added"
        logging.info(f"{action} contact {email} with additional data")

    return response


def send_info_email_campaign():
    url = "https://api.brevo.com/v3/emailCampaigns"
    payload = {
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "name": "Business Partnership Opportunity",
        "subject": "თარგმნის სახლი - სპეციალური შეთავაზება სატენდერო დოკუმენტებისთვის",
        "htmlContent": """<!DOCTYPE html>
<html lang="ka">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>თარგმნის სახლი - სპეციალური შეთავაზება</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .email-container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        
        .header {
            background: linear-gradient(135deg, #24505a, #1e434c);
            padding: 20px;
            color: white;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
        }
        
        .logo {
            width: 120px;
            height: auto;
            background-color: rgba(255,255,255,0.1);
            padding: 5px;
            border-radius: 5px;
            flex-shrink: 0;
        }
        
        .header-content {
            text-align: center;
            flex: 1;
            margin-left: 20px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .content {
            padding: 40px 30px;
        }
        
        .special-offer {
            background: linear-gradient(135deg, #e8f2f4, #f0f6f7);
            border: 2px solid #24505a;
            padding: 30px;
            margin: 30px 0;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(36, 80, 90, 0.1);
        }
        
        .special-offer h2 {
            color: #24505a;
            font-size: 1.8em;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .offer-list {
            list-style: none;
            margin: 20px 0;
        }
        
        .offer-list li {
            padding: 8px 0;
            font-size: 0.85em;
            display: flex;
            align-items: center;
            line-height: 1.3;
        }
        
        .offer-list li strong {
            color: #038211;
        }
        
        .offer-list li::before {
            content: "✓";
            color: #24505a;
            font-weight: bold;
            font-size: 1.3em;
            margin-right: 10px;
        }
        
        .price-section {
            margin: 40px 0;
        }
        
        .price-section h2 {
            color: #24505a;
            font-size: 1.8em;
            text-align: center;
            margin-bottom: 30px;
        }
        
        .price-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .price-table-container {
            overflow-x: auto;
            margin: 20px 0;
        }
        
        .price-table th {
            background: linear-gradient(135deg, #24505a, #1e434c);
            color: white;
            padding: 15px 10px;
            text-align: center;
            font-weight: bold;
        }
        
        .price-table td {
            padding: 15px 10px;
            text-align: center;
            border-bottom: 1px solid #eee;
        }
        
        .price-table tr:hover {
            background-color: #f8f9fa;
        }
        
        .country-flag {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            font-size: 1.5em;
        }
        
        .flag {
            width: 30px;
            height: 20px;
            border-radius: 3px;
            display: inline-block;
        }
        
        .flag.uk {
            background: linear-gradient(to bottom, #012169 33%, white 33%, white 66%, #C8102E 66%);
            position: relative;
        }
        
        .flag.turkey {
            background: #E30A17;
            position: relative;
        }
        
        .flag.germany {
            background: linear-gradient(to bottom, #000 33%, #DD0000 33%, #DD0000 66%, #FFCE00 66%);
        }
        
        .flag.china {
            background: #DE2910;
        }
        
        .price {
            font-weight: bold;
            color: #24505a;
            font-size: 1.1em;
        }
        
        .why-choose {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            margin: 30px 0;
        }
        
        .why-choose h2 {
            color: #24505a;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .feature {
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .feature h3 {
            color: #24505a;
            margin-bottom: 10px;
        }
        
        .languages {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            margin: 30px 0;
        }
        
        .languages h2 {
            color: #24505a;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .language-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .language {
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
            color: #24505a;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .contact-section {
            background: linear-gradient(135deg, #24505a, #1e434c);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        
        .contact-section h2 {
            font-size: 2em;
            margin-bottom: 20px;
        }
        
        .contact-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 30px;
            margin: 30px 0;
        }
        
        .contact-person {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        
        .contact-person h3 {
            font-size: 1.3em;
            margin-bottom: 10px;
        }
        
        .footer {
            background: #333;
            color: white;
            text-align: center;
            padding: 30px;
        }

.btn {
    display: inline-block;
    background-color: #ffb400; /* Bright amber */
    color: #1e1e1e;
    padding: 14px 28px;
    font-size: 1.05em;
    font-weight: bold;
    border: none;
    border-radius: 10px;
    cursor: pointer;
    text-align: center;
    text-decoration: none;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    transition: background-color 0.3s ease, transform 0.2s ease;
}

.btn:hover {
    background-color: #e69f00;
    transform: translateY(-2px);
}

.btn:active {
    background-color: #cc8c00;
    transform: translateY(0);
}

.btn-secondary {
    background-color: #ffffff;
    color: #24505a;
    border: 2px solid #24505a;
}

.btn-secondary:hover {
    background-color: #f0f6f7;
    color: #1e434c;
}
        
        @media (max-width: 600px) {
            .email-container {
                margin: 0;
            }
            
            .header {
                flex-direction: column;
                text-align: center;
            }
            
            .header-content {
                margin-left: 0;
                margin-top: 15px;
            }
            
            .logo {
                width: 100px;
            }
            
            .content {
                padding: 20px 15px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .price-table {
                font-size: 0.8em;
                min-width: 600px;
            }
            
            .price-table th,
            .price-table td {
                padding: 8px 4px;
                white-space: nowrap;
            }
            
            .country-flag {
                font-size: 1.2em;
            }
        }
    </style>
</head>
<body>
    <div class="email-container">
        <!-- Header -->
        <div class="header">
              <img src="https://th.com.ge/assets/images/logo.jpg" alt="თარგმნის სახლი" class="logo">
            <div class="header-content">
                <h1>თარგმნის სახლი</h1>
                <p>სატენდერო დოკუმენტების თარგმნა და ნოტარიული დამოწმება</p>
            </div>
        </div>

        <!-- Content -->
        <div class="content">
            <p style="font-size: 1.1em; margin-bottom: 30px;">თუ თქვენი კომპანია <strong>სახელმწიფო შესყიდვებში მონაწილეობს</strong>, გთავაზობთ სპეციალურ პირობებს დოკუმენტაციის თარგმნისთვის.</p>

            <!-- Special Offer -->
            <div class="special-offer">
                <h2>სპეციალური შეთავაზება თქვენთვის:</h2>
                
                <ul class="offer-list">
                    <li><strong>15%-იანი ფასდაკლება</strong>&nbsp; ნოტარიულად დამოწმებულ პირველ თარგმანზე</li>
                    <li><strong>შესრულების დაჩქარებული ვადები</strong>&nbsp; - დროული მიწოდება გარანტირებულია</li>
                    <li><strong>პერსონალური მენეჯერი</strong>&nbsp; თქვენი პროექტისთვის</li>
                </ul>
            </div>

            <!-- Price List -->
            <div class="price-section">
                <h2>ფასთა ცხრილი</h2>
                <div class="price-table-container">
                    <table class="price-table">
                    <thead>
                        <tr>
                            <th rowspan="2">ენა</th>
                            <th>თარგმნა</th>
                            <th colspan="4">თარგმნა + დამოწმება</th>
                        </tr>
                        <tr>
                            <th>1 გვერდი</th>
                            <th>1 გვერდი</th>
                            <th>2-10 გვერდი</th>
                            <th>10-50 გვერდი</th>
                            <th>50+ გვერდი</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="country-flag">
                                🇬🇧
                            </td>
                            <td class="price">20₾</td>
                            <td class="price">27₾</td>
                            <td class="price">25₾</td>
                            <td class="price">24₾</td>
                            <td class="price">22₾</td>
                        </tr>
                        <tr>
                            <td class="country-flag">
                                🇹🇷
                            </td>
                            <td class="price">25₾</td>
                            <td class="price">32₾</td>
                            <td class="price">30₾</td>
                            <td class="price">29₾</td>
                            <td class="price">27₾</td>
                        </tr>
                        <tr>
                            <td class="country-flag">
                                🇩🇪
                            </td>
                            <td class="price">25₾</td>
                            <td class="price">32₾</td>
                            <td class="price">30₾</td>
                            <td class="price">29₾</td>
                            <td class="price">27₾</td>
                        </tr>
                        <tr>
                            <td class="country-flag">
                                🇨🇳
                            </td>
                            <td class="price">68₾</td>
                            <td class="price">75₾</td>
                            <td class="price">73₾</td>
                            <td class="price">72₾</td>
                            <td class="price">70₾</td>
                        </tr>
                    </tbody>
                </table>
                </div>
                
                <p style="margin-top: 15px; font-size: 0.9em; color: #666; text-align: center; font-style: italic;">
                    * თითო დოკუმენტის დამოწმებას ემატება 5₾ ნოტარიუსთან აკინძვის ღირებულება
                </p>
            </div>

            <!-- Why Choose Us -->
            <div class="why-choose">
                <h2>რატომ უნდა აირჩიოთ "თარგმნის სახლი"?</h2>
                <div class="features">
                    <div class="feature">
                        <h3>სერტიფიცირებული თარჯიმნები</h3>
                        <p>მხოლოდ კვალიფიციური და გამოცდილი სპეციალისტები</p>
                    </div>
                    <div class="feature">
                        <h3>ნოტარიული დამოწმება</h3>
                        <p>სრული იურიდიული ღირებულება</p>
                    </div>
                    <div class="feature">
                        <h3>სწრაფი შესრულება</h3>
                        <p>დროული მიწოდება გარანტირებულია</p>
                    </div>
                    <div class="feature">
                        <h3>კონკურენტული ფასები</h3>
                        <p>საუკეთესო თანაფარდობა ფასი/ხარისხი</p>
                    </div>
                </div>
            </div>

            <!-- Languages -->
            <div class="languages">
                <h2>ენები, რომლებზეც ვთარგმნით</h2>
                <p>ჩვენ გთავაზობთ პროფესიონალურ თარგმანს შემდეგ ენებზე:</p>
                <div class="language-grid">
                    <div class="language">🇬🇧 ინგლისური</div>
                    <div class="language">🇷🇺 რუსული</div>
                    <div class="language">🇩🇪 გერმანული</div>
                    <div class="language">🇫🇷 ფრანგული</div>
                    <div class="language">🇨🇳 ჩინური</div>
                    <div class="language">🇹🇷 თურქული</div>
                    <div class="language">🇺🇦 უკრაინული</div>
                    <div class="language">🌍 და სხვა</div>
                </div>
            </div>
        </div>

        <!-- Contact Section -->
        <div class="contact-section">
            <h2>მოგვწერეთ ახლავე</h2>
            <p>დაგვიკავშირდით დღესვე:</p>
            
            <div class="contact-info">
                <div class="contact-person">
                    <h3>თამარი</h3>
                    <p>📞 +995 568 42 05 53</p>
                    <a href="https://iuristi.ge/translation/tako.vcf" download="tako.vcf" class="btn">📥 ნომრის ჩანიშვნა</a>
                </div>
            </div>
            
            <p>📧 info@th.com.ge</p>
            <p style="margin-top: 20px; font-size: 1.2em;"><strong>გისურვებთ წარმატებას სატენდერო პროცესში!</strong></p>
        </div>

        <!-- Footer -->
        <div class="footer">
            <h3>თარგმნის სახლი</h3>
            <p>მისამართი: თბილისი, ც. დადიანის 7 (ქარვასლა)</p>
            <p>© 2025 თარგმნის სახლი - ყველა უფლება დაცულია</p>
        </div>
    </div>
</body>
</html>""",
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
    if not SENDER_EMAIL:
        logging.error("SENDER_EMAIL not configured in environment variables")
        raise ValueError("SENDER_EMAIL is required for sending emails")

    url = "https://api.brevo.com/v3/smtp/email"
    payload = {
        "to": [{"email": email}],
        "subject": "თარგმნის სახლი - სპეციალური შეთავაზება სატენდერო დოკუმენტებისთვის",
        "htmlContent": """<!DOCTYPE html>
<html lang="ka">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>თარგმნის სახლი - სპეციალური შეთავაზება</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .email-container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        
        .header {
            background: linear-gradient(135deg, #24505a, #1e434c);
            padding: 20px;
            color: white;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
        }
        
        .logo {
            width: 120px;
            height: auto;
            background-color: rgba(255,255,255,0.1);
            padding: 5px;
            border-radius: 5px;
            flex-shrink: 0;
        }
        
        .header-content {
            text-align: center;
            flex: 1;
            margin-left: 20px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .content {
            padding: 40px 30px;
        }
        
        .special-offer {
            background: linear-gradient(135deg, #e8f2f4, #f0f6f7);
            border: 2px solid #24505a;
            padding: 30px;
            margin: 30px 0;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(36, 80, 90, 0.1);
        }
        
        .special-offer h2 {
            color: #24505a;
            font-size: 1.8em;
            margin-bottom: 20px;
            text-align: center;
        }
        
        .offer-list {
            list-style: none;
            margin: 20px 0;
        }
        
        .offer-list li {
            padding: 8px 0;
            font-size: 0.85em;
            display: flex;
            align-items: center;
            line-height: 1.3;
        }
        
        .offer-list li strong {
            color: #038211;
        }
        
        .offer-list li::before {
            content: "✓";
            color: #24505a;
            font-weight: bold;
            font-size: 1.3em;
            margin-right: 10px;
        }
        
        .price-section {
            margin: 40px 0;
        }
        
        .price-section h2 {
            color: #24505a;
            font-size: 1.8em;
            text-align: center;
            margin-bottom: 30px;
        }
        
        .price-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .price-table-container {
            overflow-x: auto;
            margin: 20px 0;
        }
        
        .price-table th {
            background: linear-gradient(135deg, #24505a, #1e434c);
            color: white;
            padding: 15px 10px;
            text-align: center;
            font-weight: bold;
        }
        
        .price-table td {
            padding: 15px 10px;
            text-align: center;
            border-bottom: 1px solid #eee;
        }
        
        .price-table tr:hover {
            background-color: #f8f9fa;
        }
        
        .country-flag {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            font-size: 1.5em;
        }
        
        .flag {
            width: 30px;
            height: 20px;
            border-radius: 3px;
            display: inline-block;
        }
        
        .flag.uk {
            background: linear-gradient(to bottom, #012169 33%, white 33%, white 66%, #C8102E 66%);
            position: relative;
        }
        
        .flag.turkey {
            background: #E30A17;
            position: relative;
        }
        
        .flag.germany {
            background: linear-gradient(to bottom, #000 33%, #DD0000 33%, #DD0000 66%, #FFCE00 66%);
        }
        
        .flag.china {
            background: #DE2910;
        }
        
        .price {
            font-weight: bold;
            color: #24505a;
            font-size: 1.1em;
        }
        
        .why-choose {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            margin: 30px 0;
        }
        
        .why-choose h2 {
            color: #24505a;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .feature {
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .feature h3 {
            color: #24505a;
            margin-bottom: 10px;
        }
        
        .languages {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 10px;
            margin: 30px 0;
        }
        
        .languages h2 {
            color: #24505a;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .language-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .language {
            background: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
            color: #24505a;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .contact-section {
            background: linear-gradient(135deg, #24505a, #1e434c);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        
        .contact-section h2 {
            font-size: 2em;
            margin-bottom: 20px;
        }
        
        .contact-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 30px;
            margin: 30px 0;
        }
        
        .contact-person {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        
        .contact-person h3 {
            font-size: 1.3em;
            margin-bottom: 10px;
        }
        
        .footer {
            background: #333;
            color: white;
            text-align: center;
            padding: 30px;
        }

.btn {
    display: inline-block;
    background-color: #ffb400; /* Bright amber */
    color: #1e1e1e;
    padding: 14px 28px;
    font-size: 1.05em;
    font-weight: bold;
    border: none;
    border-radius: 10px;
    cursor: pointer;
    text-align: center;
    text-decoration: none;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
    transition: background-color 0.3s ease, transform 0.2s ease;
}

.btn:hover {
    background-color: #e69f00;
    transform: translateY(-2px);
}

.btn:active {
    background-color: #cc8c00;
    transform: translateY(0);
}

.btn-secondary {
    background-color: #ffffff;
    color: #24505a;
    border: 2px solid #24505a;
}

.btn-secondary:hover {
    background-color: #f0f6f7;
    color: #1e434c;
}
        
        @media (max-width: 600px) {
            .email-container {
                margin: 0;
            }
            
            .header {
                flex-direction: column;
                text-align: center;
            }
            
            .header-content {
                margin-left: 0;
                margin-top: 15px;
            }
            
            .logo {
                width: 100px;
            }
            
            .content {
                padding: 20px 15px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .price-table {
                font-size: 0.8em;
                min-width: 600px;
            }
            
            .price-table th,
            .price-table td {
                padding: 8px 4px;
                white-space: nowrap;
            }
            
            .country-flag {
                font-size: 1.2em;
            }
        }
    </style>
</head>
<body>
    <div class="email-container">
        <!-- Header -->
        <div class="header">
              <img src="https://th.com.ge/assets/images/logo.jpg" alt="თარგმნის სახლი" class="logo">
            <div class="header-content">
                <h1>თარგმნის სახლი</h1>
                <p>სატენდერო დოკუმენტების თარგმნა და ნოტარიული დამოწმება</p>
            </div>
        </div>

        <!-- Content -->
        <div class="content">
            <p style="font-size: 1.1em; margin-bottom: 30px;">თუ თქვენი კომპანია <strong>სახელმწიფო შესყიდვებში მონაწილეობს</strong>, გთავაზობთ სპეციალურ პირობებს დოკუმენტაციის თარგმნისთვის.</p>

            <!-- Special Offer -->
            <div class="special-offer">
                <h2>სპეციალური შეთავაზება თქვენთვის:</h2>
                
                <ul class="offer-list">
                    <li><strong>15%-იანი ფასდაკლება</strong>&nbsp; ნოტარიულად დამოწმებულ პირველ თარგმანზე</li>
                    <li><strong>შესრულების დაჩქარებული ვადები</strong>&nbsp; - დროული მიწოდება გარანტირებულია</li>
                    <li><strong>პერსონალური მენეჯერი</strong>&nbsp; თქვენი პროექტისთვის</li>
                </ul>
            </div>

            <!-- Price List -->
            <div class="price-section">
                <h2>ფასთა ცხრილი</h2>
                <div class="price-table-container">
                    <table class="price-table">
                    <thead>
                        <tr>
                            <th rowspan="2">ენა</th>
                            <th>თარგმნა</th>
                            <th colspan="4">თარგმნა + დამოწმება</th>
                        </tr>
                        <tr>
                            <th>1 გვერდი</th>
                            <th>1 გვერდი</th>
                            <th>2-10 გვერდი</th>
                            <th>10-50 გვერდი</th>
                            <th>50+ გვერდი</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td class="country-flag">
                                🇬🇧
                            </td>
                            <td class="price">20₾</td>
                            <td class="price">27₾</td>
                            <td class="price">25₾</td>
                            <td class="price">24₾</td>
                            <td class="price">22₾</td>
                        </tr>
                        <tr>
                            <td class="country-flag">
                                🇹🇷
                            </td>
                            <td class="price">25₾</td>
                            <td class="price">32₾</td>
                            <td class="price">30₾</td>
                            <td class="price">29₾</td>
                            <td class="price">27₾</td>
                        </tr>
                        <tr>
                            <td class="country-flag">
                                🇩🇪
                            </td>
                            <td class="price">25₾</td>
                            <td class="price">32₾</td>
                            <td class="price">30₾</td>
                            <td class="price">29₾</td>
                            <td class="price">27₾</td>
                        </tr>
                        <tr>
                            <td class="country-flag">
                                🇨🇳
                            </td>
                            <td class="price">68₾</td>
                            <td class="price">75₾</td>
                            <td class="price">73₾</td>
                            <td class="price">72₾</td>
                            <td class="price">70₾</td>
                        </tr>
                    </tbody>
                </table>
                </div>
                
                <p style="margin-top: 15px; font-size: 0.9em; color: #666; text-align: center; font-style: italic;">
                    * თითო დოკუმენტის დამოწმებას ემატება 5₾ ნოტარიუსთან აკინძვის ღირებულება
                </p>
            </div>

            <!-- Why Choose Us -->
            <div class="why-choose">
                <h2>რატომ უნდა აირჩიოთ "თარგმნის სახლი"?</h2>
                <div class="features">
                    <div class="feature">
                        <h3>სერტიფიცირებული თარჯიმნები</h3>
                        <p>მხოლოდ კვალიფიციური და გამოცდილი სპეციალისტები</p>
                    </div>
                    <div class="feature">
                        <h3>ნოტარიული დამოწმება</h3>
                        <p>სრული იურიდიული ღირებულება</p>
                    </div>
                    <div class="feature">
                        <h3>სწრაფი შესრულება</h3>
                        <p>დროული მიწოდება გარანტირებულია</p>
                    </div>
                    <div class="feature">
                        <h3>კონკურენტული ფასები</h3>
                        <p>საუკეთესო თანაფარდობა ფასი/ხარისხი</p>
                    </div>
                </div>
            </div>

            <!-- Languages -->
            <div class="languages">
                <h2>ენები, რომლებზეც ვთარგმნით</h2>
                <p>ჩვენ გთავაზობთ პროფესიონალურ თარგმანს შემდეგ ენებზე:</p>
                <div class="language-grid">
                    <div class="language">🇬🇧 ინგლისური</div>
                    <div class="language">🇷🇺 რუსული</div>
                    <div class="language">🇩🇪 გერმანული</div>
                    <div class="language">🇫🇷 ფრანგული</div>
                    <div class="language">🇨🇳 ჩინური</div>
                    <div class="language">🇹🇷 თურქული</div>
                    <div class="language">🇺🇦 უკრაინული</div>
                    <div class="language">🌍 და სხვა</div>
                </div>
            </div>
        </div>

        <!-- Contact Section -->
        <div class="contact-section">
            <h2>მოგვწერეთ ახლავე</h2>
            <p>დაგვიკავშირდით დღესვე:</p>
            
            <div class="contact-info">
                <div class="contact-person">
                    <h3>თამარი</h3>
                    <p>📞 +995 568 42 05 53</p>
                    <a href="https://iuristi.ge/translation/tako.vcf" download="tako.vcf" class="btn">📥 ნომრის ჩანიშვნა</a>
                </div>
            </div>
            
            <p>📧 info@th.com.ge</p>
            <p style="margin-top: 20px; font-size: 1.2em;"><strong>გისურვებთ წარმატებას სატენდერო პროცესში!</strong></p>
        </div>

        <!-- Footer -->
        <div class="footer">
            <h3>თარგმნის სახლი</h3>
            <p>მისამართი: თბილისი, ც. დადიანის 7 (ქარვასლა)</p>
            <p>© 2025 თარგმნის სახლი - ყველა უფლება დაცულია</p>
        </div>
    </div>
</body>
</html>""",
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


def handle_csv(file_bytes: bytes):
    decoded = file_bytes.decode("utf-8")

    reader = csv.DictReader(io.StringIO(decoded))

    existing_contacts = get_existing_contacts()
    results = {"added_contacts": [], "info_sent": [], "errors": []}

    for row in reader:
        # Try to get email from different possible column names
        email = row.get("email") or row.get("Email") or row.get("EMAIL", "")
        email = email.strip().lower() if email else ""
        if not email:
            continue

        # Extract all additional contact data from CSV
        contact_data = {}

        # Map CSV column names to our internal field names
        csv_field_mapping = {
            "NAT": "nat",
            "STOP": "stop",
            "ID": "contact_id",
            "Contacts": "contacts",
            "Website": "website",
            "VendorName": "vendor_name",
            "Address": "address",
            "IdCode": "id_code",
            "Phone": "phone",
            "Fax": "fax",
            "City": "city",
            "Country": "country",
        }

        for csv_col, field_name in csv_field_mapping.items():
            value = row.get(csv_col, "").strip()
            if value and value not in ("", "http://"):
                contact_data[field_name] = value

        try:
            if email in existing_contacts:
                resp = send_info_email(email)
                if resp.status_code in (200, 201, 202):
                    results["info_sent"].append({"email": email, "data": contact_data})
                else:
                    results["errors"].append({"email": email, "error": resp.text})
            else:
                resp = add_contact(email, existing_contacts, contact_data=contact_data)
                if resp and resp.status_code in (201, 204):
                    if resp.status_code == 204:
                        results["added_contacts"].append(
                            {"email": email, "data": contact_data, "action": "updated"}
                        )
                    else:
                        results["added_contacts"].append(
                            {"email": email, "data": contact_data, "action": "created"}
                        )
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

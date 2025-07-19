# Brevo Flow

---
### Get Started
```shell
uvicorn brevo.main:app --reload
```
--- 
### Single Contact Addition (`POST /add_contact`)
Client sends: {"email": "user@example.com"}
↓
1. FastAPI receives request at /add_contact endpoint
2. Validates email format using Pydantic EmailStr
3. Calls get_existing_contacts():
   - Makes GET request to Brevo API: /v3/contacts
   - Returns set of existing contact emails
4. Calls add_contact():
   - Checks if email already exists in contacts
   - If exists: logs and returns early
   - If new: makes POST to /v3/contacts with payload:
     {
       "email": "user@example.com",
       "updateEnabled": true,
       "listIds": [1]  // CAMPAIGN_LIST_ID
     }
5. Returns: {"status": "contact_added", "email": "user@example.com"}

---

### Send Info Email (`POST /send-info`)
Client sends: {"email": "user@example.com"}
↓
1. FastAPI receives request at /send-info endpoint
2. Calls send_info_email():
   - Makes POST to /v3/smtp/email with payload:
     {
       "to": [{"email": "user@example.com"}],
       "subject": "Here's what you need to know",
       "htmlContent": "<p>Dear user, here is the information...</p>",
       "sender": {"name": "Brevo Bot", "email": "your@email.com"}
     }
3. Returns: {"status": "sent", "email": "user@example.com"}

---
## CSV Processing (`POST /process-csv`)

Client uploads CSV file:
1. FastAPI receives file upload
2. Reads file bytes: await file.read()
3. Calls handle_csv():
   
   a) Decode bytes to UTF-8 (handles Georgian characters)
   b) Create CSV reader from decoded string
   c) Get existing contacts from Brevo API
   d) Initialize results: {"added_contacts": [], "info_sent": [], "errors": []}
   
   e) For each row in CSV:
      - Extract email: row.get("email") or row.get("Email", "")
      - Clean and lowercase email
      - Skip if email is empty
      
      f) Decision logic:
         If email in existing_contacts:
           → Send info email via /v3/smtp/email
           → Add to "info_sent" list
         
         If email NOT in existing_contacts:
           → Add contact via /v3/contacts
           → Add to existing_contacts set (prevent duplicates)
           → Add to "added_contacts" list
      
      g) Handle errors: catch exceptions and add to "errors" list

4. Return complete results:
   {
     "added_contacts": ["new1@example.com", "new2@example.com"],
     "info_sent": ["existing@example.com"],
     "errors": [{"email": "invalid", "error": "reason"}]
   }

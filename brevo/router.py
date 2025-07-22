from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, EmailStr
from pathlib import Path
from typing import Optional, Union
import re
from datetime import datetime
from .brevo_service import (
    add_contact,
    send_info_email,
    get_existing_contacts_email,
    get_detailed_contacts,
    handle_csv,
)

router = APIRouter()


class UserEmail(BaseModel):
    email: EmailStr


class ContactInfo(BaseModel):
    email: EmailStr
    nat: Union[str, None] = None
    stop: Union[str, None] = None
    contact_id: Union[str, None] = None
    contacts: Union[str, None] = None
    website: Union[str, None] = None
    vendor_name: Union[str, None] = None
    address: Union[str, None] = None
    id_code: Union[str, None] = None
    phone: Union[str, None] = None
    fax: Union[str, None] = None
    city: Union[str, None] = None
    country: Union[str, None] = None
    tender_code: Union[str, None] = None


@router.post("/add_contact")
async def add_contact_endpoint(data: ContactInfo):
    existing_contacts = get_existing_contacts_email()

    # excluding None values
    contact_data = {}
    if data.nat:
        contact_data["nat"] = data.nat
    if data.stop:
        contact_data["stop"] = data.stop
    if data.contact_id:
        contact_data["contact_id"] = data.contact_id
    if data.contacts:
        contact_data["contacts"] = data.contacts
    if data.website:
        contact_data["website"] = data.website
    if data.vendor_name:
        contact_data["vendor_name"] = data.vendor_name
    if data.address:
        contact_data["address"] = data.address
    if data.id_code:
        contact_data["id_code"] = data.id_code
    if data.phone:
        contact_data["phone"] = data.phone
    if data.fax:
        contact_data["fax"] = data.fax
    if data.city:
        contact_data["city"] = data.city
    if data.country:
        contact_data["country"] = data.country
    if data.tender_code:
        contact_data["tender_code"] = data.tender_code

    response = add_contact(data.email, existing_contacts, contact_data=contact_data)
    if response.status_code not in (201, 204):
        raise HTTPException(status_code=response.status_code, detail=response.text)

    # Check if this was an update vs new contact
    if response.status_code == 204:
        return {
            "status": "contact_updated",
            "email": data.email,
            "message": "Contact was updated with new data",
            "data": contact_data,
        }
    else:
        return {"status": "contact_added", "email": data.email, "data": contact_data}


@router.post("/send-info")
async def send_info(data: UserEmail):
    response = send_info_email(data.email)
    if response.status_code not in (200, 201):
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return {"status": "sent", "email": data.email}


@router.post("/process-csv")
async def process_csv_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    results = handle_csv(contents)
    return results


@router.get("/users")
async def get_all_users(detailed: bool = False):
    try:
        if detailed:
            contacts = get_detailed_contacts()
            return {"total_contacts": len(contacts), "contacts": contacts}
        else:
            existing_contacts = get_existing_contacts()
            return {
                "total_contacts": len(existing_contacts),
                "contacts": sorted(list(existing_contacts)),
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch contacts: {str(e)}"
        )


@router.get("/logs")
async def get_logs(limit: int = 50):
    log_files = ["api_service.log", "background_service.log", "brevo_service.log"]

    all_logs = []

    for log_file in log_files:
        log_path = Path(log_file)
        if log_path.exists():
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                recent_lines = lines[-100:] if len(lines) > 100 else lines

                for line in recent_lines:
                    line = line.strip()
                    if not line:
                        continue

                    match = re.match(
                        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (.+)", line
                    )
                    if match:
                        timestamp_str, level, message = match.groups()
                        try:
                            datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                            all_logs.append(
                                {
                                    "timestamp": timestamp_str,
                                    "level": level,
                                    "message": message,
                                    "source": log_file,
                                }
                            )
                        except ValueError:
                            all_logs.append(
                                {
                                    "timestamp": timestamp_str,
                                    "level": level,
                                    "message": message,
                                    "source": log_file,
                                }
                            )
                    else:
                        all_logs.append(
                            {
                                "timestamp": datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "level": "INFO",
                                "message": line,
                                "source": log_file,
                            }
                        )
            except Exception as e:
                all_logs.append(
                    {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "level": "ERROR",
                        "message": f"Error reading {log_file}: {str(e)}",
                        "source": "system",
                    }
                )

    all_logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"logs": all_logs[:limit]}

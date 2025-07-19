from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, EmailStr
from .brevo_service import (
    add_contact,
    send_info_email,
    get_existing_contacts,
    handle_csv,
)

router = APIRouter()


class UserEmail(BaseModel):
    email: EmailStr


@router.post("/add_contact")
async def add_contact_endpoint(data: UserEmail):
    existing_contacts = get_existing_contacts()
    response = add_contact(data.email, existing_contacts)
    if response.status_code not in (201, 204):
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return {"status": "contact_added", "email": data.email}


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

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, EmailStr
from .brevo_service import (
    invite_user,
    send_info_email,
    get_registered_users,
    handle_csv,
)

router = APIRouter()


class UserEmail(BaseModel):
    email: EmailStr


@router.post("/invite_user")
async def invite(data: UserEmail):
    users = get_registered_users()
    response = invite_user(data.email, users)
    if response.status_code != 201:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return {"status": "invited", "email": data.email}


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

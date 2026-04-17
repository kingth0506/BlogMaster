# -*- coding: utf-8 -*-
"""Google Drive 자동 업로드 — OAuth 인증 (유저 계정)"""
import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET = os.path.join(BASE_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(BASE_DIR, "drive_token.json")
FOLDER_ID = "1CwYjWw0pMfElwh40e_8HmekPaQnnU9H1"
SCOPES = ["https://www.googleapis.com/auth/drive"]


def get_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)


def find_file(service, name: str, folder_id: str = FOLDER_ID):
    q = f"name='{name}' and '{folder_id}' in parents and trashed=false"
    results = service.files().list(q=q, fields="files(id,name)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def upload_or_update(file_path: str, file_name: str = None, folder_id: str = FOLDER_ID):
    if not os.path.exists(file_path):
        print(f"파일 없음: {file_path}")
        return None

    service = get_service()
    name = file_name or os.path.basename(file_path)
    media = MediaFileUpload(file_path, resumable=True)

    existing_id = find_file(service, name, folder_id)

    if existing_id:
        updated = service.files().update(
            fileId=existing_id,
            media_body=media,
        ).execute()
        file_id = updated["id"]
        print(f"업데이트 완료: {name} (ID: {file_id})")
    else:
        metadata = {"name": name, "parents": [folder_id]}
        created = service.files().create(
            body=metadata,
            media_body=media,
            fields="id",
        ).execute()
        file_id = created["id"]
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
        ).execute()
        print(f"업로드 완료: {name} (ID: {file_id})")

    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    print(f"다운로드 링크: {download_url}")
    return download_url


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python drive_upload.py <파일경로> [파일명]")
        sys.exit(1)
    path = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else None
    upload_or_update(path, name)

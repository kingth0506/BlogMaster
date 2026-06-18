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


LOGS_FOLDER_PREFIX = "blogmaster_logs_"


def get_or_create_folder(service, name: str, parent_id: str = FOLDER_ID) -> str:
    q = (f"name='{name}' and '{parent_id}' in parents"
         f" and mimeType='application/vnd.google-apps.folder' and trashed=false")
    results = service.files().list(q=q, fields="files(id)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]
    metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_log_file(local_path: str, account_folder_name: str, parent_folder_id: str = FOLDER_ID):
    """로그 파일 하나를 Drive의 account 서브폴더에 업로드/업데이트"""
    if not os.path.exists(local_path):
        return
    try:
        service = get_service()
        sub_id = get_or_create_folder(service, f"{LOGS_FOLDER_PREFIX}{account_folder_name}", parent_folder_id)
        file_name = os.path.basename(local_path)
        media = MediaFileUpload(local_path, resumable=False)
        existing_id = find_file(service, file_name, sub_id)
        if existing_id:
            service.files().update(fileId=existing_id, media_body=media).execute()
        else:
            metadata = {"name": file_name, "parents": [sub_id]}
            service.files().create(body=metadata, media_body=media, fields="id").execute()
    except Exception as e:
        print(f"Drive 업로드 실패 ({local_path}): {e}")


def delete_log_file(file_name: str, account_folder_name: str, parent_folder_id: str = FOLDER_ID):
    """Drive의 account 서브폴더에서 파일 삭제"""
    try:
        service = get_service()
        q = (f"name='{LOGS_FOLDER_PREFIX}{account_folder_name}' and '{parent_folder_id}' in parents"
             f" and mimeType='application/vnd.google-apps.folder' and trashed=false")
        results = service.files().list(q=q, fields="files(id)").execute()
        folders = results.get("files", [])
        if not folders:
            return
        sub_id = folders[0]["id"]
        file_id = find_file(service, file_name, sub_id)
        if file_id:
            service.files().delete(fileId=file_id).execute()
    except Exception as e:
        print(f"Drive 삭제 실패 ({file_name}): {e}")


def download_logs_for_account(account_folder_name: str, local_dir: str, parent_folder_id: str = FOLDER_ID):
    """Drive의 account 서브폴더 파일을 모두 local_dir로 다운로드"""
    import io
    from googleapiclient.http import MediaIoBaseDownload
    try:
        service = get_service()
        q = (f"name='{LOGS_FOLDER_PREFIX}{account_folder_name}' and '{parent_folder_id}' in parents"
             f" and mimeType='application/vnd.google-apps.folder' and trashed=false")
        results = service.files().list(q=q, fields="files(id)").execute()
        folders = results.get("files", [])
        if not folders:
            return
        sub_id = folders[0]["id"]
        drive_files = service.files().list(
            q=f"'{sub_id}' in parents and trashed=false",
            fields="files(id,name)"
        ).execute().get("files", [])
        os.makedirs(local_dir, exist_ok=True)
        for f in drive_files:
            local_path = os.path.join(local_dir, f["name"])
            request = service.files().get_media(fileId=f["id"])
            with open(local_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
    except Exception as e:
        print(f"Drive 다운로드 실패 ({account_folder_name}): {e}")


def list_drive_log_folders(app_user: str, parent_folder_id: str = FOLDER_ID) -> list:
    """Drive에서 app_user에 해당하는 logs 폴더 목록 반환 [account_folder_name, ...]"""
    try:
        service = get_service()
        prefix = f"{LOGS_FOLDER_PREFIX}{app_user}_"
        q = (f"'{parent_folder_id}' in parents"
             f" and mimeType='application/vnd.google-apps.folder' and trashed=false")
        results = service.files().list(q=q, fields="files(id,name)").execute()
        return [f["name"].replace(LOGS_FOLDER_PREFIX, "")
                for f in results.get("files", [])
                if f["name"].startswith(prefix)]
    except Exception as e:
        print(f"Drive 폴더 목록 실패: {e}")
        return []


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python drive_upload.py <파일경로> [파일명]")
        sys.exit(1)
    path = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else None
    upload_or_update(path, name)

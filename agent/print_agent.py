import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone

import requests
from supabase import Client, create_client

SUPABASE_URL = "SUPABASE_URL"
SUPABASE_SERVICE_ROLE_KEY = "SUPABASE_SERVICE_ROLE_KEY"
SHOP_ID = "SHOP_ID"
BUCKET_NAME = "print-uploads"
SUMATRA_EXE = "SumatraPDF.exe"
POLL_INTERVAL_SECONDS = 3
PRINT_SETTINGS = "fit"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_supabase_client() -> Client:
    if "SUPABASE_URL" in SUPABASE_URL or "SUPABASE_SERVICE_ROLE_KEY" in SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Update SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY before running the agent.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def fetch_next_job(sb: Client):
    response = (
        sb.table("print_jobs")
        .select("id, file_path")
        .eq("shop_id", SHOP_ID)
        .eq("payment_status", "paid")
        .eq("print_status", "queued")
        .order("created_at", desc=False)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def claim_job(sb: Client, job_id: int) -> bool:
    response = (
        sb.table("print_jobs")
        .update({"print_status": "printing", "updated_at": utc_now_iso()})
        .eq("id", job_id)
        .eq("print_status", "queued")
        .execute()
    )
    return bool(response.data)


def set_job_status(sb: Client, job_id: int, status: str):
    sb.table("print_jobs").update({"print_status": status, "updated_at": utc_now_iso()}).eq("id", job_id).execute()


def download_pdf(file_path: str) -> str:
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": "Bearer " + SUPABASE_SERVICE_ROLE_KEY,
    }
    object_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET_NAME}/{file_path}"

    with requests.get(object_url, headers=headers, timeout=60) as response:
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(response.content)
            return temp_file.name


def silent_print(pdf_path: str):
    if not os.path.exists(SUMATRA_EXE):
        raise FileNotFoundError(f"{SUMATRA_EXE} not found. Place it in the same directory as print_agent.py.")

    command = [
        SUMATRA_EXE,
        "-print-to-default",
        "-silent",
        "-print-settings",
        PRINT_SETTINGS,
        pdf_path,
    ]
    subprocess.run(command, check=True, timeout=120)


def process_job(sb: Client, job: dict):
    job_id = job["id"]
    file_path = job["file_path"]
    local_pdf_path = None

    try:
        print(f"[INFO] Processing job #{job_id}")
        local_pdf_path = download_pdf(file_path)
        silent_print(local_pdf_path)
        set_job_status(sb, job_id, "completed")
        print(f"[OK] Completed job #{job_id}")
    except Exception as exc:
        print(f"[ERROR] Job #{job_id} failed: {exc}")
        set_job_status(sb, job_id, "queued")
    finally:
        if local_pdf_path and os.path.exists(local_pdf_path):
            os.remove(local_pdf_path)


def main():
    print("Campus Quick Print Agent started...")
    print(f"Watching SHOP_ID={SHOP_ID}")
    sb = get_supabase_client()

    while True:
        try:
            job = fetch_next_job(sb)
            if not job:
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            if not claim_job(sb, job["id"]):
                continue

            process_job(sb, job)
        except KeyboardInterrupt:
            print("\n[INFO] Agent stopped by user.")
            break
        except Exception as exc:
            print(f"[ERROR] Agent loop error: {exc}")
            time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_on_demand.py - 수동 갱신 요청 감지 후 데이터 업데이트
Task Scheduler에서 5분마다 실행하세요.
"""

import sys
import os
import subprocess
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = "https://miyrssfrjvhwswjylahw.supabase.co"
SUPABASE_SERVICE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1peXJzc2ZyanZod3N3anlsYWh3Iiwicm9sZSI6"
    "InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyMjE0NiwiZXhwIjoyMDg3NTk4MTQ2fQ."
    "rZczJNVwP5ApcQnFFiogD_Bop3IIAItNPjUD2zvN0ts"
)

BASE_DIR = r"C:\Users\asdf\webtest"
SCRIPTS = ["update_barchart.py", "update_finviz.py", "update_kospi_map.py"]


def main():
    client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # pending 요청 확인
    res = client.table("refresh_trigger").select("*").eq("status", "pending").limit(1).execute()
    if not res.data:
        return  # 요청 없음

    trigger_id = res.data[0]["id"]
    print(f"[갱신 요청 감지] ID: {trigger_id}")

    # running으로 변경
    client.table("refresh_trigger").update({"status": "running"}).eq("id", trigger_id).execute()

    errors = []
    for script in SCRIPTS:
        path = os.path.join(BASE_DIR, script)
        print(f"  {script} 실행 중...")
        try:
            result = subprocess.run(
                [sys.executable, path],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=BASE_DIR,
            )
            if result.returncode != 0:
                errors.append(f"{script}: {result.stderr[:200]}")
                print(f"  [오류] {script}: {result.stderr[:100]}")
            else:
                print(f"  [완료] {script}")
        except subprocess.TimeoutExpired:
            errors.append(f"{script}: timeout")
            print(f"  [타임아웃] {script}")
        except Exception as e:
            errors.append(f"{script}: {e}")
            print(f"  [예외] {script}: {e}")

    now = datetime.now(timezone.utc).isoformat()
    if errors:
        client.table("refresh_trigger").update({
            "status": "error",
            "completed_at": now,
        }).eq("id", trigger_id).execute()
        print(f"[오류로 완료] {errors}")
    else:
        client.table("refresh_trigger").update({
            "status": "done",
            "completed_at": now,
        }).eq("id", trigger_id).execute()
        print("[갱신 완료]")


if __name__ == "__main__":
    main()

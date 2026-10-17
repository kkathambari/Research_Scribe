"""
ResearchScribe - Personal Data Backup and Restore Utility
Docker-Free Windows Local Deployment (FR-04, AC-11)

Safely archives and restores:
  1. SQLite database (researchscribe.db)
  2. Uploaded reference papers and PDFs (storage/uploads/)
  3. Exported manuscripts (storage/exports/)
  4. Environment settings (.env)

Usage:
  python scripts/backup_data.py --backup [output_path.zip]
  python scripts/backup_data.py --restore <backup_path.zip>
  python scripts/backup_data.py --list
"""

import os
import sys
import json
import shutil
import zipfile
import hashlib
import argparse
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
BACKUP_DIR = ROOT_DIR / "backups"

def sha256_file(filepath: Path) -> str:
    """Computes SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def perform_backup(output_path: str = None) -> Path:
    """Packages all research data into a timestamped zip file."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not output_path:
        target_zip = BACKUP_DIR / f"researchscribe_backup_{timestamp}.zip"
    else:
        target_zip = Path(output_path).resolve()
        target_zip.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("  ResearchScribe - Data Backup")
    print("=" * 65)

    manifest = {
        "version": "3.0.0",
        "created_at": datetime.now().isoformat(),
        "files": []
    }

    db_path = BACKEND_DIR / "researchscribe.db"
    uploads_dir = BACKEND_DIR / "storage" / "uploads"
    exports_dir = BACKEND_DIR / "storage" / "exports"
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        env_path = BACKEND_DIR / ".env"

    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        # 1. Database
        if db_path.exists():
            arcname = "data/researchscribe.db"
            zipf.write(db_path, arcname)
            manifest["files"].append({
                "arcname": arcname,
                "size": db_path.stat().st_size,
                "sha256": sha256_file(db_path)
            })
            print(f"  * Archived database: {db_path.name} ({db_path.stat().st_size} bytes)")
        else:
            print("  * Note: No database file found yet (will be created on first launch).")

        # 2. Uploaded PDFs
        pdf_count = 0
        if uploads_dir.exists():
            for root, _, files in os.walk(uploads_dir):
                for f in files:
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(BACKEND_DIR)
                    arcname = f"data/{rel_p.as_posix()}"
                    zipf.write(full_p, arcname)
                    manifest["files"].append({
                        "arcname": arcname,
                        "size": full_p.stat().st_size,
                        "sha256": sha256_file(full_p)
                    })
                    pdf_count += 1
            print(f"  * Archived uploaded files: {pdf_count} files")

        # 3. Exported files
        export_count = 0
        if exports_dir.exists():
            for root, _, files in os.walk(exports_dir):
                for f in files:
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(BACKEND_DIR)
                    arcname = f"data/{rel_p.as_posix()}"
                    zipf.write(full_p, arcname)
                    manifest["files"].append({
                        "arcname": arcname,
                        "size": full_p.stat().st_size,
                        "sha256": sha256_file(full_p)
                    })
                    export_count += 1
            print(f"  * Archived exported files: {export_count} files")

        # 4. Environment config
        if env_path.exists():
            arcname = "config/.env"
            zipf.write(env_path, arcname)
            manifest["files"].append({
                "arcname": arcname,
                "size": env_path.stat().st_size,
                "sha256": sha256_file(env_path)
            })
            print(f"  * Archived configuration: {env_path.name}")

        # 5. Manifest
        zipf.writestr("manifest.json", json.dumps(manifest, indent=2))

    total_size = target_zip.stat().st_size
    print("-" * 65)
    print(f"  [OK] Backup successfully created:")
    print(f"       File: {target_zip}")
    print(f"       Size: {total_size} bytes ({total_size / (1024*1024):.2f} MB)")
    print("=" * 65)
    return target_zip

def perform_restore(backup_path: str) -> bool:
    """Restores research data from a valid backup zip archive."""
    target_zip = Path(backup_path).resolve()
    if not target_zip.exists():
        print(f"  [ERROR] Backup file does not exist: {target_zip}")
        return False

    print("=" * 65)
    print("  ResearchScribe - Data Restore")
    print("=" * 65)
    print(f"Reading backup archive: {target_zip.name}")

    try:
        with zipfile.ZipFile(target_zip, "r") as zipf:
            if "manifest.json" not in zipf.namelist():
                print("  [ERROR] Invalid backup: missing manifest.json")
                return False
            
            manifest = json.loads(zipf.read("manifest.json").decode("utf-8"))
            print(f"  Backup created: {manifest.get('created_at')} (Version {manifest.get('version')})")
            
            # Optional pre-restore safety snapshot
            existing_db = BACKEND_DIR / "researchscribe.db"
            if existing_db.exists():
                safety_copy = BACKUP_DIR / f"pre_restore_safety_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(existing_db, safety_copy)
                print(f"  * Existing database backed up to: {safety_copy.name}")

            restored_count = 0
            for item in manifest.get("files", []):
                arcname = item["arcname"]
                if arcname.startswith("data/"):
                    rel_p = arcname[len("data/"):]
                    out_path = BACKEND_DIR / rel_p
                elif arcname == "config/.env":
                    out_path = ROOT_DIR / ".env"
                else:
                    continue

                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(out_path, "wb") as f_out:
                    f_out.write(zipf.read(arcname))
                
                # Verify sha256
                computed = sha256_file(out_path)
                if computed != item.get("sha256"):
                    print(f"  [WARN] Checksum mismatch for {out_path.name}")
                restored_count += 1

            print("-" * 65)
            print(f"  [OK] Successfully restored {restored_count} files from backup.")
            print("=" * 65)
            return True
    except Exception as e:
        print(f"  [ERROR] Failed to restore backup: {e}")
        return False

def list_backups():
    """Lists available backups in the backups/ directory."""
    print("=" * 65)
    print("  Available ResearchScribe Backups")
    print("=" * 65)
    if not BACKUP_DIR.exists():
        print("  No backups directory found.")
        return

    backups = sorted(BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        print("  No backup archives found.")
        return

    for idx, b in enumerate(backups, 1):
        mtime = datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size_kb = b.stat().st_size / 1024
        print(f"  {idx}. {b.name}  ({size_kb:.1f} KB, modified: {mtime})")
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(description="ResearchScribe Backup & Restore Tool")
    parser.add_argument("--backup", nargs="?", const="", help="Create backup archive [optional path]")
    parser.add_argument("--restore", type=str, help="Restore from backup archive path")
    parser.add_argument("--list", action="store_true", help="List existing backups")

    args = parser.parse_args()

    if args.backup is not None:
        target = args.backup if args.backup else None
        perform_backup(target)
    elif args.restore:
        success = perform_restore(args.restore)
        if not success:
            sys.exit(1)
    elif args.list:
        list_backups()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

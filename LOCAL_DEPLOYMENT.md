# Docker-Free Local Deployment Guide for ResearchScribe

This guide outlines how to install, configure, run, and maintain **ResearchScribe** directly on your personal Windows computer without requiring Docker, Docker Compose, Kubernetes, or separate virtual machines.

---

## 1. System Requirements

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| **Operating System** | Windows 10 / 11 (64-bit) | Windows 10 / 11 (64-bit) |
| **Python** | Python 3.10+ | Python 3.10, 3.11, or 3.12 |
| **RAM** | 8 GB RAM | 16 GB+ RAM |
| **GPU (Optional)** | None (runs on CPU) | NVIDIA GPU (6GB+ VRAM) for faster LLM inference |
| **AI Runtime** | Host-installed Ollama | Host-installed Ollama |

---

## 2. Prerequisites & One-Time Setup

### A. Python
Ensure Python 3.10 or higher is installed and added to your system `PATH`.
Verify in PowerShell or CMD:
```powershell
python --version
```

### B. Ollama (Host-Installed)
ResearchScribe connects directly to your existing host Ollama service:
1. Download and install Ollama for Windows from [https://ollama.com/download](https://ollama.com/download).
2. Pull your desired model. Recommended models based on system RAM:
   - **8GB RAM / CPU-only:**
     ```powershell
     ollama pull deepseek-coder:latest
     # Or
     ollama pull gemma2:2b
     ```
   - **16GB RAM / 6GB+ GPU:**
     ```powershell
     ollama pull mistral:latest
     # Or
     ollama pull llama3:latest
     ```
3. Verify Ollama is responding:
   ```powershell
   ollama list
   ```

### C. OCR Support (Optional for scanned PDFs)
If you work with scanned paper PDFs that require OCR:
1. Download Tesseract OCR for Windows from [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
2. Add `C:\Program Files\Tesseract-OCR` to your Windows `PATH`.
*Note: If Tesseract is not installed, ResearchScribe automatically extracts text from regular PDFs and displays a non-destructive warning for scanned documents.*

---

## 3. Quick Start (1-Click Launch)

### Option 1: Double-Click Batch File (Recommended)
Double-click `start_researchscribe.bat` in the repository root.

The launcher automatically:
1. Detects or creates the Python virtual environment (`backend\.venv`).
2. Installs required dependencies from `backend\requirements.txt`.
3. Verifies that the host Ollama service is reachable at `http://localhost:11434`.
4. Starts the local ResearchScribe backend at `http://127.0.0.1:8000`.

### Option 2: PowerShell
```powershell
.\start_researchscribe.ps1
```

### Option 3: Manual Command Line
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Once started, access ResearchScribe:
- **Web Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive API Docs (Swagger):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 4. Configuration (`.env`)

A default `.env` file is included in both the root directory and `backend/`. You can customize settings:

```ini
# LLM Provider: "ollama" (default local), "gemini" (optional cloud), "heuristic" (offline mock)
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=deepseek-coder:latest
OLLAMA_TIMEOUT=60.0
OLLAMA_KEEP_ALIVE=5m

# Fallback Policy: "none" strictly prevents sending prompts to external APIs without permission
LLM_FALLBACK_PROVIDER=none
LLM_MAX_RETRIES=2

# Optional Gemini Cloud Key (leave blank for 100% offline local privacy)
GEMINI_API_KEY=

# Local Server Binding (bound to localhost for personal workstation security)
HOST=127.0.0.1
PORT=8000

# SQLite Database
DATABASE_URL=sqlite:///./researchscribe.db
```

---

## 5. Local Data Storage & Persistence

All research data is stored locally on your machine:
- **Database:** `backend/researchscribe.db` (SQLite containing projects, sources, evidence cards, citations, manuscript drafts, verification records).
- **Uploaded PDFs:** `backend/storage/uploads/` (PDF files uploaded as references).
- **Exported Manuscripts:** `backend/storage/exports/` (Generated DOCX, PDF, and LaTeX documents).
- **Ollama Models:** Stored in `%USERPROFILE%\.ollama\models` by Ollama, preserved independently of ResearchScribe.

---

## 6. Personal Data Backup & Restore

ResearchScribe provides a dedicated backup and restore tool (`scripts/backup_data.py`) with 1-click Windows batch scripts.

### Creating a Backup
Double-click `backup_data.bat` or run:
```powershell
.\backend\.venv\Scripts\python.exe scripts/backup_data.py --backup
```
- Archives `researchscribe.db`, all uploaded PDFs, exported manuscripts, and `.env`.
- Creates a timestamped `.zip` archive in `backups/` with a verified `manifest.json` and SHA256 checksums.

### Restoring from a Backup
Double-click `restore_data.bat` to list available backups, or pass a specific backup:
```powershell
restore_data.bat backups\researchscribe_backup_YYYYMMDD_HHMMSS.zip
```
- Validates the manifest and file integrity.
- Creates an automatic safety copy of existing data before restoring.

---

## 7. Personal-Use Security

1. **Localhost Isolation:** The server binds strictly to `127.0.0.1:8000` by default, preventing unauthorized network access from other devices on your local network.
2. **Zero Cloud Leakage:** When `LLM_FALLBACK_PROVIDER=none`, research queries, PDF texts, and manuscript contents are never sent to external cloud LLM providers.
3. **No Committed Secrets:** API keys and credentials reside exclusively in `.env`, which is ignored by Git.

---

## 8. Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `[WARN] Ollama is NOT reachable at http://localhost:11434` | Ollama service is stopped | Open PowerShell and run `ollama serve`, or start the Ollama desktop app. |
| `Model 'xyz' was not found in installed models` | Model hasn't been pulled | Run `ollama pull <model_name>` (e.g. `ollama pull deepseek-coder:latest`) or adjust `OLLAMA_MODEL` in `.env`. |
| Port 8000 already in use | Another application is using port 8000 | Set `PORT=8080` in `.env` and relaunch. |
| Slow generation on CPU | Large model running on limited RAM | Switch to a lightweight model: `ollama pull deepseek-coder:latest` or `ollama pull gemma2:2b`, and set `OLLAMA_MODEL` in `.env`. |
| Scanned PDF OCR warning | Tesseract not found on system PATH | Install Tesseract OCR from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH. |

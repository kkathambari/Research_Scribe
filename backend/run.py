import sys
import httpx
import uvicorn
from app.config import settings

def check_local_environment():
    print("=" * 70)
    print("  ResearchScribe - Evidence-Grounded AI Research Writing System")
    print("  Mode: Docker-Free Native Windows Deployment")
    print("=" * 70)
    print(f"* Host Binding   : http://{settings.HOST}:{settings.PORT}")
    print(f"* API Docs       : http://{settings.HOST}:{settings.PORT}/docs")
    print(f"* Database       : {settings.DATABASE_URL}")
    print(f"* LLM Provider   : {settings.LLM_PROVIDER}")
    print(f"* Fallback Policy: {settings.LLM_FALLBACK_PROVIDER}")
    
    if settings.LLM_PROVIDER == "ollama":
        print(f"* Ollama Endpoint: {settings.OLLAMA_BASE_URL}")
        print(f"* Configured Model: {settings.OLLAMA_MODEL}")
        try:
            resp = httpx.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=3.0)
            if resp.status_code == 200:
                models = [m.get("name") for m in resp.json().get("models", [])]
                print(f"  [OK] Ollama is REACHABLE. Available models: {models}")
                model_base = settings.OLLAMA_MODEL.split(":")[0]
                matched = any(settings.OLLAMA_MODEL == m or m.startswith(model_base) for m in models)
                if matched:
                    print(f"  [OK] Model '{settings.OLLAMA_MODEL}' is ready.")
                else:
                    print(f"  [WARN] Model '{settings.OLLAMA_MODEL}' was not found in installed models.")
                    print(f"         Run 'ollama pull {settings.OLLAMA_MODEL}' or update OLLAMA_MODEL in .env.")
            else:
                print(f"  [WARN] Ollama returned HTTP status {resp.status_code}")
        except Exception:
            print(f"  [WARN] Ollama is NOT reachable at {settings.OLLAMA_BASE_URL}")
            print("         To start Ollama on Windows, run 'ollama serve' or launch the Ollama app.")
            print("         ResearchScribe will continue with heuristic fallback if configured.")
    elif settings.LLM_PROVIDER == "gemini":
        if not settings.GEMINI_API_KEY:
            print("  [WARN] GEMINI_API_KEY is not set. Set GEMINI_API_KEY in .env or switch to Ollama.")
        else:
            print(f"* Gemini Model   : {settings.GEMINI_MODEL}")
    
    print("=" * 70)
    print(f"Starting server on http://{settings.HOST}:{settings.PORT} (Press Ctrl+C to stop)...")
    print("=" * 70)

if __name__ == "__main__":
    check_local_environment()
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)


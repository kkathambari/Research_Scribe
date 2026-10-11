import uvicorn

if __name__ == "__main__":
    print("=" * 65)
    print("🚀 ResearchScribe — Evidence-Grounded AI Research Writing System")
    print("Serving web dashboard at: http://localhost:8000")
    print("Interactive Swagger API at: http://localhost:8000/docs")
    print("=" * 65)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

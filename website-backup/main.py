"""
Mirai Portal — Entry point.

Local dev:   python main.py
             uvicorn main:app --reload --port 8000

AWS Lambda:  handler = main.handler  (via Mangum)
"""

from app import create_app

app = create_app()

# AWS Lambda adapter (conditional — mangum not required for local dev)
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    handler = None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

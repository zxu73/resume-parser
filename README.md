cd C:\Users\Zicho\OneDrive\Desktop\resume-parser\backend
.venv\Scripts\activate
cd src
uvicorn agent.app:app --host 127.0.0.1 --port 8000 --reload

cd C:\Users\Zicho\OneDrive\Desktop\resume-parser\frontend
npm run dev
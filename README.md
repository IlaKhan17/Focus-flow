# Focus Flow

Focus Flow is a small full‑stack app that helps you plan and protect deep‑work sessions.

- Break a vague task into concrete steps  
- Estimate roughly how long each step will take  
- Start a focus session and log how long you actually worked  
- See simple stats about your recent focus time  

---

## Running the project

### Backend (Python)

```bash
cd backend
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
# source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at `http://localhost:8000` (interactive docs at `/docs`).

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:3000` and will show “Backend: connected” once the API is up.

---

## Stack

- FastAPI (Python)  
- SQLModel + SQLite  
- Next.js (React + TypeScript)

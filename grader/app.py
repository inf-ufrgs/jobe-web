from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
import json
import logging
import os

# --- CONFIGURATION ---
# 1. Get Jobe URL from Environment (Default to localhost for testing)
DEFAULT_LOCAL_JOBE = "http://localhost:4000/jobe/index.php/restapi/runs"
JOBE_URL = os.getenv("JOBE_URL", DEFAULT_LOCAL_JOBE)

# 2. Jobe Outcome Codes
JOBE_OUTCOME_MAP = {
    15: "Success",
    11: "Compilation Error",
    12: "Runtime Error",
    13: "Time Limit Exceeded",
    17: "Memory Limit Exceeded",
    19: "Security Violation",
    20: "Internal Error",
    21: "Server Overloaded",
}

# --- SECURITY CONFIGURATION ---
# ONLY this ID is allowed to submit code.
# Later we can expand this to a list or a proper auth system.
ALLOWED_STUDENT_ID = "00177562"

# --- FASTAPI SETUP ---
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Configure Logging (This is your "Database" for now)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grader")

# Load Tests
with open("assignments.json", "r") as f:
    ASSIGNMENTS = json.load(f)

# The Wrapper to silence inputs
MOCK_WRAPPER = """
import sys
def input(prompt=None):
    line = sys.stdin.readline()
    if not line: return ""
    return line.strip()
"""

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Pass assignment list to the dropdown
    return templates.TemplateResponse("index.html", {"request": request, "assignments": ASSIGNMENTS})

@app.post("/submit", response_class=HTMLResponse)
async def submit_code(
    request: Request, 
    student_id: str = Form(...), 
    assignment_id: str = Form(...), 
    code: str = Form(...)
):
    # 1. SECURITY CHECK (Hard-coded Auth)
    # We strip whitespace just in case they added a space by accident
    if student_id.strip() != ALLOWED_STUDENT_ID:
        logger.warning(f"UNAUTHORIZED ATTEMPT | Student: {student_id} | IP: {request.client.host}")
        return HTMLResponse(
            content=f"""
            <div style="color: red; font-family: sans-serif; padding: 20px; text-align: center;">
                <h1>🚫 Access Denied</h1>
                <p>The Student ID <strong>{student_id}</strong> is not authorized to use this system.</p>
                <a href="/">Go Back</a>
            </div>
            """, 
            status_code=403
        )

    # 2. Logging (Authorized)
    client_ip = request.client.host
    logger.info(f"SUBMISSION | Student: {student_id} | Lab: {assignment_id}")

    if assignment_id not in ASSIGNMENTS:
        return HTMLResponse("Invalid Assignment ID", status_code=400)

    tests = ASSIGNMENTS[assignment_id]['cases']
    results = []
    score = 0
    
    # Inject wrapper before student code
    full_code = MOCK_WRAPPER + "\n" + code

    for i, test in enumerate(tests):
        payload = {
            "run_spec": {
                "language_id": "python3",
                "sourcecode": full_code,
                "input": test['input']
            }
        }
        
        try:
            resp = requests.post(JOBE_URL, json=payload, timeout=6)
            
            if resp.status_code != 200:
                results.append({
                    "status": "SERVER ERROR", 
                    "css": "secondary", 
                    "details": f"Jobe returned HTTP {resp.status_code}"
                })
                continue

            outcome_data = resp.json()
            outcome_code = outcome_data['outcome']
            outcome_desc = JOBE_OUTCOME_MAP.get(outcome_code, f"Unknown Error ({outcome_code})")
            
            # 1. CHECK EXECUTION HEALTH
            if outcome_code != 15:
                # If it didn't run successfully (Crashed, Timeout, etc)
                # 'cmpinfo' usually holds Python tracebacks or SyntaxErrors
                error_details = outcome_data.get('cmpinfo', '') 
                
                # Fallback: sometimes Jobe puts runtime errors in stdout or stderr
                if not error_details:
                     error_details = outcome_data.get('stderr', '')

                results.append({
                    "status": outcome_desc, # e.g. "Runtime Error"
                    "css": "warning", 
                    "details": error_details # e.g. "ZeroDivisionError..."
                })
                continue

            # 2. CHECK LOGIC (Only if execution was successful)
            actual = outcome_data['stdout'].strip()
            expected = test['expected'].strip()
            
            if actual == expected:
                results.append({
                    "status": "PASS", 
                    "css": "success", 
                    "details": f"Output: {actual}"
                })
                score += 1
            else:
                results.append({
                    "status": "FAIL", 
                    "css": "danger", 
                    "details": f"Expected:\n{expected}\n\nGot:\n{actual}"
                })

        except Exception as e:
            results.append({"status": "CONNECTION ERROR", "css": "dark", "details": str(e)})

    return templates.TemplateResponse("result.html", {
        "request": request, 
        "results": results, 
        "score": f"{score}/{len(tests)}",
        "student_id": student_id,
        "total": len(tests)
    })
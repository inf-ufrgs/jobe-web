from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import requests
import json
import logging

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Configure Logging (This is your "Database" for now)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grader")

# INTERNAL URL (K8s Service DNS)
JOBE_URL = "http://jobe-service.jobe-web.svc.cluster.local:80/jobe/index.php/restapi/runs"

# Load Tests
with open("tests.json", "r") as f:
    ASSIGNMENTS = json.load(f)

# The Wrapper to silence inputs
MOCK_WRAPPER = """
import sys
import builtins
def input(prompt=None):
    return builtins.sys.stdin.readline().strip()
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
    # 1. Minimal Auth / Logging
    # We rely on the student telling the truth for now. 
    # In K8s logs, you will see: "Student 00123456 submitted lab1"
    client_ip = request.client.host
    logger.info(f"SUBMISSION | Student: {student_id} | IP: {client_ip} | Lab: {assignment_id}")

    if assignment_id not in ASSIGNMENTS:
        return "Invalid Assignment"

    tests = ASSIGNMENTS[assignment_id]['cases']
    results = []
    
    # 2. Run Tests on Jobe
    full_code = MOCK_WRAPPER + "\n" + code
    
    score = 0
    for i, test in enumerate(tests):
        payload = {
            "run_spec": {
                "language_id": "python3",
                "sourcecode": full_code,
                "input": test['input']
            }
        }
        
        try:
            # Short timeout to prevent freezing
            resp = requests.post(JOBE_URL, json=payload, timeout=5)
            if resp.status_code == 200:
                outcome = resp.json()
                actual = outcome['stdout'].strip()
                expected = test['expected'].strip()
                
                if outcome['outcome'] == 15 and actual == expected:
                    results.append({"status": "✅ Passed", "details": ""})
                    score += 1
                else:
                    err_msg = outcome.get('cmpinfo', '') or f"Got '{actual}', expected '{expected}'"
                    results.append({"status": "❌ Failed", "details": err_msg})
            else:
                 results.append({"status": "⚠️ Error", "details": "Jobe Server Error"})

        except Exception as e:
            results.append({"status": "💥 Error", "details": str(e)})

    # 3. Return HTML Result
    return templates.TemplateResponse("result.html", {
        "request": request, 
        "results": results, 
        "score": f"{score}/{len(tests)}",
        "student_id": student_id
    })
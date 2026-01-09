import os
import requests
import logging
import shutil         # For clearing invalid git folders
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from git import Repo, exc
import markdown
import yaml

# --- CONFIGURATION ---
# 1. Get Jobe URL from Environment (Default to localhost for testing)
DEFAULT_LOCAL_JOBE = "http://localhost:4000/jobe/index.php/restapi/runs"
DEFAULT_REPO_URL = "https://github.com/inf-ufrgs/inf01040-assignments.git"
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

# 3. Assignments loading from GitHub
ASSIGNMENTS_DIR = "./assignments"
REPO_URL = os.getenv("GIT_REPO_URL", DEFAULT_REPO_URL) # e.g. https://github.com/inf-ufrgs/inf01040-assignments.git
GIT_TOKEN = os.getenv("GIT_TOKEN")   # The Secret Token

# --- SECURITY CONFIGURATION ---
# ONLY this ID is allowed to submit code.
# Later we can expand this to a list or a proper auth system.
ALLOWED_STUDENT_ID = "00177562"

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grader")

# Global State
ASSIGNMENTS = {}

# --- HELPER FUNCTIONS ---
def load_assignments_from_disk():
    """Scans the folder, reads README.md and config.yaml"""
    new_assignments = {}
    if not os.path.exists(ASSIGNMENTS_DIR):
        logger.error(f"Assignments directory does not exist: {ASSIGNMENTS_DIR}")
        return new_assignments

    subfolders = [f.path for f in os.scandir(ASSIGNMENTS_DIR) if f.is_dir()]

    for folder in subfolders:
        lab_id = os.path.basename(folder)
        if lab_id.startswith("."): 
            continue # Skip hidden .git folders

        # 1. Load Markdown
        readme_path = os.path.join(folder, "README.md")
        description_html = "<p>No description available.</p>"
        if os.path.exists(readme_path):
            with open(readme_path, 'r') as f:
                description_html = markdown.markdown(f.read(), extensions=['fenced_code', 'codehilite', 'tables'])
        else:
            logger.warning(f"README.md not found for {lab_id}")
        # 2. Load Config
        config_path = os.path.join(folder, "config.yaml")
        config = {"title": lab_id, "time_limit": 5, "memory_limit": 128, "author": "Unknown", "tests": []} # Defaults
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    data = yaml.safe_load(f)
                    if data: config.update(data)
            except Exception as e:
                logger.error(f"Error loading {lab_id}: {e}")
        else:
            logger.warning(f"config.yaml not found for {lab_id}")

        if config["tests"]:
            new_assignments[lab_id] = {
                "title": config["title"],
                "description_html": description_html,
                "time_limit": config["time_limit"],
                "memory_limit": config["memory_limit"],
                "author": config["author"],
                "cases": config["tests"]
            }
            logger.info(f"Loaded assignment: {lab_id} with {len(config['tests'])} test cases.")
            logger.debug(f"Config: {config}")
    
    return new_assignments

# --- LIFESPAN HANDLER (The New Way) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # === STARTUP LOGIC ===
    logger.info("🚀 Grader App Starting Up...")
    logger.info(f"🔗 Jobe Backend at: {JOBE_URL}")

    global ASSIGNMENTS

    if REPO_URL and GIT_TOKEN:
        # Construct Authenticated URL safely
        auth_url = REPO_URL.replace("https://", f"https://{GIT_TOKEN}@")
        
        if os.path.exists(ASSIGNMENTS_DIR):
            logger.info("📂 Assignments folder exists. Updating...")
            try:
                repo = Repo(ASSIGNMENTS_DIR)
                # This ensures that if the token changes, the repo updates its config.
                repo.remotes.origin.set_url(auth_url)
                repo.remotes.origin.pull()
            except exc.InvalidGitRepositoryError:
                logger.warning("⚠️ Folder exists but is not a valid git repo. Re-cloning...")
                shutil.rmtree(ASSIGNMENTS_DIR)
                Repo.clone_from(auth_url, ASSIGNMENTS_DIR)
        else:
            logger.info("📥 Cloning Private Repository...")
            Repo.clone_from(auth_url, ASSIGNMENTS_DIR)
            
        ASSIGNMENTS = load_assignments_from_disk()
        logger.info(f"📚 Loaded {len(ASSIGNMENTS)} assignments from Git.")
    else:
        logger.warning("⚠️ No GIT credentials provided. Using empty assignment list.")
    
    # === YIELD CONTROL TO APP ===
    yield
    
    # === SHUTDOWN LOGIC (Optional) ===
    logger.info("🛑 Grader App Shutting Down...")
    # Clear the temp folder here if needed, 
    # but keeping it speeds up the next restart.

# --- APP INITIALIZATION ---
app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

# The Wrapper to silence inputs
MOCK_WRAPPER = """
import sys
def input(prompt=None):
    line = sys.stdin.readline()
    if not line: return ""
    return line.strip()
"""

# --- ROUTES ---
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(content="""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
          <text y=".9em" font-size="90">🐍</text>
        </svg>
    """, media_type="image/svg+xml")

# 1. NEW ROOT ROUTE (No Dropdown)
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return """
    <html>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1>🎓 UFRGS Python Grader</h1>
            <p>Por favor, acesse os exercícios pelo link disponibilizado pelo seu professor.</p>
        </body>
    </html>
    """
# 2. OLD ROOT ROUTE (With Dropdown for manual testing)
'''
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # Pass assignment list to the dropdown
    return templates.TemplateResponse("index.html", {"request": request, "assignments": ASSIGNMENTS})
'''

# 3. ASSIGNMENT ROUTE
@app.get("/assignment/{assignment_id}", response_class=HTMLResponse)
async def view_assignment(request: Request, assignment_id: str):
    if assignment_id not in ASSIGNMENTS:
        logger.warning(f"Assignment not found: {assignment_id}")
        raise HTTPException(status_code=404, detail="Assignment not found. Please check your URL.")

    lab_data = ASSIGNMENTS[assignment_id]

    return templates.TemplateResponse("assignment.html", {
        "request": request,
        "assignment_id": assignment_id, # Passed to the hidden input
        "title": lab_data['title'],
        "description_html": lab_data['description_html'],
        "time_limit": lab_data.get('time_limit'),
        "memory_limit": lab_data.get('memory_limit'),
        "author": lab_data.get('author')
    })

# 4. SUBMISSION ROUTE
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
                <a href="javascript: history.back()">Go Back</a>
            </div>
            """, 
            status_code=403
        )

    # 2. Logging (Authorized)
    client_ip = request.client.host
    logger.info(f"SUBMISSION | Student: {student_id} | Assignment: {assignment_id}")

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
                    "name": test['name'],
                    "status": outcome_desc, # e.g. "Runtime Error"
                    "css": "warning", 
                    "details": error_details # e.g. "ZeroDivisionError..."
                })
                continue

            # 2. CHECK LOGIC (Only if execution was successful)
            actual = outcome_data['stdout'].strip()
            expected = test['output'].strip()
            
            if actual == expected:
                results.append({
                    "name": test['name'],
                    "status": "PASS", 
                    "css": "success", 
                    "details": f"Output: {actual}"
                })
                score += 1
            else:
                results.append({
                    "name": test['name'],
                    "status": "FAIL", 
                    "css": "danger", 
                    "details": f"Expected:\n{expected}\n\nGot:\n{actual}"
                })

        except Exception as e:
            logger.error(f"Connection error during submission: {e}{type(e)}")
            results.append({"status": "CONNECTION ERROR", "css": "dark", "details": str(e)})

    return templates.TemplateResponse("result.html", {
        "request": request,
        "results": results, 
        "score": f"{score}/{len(tests)}",
        "student_id": student_id,
        "total": len(tests)
    })
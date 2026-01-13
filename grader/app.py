import os
import requests
import logging
import shutil         # For clearing invalid git folders
from contextlib import asynccontextmanager
from fastapi import FastAPI, Form, HTTPException, Request, Response, UploadFile, File
import zipfile
import shutil
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

# Configure Log Level from Environment
log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level_str, logging.INFO)
logging.basicConfig(level=numeric_level)
logger = logging.getLogger("grader")

# Global State
ASSIGNMENTS = {}
AUTHORIZED_USERS = {
    "students": set(),
    "professors": set()
}

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
            logger.debug(f"Loaded assignment: {lab_id} with {len(config['tests'])} test cases.")
            logger.debug(f"Config: {config}")
    
    return new_assignments

# --- HELPER: Load Users ---
def load_users_from_disk():
    """Reads users.yaml and returns a dict of sets"""
    users_path = os.path.join(ASSIGNMENTS_DIR, "users.yaml")
    data = {"students": set(), "professors": set()}
    
    if os.path.exists(users_path):
        try:
            with open(users_path, 'r') as f:
                raw = yaml.safe_load(f) or {}
                
                # Convert lists to sets for O(1) lookup speed
                # usage of str() ensures we don't have integer/string mismatches
                if "students" in raw:
                    data["students"] = set(str(u) for u in raw["students"])
                
                if "professors" in raw:
                    data["professors"] = set(str(u) for u in raw["professors"])
                    
        except Exception as e:
            logger.error(f"❌ Error loading users.yaml: {e}")
    else:
        logger.warning("⚠️ users.yaml not found. Authentication might fail.")
        
    return data

# --- HELPER: The Grading Engine ---
def grade_submission(code, assignment_id):
    """
    Runs the code against the tests for the given assignment.
    Returns: (score, max_score, results_list)
    """
    if assignment_id not in ASSIGNMENTS:
        return 0, 0, [{"status": "ERROR", "css": "danger", "details": "Problema inválido!"}]

    lab_data = ASSIGNMENTS[assignment_id]
    tests = lab_data['cases']
    time_limit = lab_data.get('time_limit', 5)
    
    results = []
    score = 0
    
    # Inject wrapper
    full_code = MOCK_WRAPPER + "\n" + code

    for test in tests:
        name = test.get('name', 'Test Case')
        payload = {
            "run_spec": {
                "language_id": "python3",
                "sourcecode": full_code,
                "input": test['input'] if test['input'] else "",
                "parameters": {"cputime": time_limit}
            }
        }
        
        try:
            # We use a shorter timeout for Python requests to catch hangs
            resp = requests.post(JOBE_URL, json=payload, timeout=time_limit + 2)
            
            if resp.status_code != 200:
                results.append({"status": "SERVER ERROR", "css": "secondary", "details": f"HTTP {resp.status_code}"})
                continue

            outcome = resp.json()
            if outcome['outcome'] == 15:
                actual = outcome['stdout'].strip()
                expected = test['output'].strip()
                if actual.lower() == expected.lower():
                    results.append({"name": name, "status": "PASS", "css": "success", "details": "OK"})
                    score += 1
                else:
                    results.append({"name": name, "status": "FAIL", "css": "warning", "details": f"{20*'-'} Saída Esperada {20*'-'}\n{expected}\n\n{20*'-'} Saída Recebida {20*'-'}\n{actual}"})
            else:
                # Runtime/Syntax Error
                err = outcome.get('cmpinfo') or outcome.get('stderr') or "Runtime Error"
                results.append({"name": name, "status": JOBE_OUTCOME_MAP.get(outcome['outcome'], "Error"), "css": "danger", "details": err})

        except Exception as e:
            results.append({"status": "CONNECTION ERROR", "css": "dark", "details": str(e)})

    return score, len(tests), results

# --- LIFESPAN HANDLER (The New Way) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # === STARTUP LOGIC ===
    logger.info("🚀 Grader App Starting Up...")
    logger.info(f"🔗 Jobe Backend at: {JOBE_URL}")

    global ASSIGNMENTS, AUTHORIZED_USERS

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
            
        # Load Assignments and Users
        ASSIGNMENTS = load_assignments_from_disk()
        logger.info(f"📚 Loaded {len(ASSIGNMENTS)} assignments from Git.")
        AUTHORIZED_USERS = load_users_from_disk()
        logger.info(f"👥 Loaded {len(AUTHORIZED_USERS['students'])} students and {len(AUTHORIZED_USERS['professors'])} professors.")
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

# 1. ROOT ROUTE
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

# 2. STUDENT ASSIGNMENT ROUTE
@app.get("/assignment/{assignment_id}", response_class=HTMLResponse)
async def view_assignment(request: Request, assignment_id: str):
    if assignment_id not in ASSIGNMENTS:
        logger.warning(f"Student assignment not found: {assignment_id}")
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

# 3. STUDENT SUBMISSION ROUTE
@app.post("/submit", response_class=HTMLResponse)
async def submit_code(
    request: Request, 
    student_id: str = Form(...), 
    assignment_id: str = Form(...), 
    code: str = Form(...)
):
    # 1. SECURITY CHECK
    # We strip whitespace just in case they added a space by accident
    client_ip = request.client.host
    if student_id.strip() not in AUTHORIZED_USERS["students"] and student_id.strip() not in AUTHORIZED_USERS["professors"]:
        logger.warning(f"UNAUTHORIZED ATTEMPT | Student: {student_id} | IP: {client_ip}")
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
    logger.info(f"SUBMISSION | Student: {student_id} | Assignment: {assignment_id} | IP: {client_ip}")

    # 3. CALL THE HELPER
    score, total, results = grade_submission(code, assignment_id)

    # 4. RETURN RESPONSE
    return templates.TemplateResponse("result.html", {
        "request": request, 
        "results": results, 
        "score": f"{score}/{total}",
        "student_id": student_id,
        "assignment_id": assignment_id
    })

# 4. PROFESSOR ASSIGNMENT ROUTE
@app.get("/professor/{assignment_id}", response_class=HTMLResponse)
async def professor_upload_page(request: Request, assignment_id: str):
    """
    Renders the upload page SPECIFIC to one assignment.
    """
    if assignment_id not in ASSIGNMENTS:
        logger.warning(f"Professor assignment not found: {assignment_id}")
        raise HTTPException(status_code=404, detail="Assignment not found")

    lab_data = ASSIGNMENTS[assignment_id]

    return templates.TemplateResponse("professor_upload.html", {
        "request": request,
        "assignment_id": assignment_id,
        "title": lab_data['title']
    })

# 5. PROFESSOR SUBMISSION ROUTE
@app.post("/professor/grade", response_class=HTMLResponse)
async def professor_grade(
    request: Request,
    prof_id: str = Form(...),
    assignment_id: str = Form(...),
    zip_file: UploadFile = File(...)
):
    # 1. Auth Check
    if prof_id.strip() not in AUTHORIZED_USERS["professors"]:
        return HTMLResponse("<h1>🚫 Access Denied</h1>", status_code=403)

    # 2. Setup Temp Directory
    # We use a random suffix or timestamp to prevent collisions if two TAs grade at once
    import uuid
    run_id = str(uuid.uuid4())[:8]
    temp_dir = f"/tmp/grade_{assignment_id}_{run_id}"
    
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    zip_path = f"{temp_dir}/submissions.zip"
    with open(zip_path, "wb") as buffer:
        shutil.copyfileobj(zip_file.file, buffer)
        
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
    except zipfile.BadZipFile:
        return HTMLResponse("Error: Invalid ZIP file", status_code=400)

    # 3. Iterate through Folders (The "Moodle Parser")
    report_data = []
    
    # Walk through the extracted folder
    # Look for folders that match the pattern "Name_ID_..."
    extracted_root = temp_dir
    
    # Sometimes parsing creates a subfolder, so we check root contents
    items = os.listdir(extracted_root)
    
    for i, item in enumerate(sorted(items)):
        student_dir = os.path.join(extracted_root, item)
        
        # Skip the zip file itself and __MACOSX junk
        if not os.path.isdir(student_dir) or item.startswith("__"):
            continue

        # Extract Name (Assumption: "Name_ID_...")
        parts = item.split('_')
        student_name = parts[0]
        
        # Find Python Files
        py_files = [f for f in os.listdir(student_dir) if f.endswith(".py")]
        
        student_status = {}
        
        if not py_files:
            student_status = {"name": student_name, "has_warning": 0, "score": "0", "status": "No File", "css": "secondary"}
        else:
            # Pick the first one
            target_file = py_files[0]
            warning = f"(Found {len(py_files)} files)" if len(py_files) > 1 else ""
            
            with open(os.path.join(student_dir, target_file), "r", encoding="utf-8", errors="ignore") as f:
                code_content = f.read()
            
            # --- RUN THE GRADER ---
            score, total, results = grade_submission(code_content, assignment_id)
            
            # Calculate Pass/Fail CSS
            row_css = "success" if score == total else ("warning" if score > 0 else "danger")
            
            # Inside the professor_grade loop in app.py:

            student_status = {
                "id": f"student_{i}",  # Unique ID for the HTML collapse target
                "name": student_name,
                "has_warning": len(py_files),  # Lenght of py_files for warning display should be always 1
                "score": f"{score}/{total}",
                "css": row_css,  # "success", "danger", or "warning"
                "code_content": code_content,
                "results": results # The list of test outcomes
            }

        report_data.append(student_status)

    # Cleanup
    shutil.rmtree(temp_dir)

    return templates.TemplateResponse("professor_report.html", {
        "request": request,
        "report": report_data,
        "assignment": ASSIGNMENTS[assignment_id]['title']
    })
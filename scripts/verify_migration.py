import os
import yaml
import asyncio
import httpx
import sys
from colorama import init, Fore, Style

# Initialize colors for terminal
init(autoreset=True)

# --- CONFIGURATION ---
ASSIGNMENTS_DIR = "./grader/assignments"
JOBE_URL = os.getenv("JOBE_URL", "http://localhost:4000/jobe/index.php/restapi/runs")
CONCURRENT_ASSIGNMENTS = 5  # How many assignments to check at the same time

# --- THE MOCK WRAPPER (Must match your app.py exactly) ---
MOCK_WRAPPER = """
import sys
from io import StringIO

class MockInput:
    def __init__(self, input_data):
        self.input_lines = input_data.strip().split('\\n')
        self.line_index = 0

    def mock_input_func(self, prompt=""):
        if prompt:
            print(prompt, end="")
        if self.line_index < len(self.input_lines):
            line = self.input_lines[self.line_index]
            self.line_index += 1
            return line
        raise EOFError("No more input data")

def run_with_mock(code_str, input_str):
    mock = MockInput(input_str)
    global input
    input = mock.mock_input_func
    
    # Capture Stdout
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()
    
    try:
        exec(code_str, globals())
    except Exception as e:
        print(f"Runtime Error: {e}")
    finally:
        sys.stdout = old_stdout
    
    return mystdout.getvalue()
"""

async def run_test_case(client, code, test, time_limit):
    """Runs a single test case against Jobe."""
    
    # Combine Wrapper + Solution + Runner Call
    # We append a small footer to actually invoke the logic
    # Note: In the app we usually wrap differently, but for raw execution 
    # we need to simulate the input injection.
    
    # Actually, Jobe handles stdin automatically if we don't use the Mock Wrapper.
    # BUT, since your assignments use 'input("Prompt")', we DO need the wrapper 
    # to suppress the prompt or handle the input flow if you rely on the app's logic.
    
    # Let's use the EXACT logic the App uses:
    # App logic: full_code = MOCK_WRAPPER + "\n" + code + "\nrun_with_mock(..., input)"
    # Wait, the app wrapper usually redefines 'input'. 
    # Let's trust the logic you implemented in `grade_submission`.
    
    full_code = MOCK_WRAPPER + "\n" + code

    payload = {
        "run_spec": {
            "language_id": "python3",
            "sourcecode": full_code,
            "input": test['input'],
            "parameters": {"cputime": time_limit}
        }
    }

    try:
        resp = await client.post(JOBE_URL, json=payload, timeout=time_limit + 5)
        if resp.status_code != 200:
            return {"status": "ERROR", "msg": f"Jobe Error {resp.status_code}"}
        
        outcome = resp.json()
        
        if outcome['outcome'] == 15: # Success
            actual = outcome['stdout'].strip()
            expected = test['output'].strip()
            
            if actual == expected:
                return {"status": "PASS"}
            else:
                return {
                    "status": "FAIL", 
                    "msg": f"Expected: {expected[:20]}... | Got: {actual[:20]}..."
                }
        else:
            err = outcome.get('stderr') or outcome.get('cmpinfo') or "Runtime Error"
            return {"status": "ERROR", "msg": err.strip()}
            
    except Exception as e:
        return {"status": "CONN_ERR", "msg": str(e)}


async def verify_assignment(sem, folder_name):
    """Checks one assignment folder."""
    async with sem:
        folder_path = os.path.join(ASSIGNMENTS_DIR, folder_name)
        config_path = os.path.join(folder_path, "config.yaml")
        solution_path = os.path.join(folder_path, "solution.py")

        # 1. Validation
        if not os.path.exists(config_path) or not os.path.exists(solution_path):
            return f"{Fore.YELLOW}⚠️  {folder_name}: Missing config.yaml or solution.py"

        # 2. Load Data
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            with open(solution_path, 'r') as f:
                code = f.read()
        except Exception as e:
            return f"{Fore.RED}❌ {folder_name}: File Read Error ({e})"

        tests = config.get('tests', [])
        time_limit = config.get('time_limit', 2)

        if not tests:
            return f"{Fore.YELLOW}⚠️  {folder_name}: No tests defined"

        # 3. Run Tests Parallel
        async with httpx.AsyncClient() as client:
            tasks = [run_test_case(client, code, t, time_limit) for t in tests]
            results = await asyncio.gather(*tasks)

        # 4. Analyze Results
        failed = [r for r in results if r['status'] != 'PASS']
        
        if not failed:
            return f"{Fore.GREEN}✅ {folder_name}: All {len(tests)} tests passed."
        else:
            # Construct detailed error for the first failure
            err_msg = failed[0].get('msg', 'Unknown')
            return f"{Fore.RED}❌ {folder_name}: {len(failed)}/{len(tests)} failed. (First error: {err_msg})"


async def main():
    print(f"{Style.BRIGHT}🚀 Starting Batch Verification on {ASSIGNMENTS_DIR}...")
    
    if not os.path.exists(ASSIGNMENTS_DIR):
        print("Error: Assignments directory not found.")
        return

    # Gather folders
    folders = sorted([f for f in os.listdir(ASSIGNMENTS_DIR) if not f.startswith('.')])
    
    # Semaphore to prevent overwhelming Jobe with 100 assignments * 5 tests = 500 reqs
    sem = asyncio.Semaphore(CONCURRENT_ASSIGNMENTS)
    
    tasks = []
    for folder in folders:
        # Check if it's a directory
        if os.path.isdir(os.path.join(ASSIGNMENTS_DIR, folder)):
            tasks.append(verify_assignment(sem, folder))

    # Run everything
    results = await asyncio.gather(*tasks)

    # Print Report
    print("\n" + "="*40)
    print("FINAL REPORT")
    print("="*40)
    
    passed_count = 0
    failed_count = 0
    
    for line in results:
        print(line)
        if "✅" in line: passed_count += 1
        if "❌" in line: failed_count += 1

    print("-" * 40)
    print(f"Total: {len(results)}")
    print(f"{Fore.GREEN}Passed: {passed_count}")
    
    if failed_count > 0:
        print(f"{Fore.RED}Failed: {failed_count}")
        sys.exit(1)
    else:
        print(f"{Fore.BLUE}Perfect! All reference solutions match the test cases.")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
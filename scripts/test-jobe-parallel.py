# This script assumes you are connected to the running jobe-server Kubernetes Service on localhost port 4000
# to achieve this you can use kubectl port-forward like so:
#   kubectl port-forward -n jobe-web svc/jobe-service 4000:80

import requests
import concurrent.futures
import time
import sys

# --- Configuration ---
JOBE_URL = "http://localhost:4000/jobe/index.php/restapi/runs"
CONCURRENT_STUDENTS = 50   # Start with 50, then try 100
TOTAL_REQUESTS = 200       # Total submissions to simulate
CPU_INTENSIVE_CODE = """
def count_primes(limit):
    count = 0
    for i in range(2, limit):
        is_prime = True
        for j in range(2, int(i ** 0.5) + 1):
            if i % j == 0:
                is_prime = False
                break
        if is_prime:
            count += 1
    return count

print(count_primes(5000)) # Enough work to keep CPU busy for ~100ms
"""

def simulated_student(student_id):
    """
    Simulates one student clicking 'Submit'
    """
    payload = {
        "run_spec": {
            "language_id": "python3",
            "sourcecode": CPU_INTENSIVE_CODE,
            "input": ""
        }
    }
    
    start = time.time()
    try:
        # Send request
        response = requests.post(JOBE_URL, json=payload, timeout=10)
        duration = time.time() - start
        
        if response.status_code == 200:
            result = response.json()
            if result['outcome'] == 15:
                return (True, duration, f"Student {student_id}: ✅ Success ({duration:.2f}s)")
            else:
                return (False, duration, f"Student {student_id}: ⚠️  Jobe Error (Outcome {result['outcome']})")
        elif response.status_code == 503:
            return (False, duration, f"Student {student_id}: ❌ Overload (503 Service Unavailable)")
        else:
            return (False, duration, f"Student {student_id}: ❌ HTTP {response.status_code}")
            
    except Exception as e:
        return (False, 0, f"Student {student_id}: 💥 Connection Failed ({str(e)})")

def run_stress_test():
    print(f"🔥 Starting Stress Test: {CONCURRENT_STUDENTS} concurrent users")
    print(f"🎯 Target URL: {JOBE_URL}")
    print("-" * 50)

    # The ThreadPoolExecutor runs tasks in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_STUDENTS) as executor:
        # Launch all requests effectively at once
        futures = [executor.submit(simulated_student, i) for i in range(TOTAL_REQUESTS)]
        
        success_count = 0
        fail_count = 0
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(futures):
            success, duration, message = future.result()
            print(message)
            if success:
                success_count += 1
            else:
                fail_count += 1

    print("-" * 50)
    print(f"🏁 Test Finished.")
    print(f"✅ Successful Runs: {success_count}")
    print(f"❌ Failed Runs:     {fail_count}")
    
    if fail_count > 0:
        print("\n⚠️  DIAGNOSIS:")
        print("Your Jobe server rejected some connections. This is normal default behavior.")
        print("See the instructions below to tune 'jobe_max_users'.")

if __name__ == "__main__":
    run_stress_test()
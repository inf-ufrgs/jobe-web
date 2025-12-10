# This script assumes you are connected to the running jobe-server Kubernetes Service on localhost port 4000
# to achieve this you can use kubectl port-forward like so:
#   kubectl port-forward -n jobe-web svc/jobe-service 4000:80

import requests
import time

# Configuration
JOBE_URL = "http://localhost:4000/jobe/index.php/restapi/runs"

# 1. The Code to Run on the Server (CPU Intensive)
# This code counts prime numbers up to N.
# It's inefficient enough to generate measurable CPU load.
source_code = """
import sys

def is_prime(num):
    if num < 2:
        return False
    for i in range(2, int(num ** 0.5) + 1):
        if num % i == 0:
            return False
    return True

def count_primes(limit):
    count = 0
    for i in range(limit):
        if is_prime(i):
            count += 1
    return count

# Read input from Stdin
try:
    data = sys.stdin.read().strip()
    limit = int(data)
    result = count_primes(limit)
    print(result)
except Exception as e:
    print(f"Error: {e}")
"""

# 2. Test Cases (Input vs Expected Output)
# Calculating primes up to 100,000 takes a split second but is noticeable work.
test_cases = [
    {"input": "100",    "expected": "25",   "desc": "Warmup (0-100)"},
    {"input": "10000",  "expected": "1229", "desc": "Medium Load (0-10k)"},
    {"input": "100000", "expected": "9592", "desc": "Heavy Load (0-100k)"},
    {"input": "1000000", "expected": "78498", "desc": "Very Heavy Load (0-1M)"}
]

def run_test():
    print(f"🚀 Connecting to Jobe at {JOBE_URL}...\n")

    for test in test_cases:
        print(f"--- Running: {test['desc']} ---")
        
        payload = {
            "run_spec": {
                "language_id": "python3",
                "sourcecode": source_code,
                "input": test['input'],
                "parameters": {
                    "cputime": 30
                },
            }
        }

        try:
            start_time = time.time()
            response = requests.post(JOBE_URL, json=payload)
            end_time = time.time()
            
            # Network + Processing Latency
            latency = (end_time - start_time) * 1000 

            if response.status_code != 200:
                print(f"❌ HTTP Error: {response.status_code}")
                continue

            result = response.json()
            
            # Check Jobe Execution Status (15 = Success)
            outcome = result.get('outcome')
            if outcome != 15:
                print(f"⚠️ Execution Failed (Outcome {outcome})")
                print(f"Compiler/Runtime Output: {result.get('cmpinfo')}")
                continue

            # Check Logic
            actual_output = result.get('stdout', '').strip()
            expected_output = test['expected']
            
            if actual_output == expected_output:
                print(f"✅ PASSED")
                print(f"   Input: {test['input']} -> Output: {actual_output}")
                print(f"   Total Time (Roundtrip): {latency:.2f} ms")
            else:
                print(f"❌ FAILED")
                print(f"   Expected: {expected_output}, Got: {actual_output}")

        except Exception as e:
            print(f"❌ Connection Error: {e}")
            break
        
        print("_" * 50) # Line between tests

if __name__ == "__main__":
    run_test()
"""
sec-quest/server/tasks.py

Defines the 3 PR review tasks (easy → medium → hard).
Each task contains:
  - A code diff with deliberately planted bugs
  - A bug_manifest: the ground truth of where bugs are and what they are
  - A task_description explaining the PR's intent
"""

# ---------------------------------------------------------------------------
# TASK 1 — EASY: "Rookie Review"
# ~30 lines of Python. Two obvious bugs: hardcoded password + off-by-one.
# ---------------------------------------------------------------------------

TASK_EASY = {
    "task_id": "easy",
    "task_description": (
        "This PR adds a utility function to hash user passwords before storing them "
        "in the database, and a helper to find items in a list. Review for correctness and security."
    ),
    "diff": """\
--- a/utils.py
+++ b/utils.py
@@ -0,0 +1,34 @@
+import hashlib
+import os
+
+# Database connection configuration
+DB_PASSWORD = "supersecret123"   # line 5
+DB_HOST = "localhost"
+DB_PORT = 5432
+
+
+def hash_password(password: str) -> str:
+    \"\"\"Hash a user password for secure storage.\"\"\"
+    salt = os.urandom(16)
+    hashed = hashlib.sha256((password + str(salt)).encode()).hexdigest()
+    return hashed
+
+
+def find_first_above_threshold(values: list, threshold: float) -> int:
+    \"\"\"
+    Return the index of the first value in `values` that exceeds `threshold`.
+    Returns -1 if none found.
+    \"\"\"
+    for i in range(1, len(values)):   # line 22 — off-by-one: should start at 0
+        if values[i] > threshold:
+            return i
+    return -1
+
+
+def get_connection_string() -> str:
+    \"\"\"Build the DB connection string.\"\"\"
+    return f"postgresql://{DB_HOST}:{DB_PORT}/mydb?password={DB_PASSWORD}"
+
+
+def sanitize_input(text: str) -> str:
+    \"\"\"Remove leading/trailing whitespace.\"\"\"
+    return text.strip()
""",
    "bug_manifest": [
        {
            "bug_id": "easy_1",
            "line_number": 5,
            "line_range": [5, 5],
            "category": "security",
            "severity": "critical",
            "description": "Hardcoded database password in source code",
        },
        {
            "bug_id": "easy_2",
            "line_number": 22,
            "line_range": [21, 23],
            "category": "logic",
            "severity": "major",
            "description": "Off-by-one error: loop starts at index 1, skipping index 0",
        },
    ],
}


# ---------------------------------------------------------------------------
# TASK 2 — MEDIUM: "Mid-Level Review"
# ~80 lines. Flask API. SQL injection, missing auth check,
# N+1 query, wrong HTTP status code.
# ---------------------------------------------------------------------------

TASK_MEDIUM = {
    "task_id": "medium",
    "task_description": (
        "This PR adds a Flask REST API endpoint to search for users by name and "
        "retrieve their orders. Review the endpoint for security, correctness, and performance."
    ),
    "diff": """\
--- a/api/users.py
+++ b/api/users.py
@@ -0,0 +1,78 @@
+from flask import Flask, request, jsonify
+import sqlite3
+
+app = Flask(__name__)
+
+
+def get_db():
+    conn = sqlite3.connect("app.db")
+    conn.row_factory = sqlite3.Row
+    return conn
+
+
+def is_authenticated(req):
+    \"\"\"Check if request has a valid API token.\"\"\"
+    token = req.headers.get("Authorization")
+    return token == "Bearer valid-token"
+
+
+@app.route("/users/search", methods=["GET"])
+def search_users():
+    # No authentication check here   # line 21
+    name = request.args.get("name", "")
+    db = get_db()
+    cursor = db.cursor()
+
+    # Build query with user input directly   # line 26
+    query = f"SELECT * FROM users WHERE name LIKE '%{name}%'"   # line 27 — SQL injection
+    cursor.execute(query)
+    users = cursor.fetchall()
+
+    result = []
+    for user in users:
+        user_data = dict(user)
+
+        # Fetch orders for each user individually inside the loop   # line 35
+        order_cursor = db.cursor()
+        order_cursor.execute(
+            "SELECT * FROM orders WHERE user_id = ?", (user["id"],)   # line 38 — N+1 query
+        )
+        user_data["orders"] = [dict(o) for o in order_cursor.fetchall()]
+        result.append(user_data)
+
+    return jsonify(result), 200
+
+
+@app.route("/users/<int:user_id>", methods=["DELETE"])
+def delete_user(user_id):
+    \"\"\"Delete a user by ID. Requires authentication.\"\"\"
+    if not is_authenticated(request):
+        return jsonify({"error": "Unauthorized"}), 401
+
+    db = get_db()
+    cursor = db.cursor()
+    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
+    db.commit()
+
+    if cursor.rowcount == 0:
+        return jsonify({"error": "User not found"}), 200   # line 57 — wrong status code, should be 404
+
+    return jsonify({"message": "Deleted"}), 200
+
+
+@app.route("/users/<int:user_id>/profile", methods=["GET"])
+def get_profile(user_id):
+    \"\"\"Get a user profile. Requires authentication.\"\"\"
+    if not is_authenticated(request):
+        return jsonify({"error": "Unauthorized"}), 401
+
+    db = get_db()
+    cursor = db.cursor()
+    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
+    user = cursor.fetchone()
+
+    if not user:
+        return jsonify({"error": "Not found"}), 404
+
+    return jsonify(dict(user)), 200
+
+
+if __name__ == "__main__":
+    app.run(debug=True)
""",
    "bug_manifest": [
        {
            "bug_id": "medium_1",
            "line_number": 21,
            "line_range": [20, 22],
            "category": "security",
            "severity": "critical",
            "description": "Missing authentication check on /users/search endpoint",
        },
        {
            "bug_id": "medium_2",
            "line_number": 27,
            "line_range": [26, 28],
            "category": "security",
            "severity": "critical",
            "description": "SQL injection via f-string interpolation of user input into query",
        },
        {
            "bug_id": "medium_3",
            "line_number": 38,
            "line_range": [35, 40],
            "category": "performance",
            "severity": "major",
            "description": "N+1 query: fetching orders per user inside a loop instead of a single JOIN",
        },
        {
            "bug_id": "medium_4",
            "line_number": 57,
            "line_range": [56, 58],
            "category": "logic",
            "severity": "major",
            "description": "Wrong HTTP status code: returns 200 when user is not found; should be 404",
        },
    ],
}


# ---------------------------------------------------------------------------
# TASK 3 — HARD: "Staff Engineer Review"
# ~130 lines. Async service. Race condition, JWT bypass, TOCTOU,
# resource leak, silent exception swallow.
# ---------------------------------------------------------------------------

TASK_HARD = {
    "task_id": "hard",
    "task_description": (
        "This PR implements an async token-based file-processing service. "
        "It handles JWT authentication, concurrent job management, and file uploads. "
        "Review thoroughly for security vulnerabilities, concurrency bugs, and error handling."
    ),
    "diff": """\
--- a/services/processor.py
+++ b/services/processor.py
@@ -0,0 +1,132 @@
+import asyncio
+import os
+import jwt
+import json
+from datetime import datetime, timedelta
+
+SECRET_KEY = os.getenv("JWT_SECRET", "fallback-secret")
+JOBS = {}          # Shared dict — no lock   # line 9
+
+
+async def process_file(filepath: str, job_id: str):
+    \"\"\"Process a file asynchronously and store the result.\"\"\"
+    await asyncio.sleep(0.1)  # simulate IO
+    with open(filepath, "r") as f:
+        content = f.read()
+    JOBS[job_id] = {"status": "done", "result": content[:100]}
+
+
+async def submit_job(filepath: str) -> str:
+    \"\"\"Submit a new processing job. Returns the job_id.\"\"\"
+    import uuid
+    job_id = str(uuid.uuid4())
+    JOBS[job_id] = {"status": "pending"}
+    # asyncio.create_task fires process_file concurrently
+    # JOBS dict is mutated from multiple coroutines without a lock  # line 25 — race condition
+    asyncio.create_task(process_file(filepath, job_id))
+    return job_id
+
+
+def validate_token(token: str) -> dict:
+    \"\"\"
+    Validate a JWT and return its payload.
+    \"\"\"
+    try:
+        payload = jwt.decode(
+            token,
+            SECRET_KEY,
+            algorithms=["HS256", "none"],   # line 37 — 'none' algorithm allows unsigned tokens
+        )
+        return payload
+    except jwt.ExpiredSignatureError:
+        raise ValueError("Token expired")
+    except Exception:
+        return {}   # line 42 — silently swallows all other JWT errors, returns empty dict
+
+
+def get_user_config(username: str) -> dict:
+    \"\"\"Load a user's config from disk.\"\"\"
+    config_path = f"configs/{username}.json"
+
+    # TOCTOU: check then act without atomic operation   # line 49
+    if os.path.exists(config_path):               # line 50 — check
+        with open(config_path, "r") as f:         # line 51 — act (race window here)
+            return json.load(f)
+    return {}
+
+
+def process_upload(upload_path: str) -> str:
+    \"\"\"Read an uploaded file, process it, return a summary.\"\"\"
+    f = open(upload_path, "r")   # line 57 — resource leak: file never closed if exception
+    content = f.read()
+    # ... process content ...
+    lines = content.splitlines()
+    summary = f"Lines: {len(lines)}, Chars: {len(content)}"
+    f.close()   # not reached if an exception is raised above
+    return summary
+
+
+async def batch_process(filepaths: list) -> list:
+    \"\"\"Process multiple files concurrently.\"\"\"
+    tasks = [submit_job(fp) for fp in filepaths]
+    job_ids = await asyncio.gather(*tasks)
+    return list(job_ids)
+
+
+def get_job_status(job_id: str) -> dict:
+    \"\"\"Get the current status of a job.\"\"\"
+    return JOBS.get(job_id, {"status": "not_found"})
+
+
+def rotate_secret(new_secret: str):
+    \"\"\"Rotate the JWT signing secret.\"\"\"
+    global SECRET_KEY
+    SECRET_KEY = new_secret
+
+
+async def healthcheck() -> dict:
+    \"\"\"Return service health info.\"\"\"
+    return {
+        "status": "ok",
+        "jobs_in_memory": len(JOBS),
+        "timestamp": datetime.utcnow().isoformat(),
+    }
""",
    "bug_manifest": [
        {
            "bug_id": "hard_1",
            "line_number": 25,
            "line_range": [9, 26],
            "category": "race_condition",
            "severity": "critical",
            "description": (
                "Race condition: JOBS dict is mutated concurrently from multiple coroutines "
                "without an asyncio.Lock, leading to lost updates and corrupted state"
            ),
        },
        {
            "bug_id": "hard_2",
            "line_number": 37,
            "line_range": [36, 38],
            "category": "security",
            "severity": "critical",
            "description": (
                "JWT 'none' algorithm accepted: allows attackers to forge unsigned tokens "
                "by setting alg=none in the header, bypassing signature verification"
            ),
        },
        {
            "bug_id": "hard_3",
            "line_number": 42,
            "line_range": [41, 43],
            "category": "logic",
            "severity": "major",
            "description": (
                "Silent exception swallow: all JWT errors except ExpiredSignatureError "
                "are caught and return an empty dict, hiding invalid/tampered tokens"
            ),
        },
        {
            "bug_id": "hard_4",
            "line_number": 50,
            "line_range": [49, 52],
            "category": "security",
            "severity": "major",
            "description": (
                "TOCTOU vulnerability: os.path.exists() check and open() are not atomic; "
                "a file could be replaced between the check and the read"
            ),
        },
        {
            "bug_id": "hard_5",
            "line_number": 57,
            "line_range": [57, 64],
            "category": "performance",
            "severity": "major",
            "description": (
                "Resource leak: file handle opened without a context manager; "
                "if an exception occurs before f.close(), the file descriptor is never released"
            ),
        },
    ],
}


ALL_TASKS = {
    "easy": TASK_EASY,
    "medium": TASK_MEDIUM,
    "hard": TASK_HARD,
}
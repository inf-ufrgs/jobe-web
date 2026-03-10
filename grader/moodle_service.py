"""
Moodle REST API service module.

Encapsulates all interaction with the Moodle Web Services API.
The MOODLE_TOKEN is always passed as a function parameter and is
never stored, logged, or persisted in any way.
"""

import os
import re
import logging
import requests
from datetime import datetime

logger = logging.getLogger("grader")

MOODLE_BASE_URL = "https://moodle.ufrgs.br/webservice/rest/server.php"


def call_moodle_api(token: str, function_name: str, params: dict = None) -> dict | list:
    """
    Generic REST call to the Moodle Web Services API.

    Args:
        token: The user's Moodle web-service token (never stored).
        function_name: The Moodle WS function to call.
        params: Additional parameters for the function.

    Returns:
        Parsed JSON response (dict or list).

    Raises:
        MoodleAPIError: On any Moodle-level or HTTP error.
    """
    data = {
        "wstoken": token,
        "wsfunction": function_name,
        "moodlewsrestformat": "json",
        **(params or {}),
    }
    try:
        response = requests.post(MOODLE_BASE_URL, data=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict) and "exception" in result:
            raise MoodleAPIError(result.get("message", "Unknown Moodle error"))
        return result
    except requests.RequestException as e:
        raise MoodleAPIError(f"HTTP error communicating with Moodle: {e}") from e


class MoodleAPIError(Exception):
    """Raised when a Moodle API call fails."""
    pass


def _sanitize_filename(name: str) -> str:
    """Remove characters that are invalid in file/folder names."""
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def list_course_assignments(token: str, course_id: int) -> list[dict]:
    """
    List all assignments for a given Moodle course.

    Returns a list of dicts:
        [{id, name, duedate, duedate_formatted, submissions_count}, ...]
    """
    result = call_moodle_api(token, "mod_assign_get_assignments", {
        "courseids[0]": course_id,
    })

    if not isinstance(result, dict) or "courses" not in result:
        raise MoodleAPIError("Unexpected response format from mod_assign_get_assignments")

    assignments = []
    for course in result["courses"]:
        for assign in course.get("assignments", []):
            # Get submission stats
            submissions_count = 0
            try:
                stats = call_moodle_api(token, "mod_assign_get_submission_status", {
                    "assignid": assign["id"],
                })
                if isinstance(stats, dict) and "gradingsummary" in stats:
                    submissions_count = stats["gradingsummary"].get("submissionssubmittedcount", 0)
            except MoodleAPIError:
                pass  # Stats are optional; skip if unavailable

            # Format due date
            duedate = assign.get("duedate", 0)
            duedate_formatted = (
                datetime.fromtimestamp(duedate).strftime("%Y-%m-%d %H:%M")
                if duedate
                else "No deadline"
            )

            assignments.append({
                "id": assign["id"],
                "name": assign.get("name", f"Assignment {assign['id']}"),
                "duedate": duedate,
                "duedate_formatted": duedate_formatted,
                "submissions_count": submissions_count,
            })

    return sorted(assignments, key=lambda a: a["duedate"])


def download_assignment_submissions(
    token: str,
    assign_id: int,
    course_id: int,
    dest_dir: str,
) -> int:
    """
    Download all submitted files for a Moodle assignment into dest_dir.

    Creates subfolders named like Moodle's ZIP export:
        StudentName_UserID_assignsubmission_file_/filename.py

    Args:
        token: Moodle web-service token.
        assign_id: The Moodle assignment ID.
        course_id: The Moodle course ID (needed to map user IDs to names).
        dest_dir: Local directory to write files into.

    Returns:
        Number of files successfully downloaded.
    """
    # 1. Build user ID → full name map
    users_list = call_moodle_api(token, "core_enrol_get_enrolled_users", {
        "courseid": course_id,
    })
    if not isinstance(users_list, list):
        raise MoodleAPIError("Failed to fetch enrolled users")

    user_map = {u["id"]: u["fullname"] for u in users_list}

    # 2. Fetch submissions
    res = call_moodle_api(token, "mod_assign_get_submissions", {
        "assignmentids[0]": assign_id,
    })
    if not isinstance(res, dict) or "assignments" not in res:
        raise MoodleAPIError("Failed to fetch submissions")

    submissions = res["assignments"][0].get("submissions", [])
    if not submissions:
        return 0

    # 3. Download each submission's files
    download_count = 0
    for sub in submissions:
        user_id = sub.get("userid")
        user_name = _sanitize_filename(user_map.get(user_id, f"User_{user_id}"))

        for plugin in sub.get("plugins", []):
            if plugin.get("type") != "file":
                continue
            for filearea in plugin.get("fileareas", []):
                for f in filearea.get("files", []):
                    filename = f.get("filename", "unknown")
                    file_url = f.get("fileurl")
                    if not file_url:
                        continue

                    # Create a subfolder matching Moodle ZIP naming:
                    # StudentName_UserID_assignsubmission_file_
                    student_folder = f"{user_name}_{user_id}_assignsubmission_file_"
                    student_dir = os.path.join(dest_dir, student_folder)
                    os.makedirs(student_dir, exist_ok=True)

                    # Download the file
                    download_url = f"{file_url}?token={token}"
                    try:
                        r = requests.get(download_url, stream=True, timeout=60)
                        r.raise_for_status()
                        file_path = os.path.join(student_dir, filename)
                        with open(file_path, "wb") as out:
                            for chunk in r.iter_content(chunk_size=8192):
                                out.write(chunk)
                        download_count += 1
                    except requests.RequestException as e:
                        logger.warning(f"Failed to download file for user {user_id}: {e}")

    return download_count

import requests

MOODLE_URL = "https://moodle.htw-berlin.de/webservice/rest/server.php"
MOODLE_TOKEN = "d31077c2fd0d1c9d0bbd3adc81650e8b"


def get_users(token, email):
    params = {
        "wstoken": token,
        "wsfunction": "core_user_get_users",
        "moodlewsrestformat": "json",
        "criteria[0][key]": "s0541972@htw-berlin.de",
        "criteria[0][value]": email
    }
    response = requests.get(MOODLE_URL, params=params)
    response.raise_for_status()
    return response.json()


def get_users_by_field(token, field, value):
    params = {
        "wstoken": token,
        "wsfunction": "core_user_get_users_by_field",
        "moodlewsrestformat": "json",
        "field": field,
        "values[0]": value
    }
    response = requests.get(MOODLE_URL, params=params)
    response.raise_for_status()
    return response.json()


def get_user_courses(token, user_id):
    params = {
        "wstoken": token,
        "wsfunction": "core_enrol_get_users_courses",
        "moodlewsrestformat": "json",
        "userid": user_id
    }
    response = requests.get(MOODLE_URL, params=params)
    response.raise_for_status()
    return response.json()


def get_course_contents(token, course_id):
    params = {
        "wstoken": token,
        "wsfunction": "core_course_get_contents",
        "moodlewsrestformat": "json",
        "courseid": course_id
    }
    response = requests.get(MOODLE_URL, params=params)
    response.raise_for_status()
    return response.json()


def get_grades(token, course_id, user_id):
    params = {
        "wstoken": token,
        "wsfunction": "gradereport_user_get_grade_items",
        "moodlewsrestformat": "json",
        "courseid": course_id,
        "userid": user_id
    }
    response = requests.get(MOODLE_URL, params=params)
    response.raise_for_status()
    return response.json()

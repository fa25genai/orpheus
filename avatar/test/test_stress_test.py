import subprocess
import uuid
import json

API_URL = "http://localhost:9000/v1/video/generate"

LONG_VOICE_TRACK = """Welcome my students!
Today we are going to learn how to think critically and creatively.
Please pay attention to the slides and take notes.
Remember to ask questions whenever you feel confused.
We will explore practical examples and real-world scenarios.
Keep your mind open and stay curious about new ideas.
Your active participation makes this session more valuable.
Feel free to experiment and test your knowledge.
At the end we will have a Q&A session to clarify doubts.
Let's begin the exciting journey of learning now!
"""

def make_payload(slide_num: int) -> str:
    data = {
        "voiceTrack": LONG_VOICE_TRACK,
        "slideNumber": slide_num,
        "promptId": str(uuid.uuid4()),
        "courseId": "course_123",
        "userProfile": {
            "id": f"user_{slide_num:03d}",
            "role": "student",
            "language": "english",
            "preferences": {
                "answerLength": "medium",
                "languageLevel": "advanced",
                "expertiseLevel": "intermediate",
                "includePictures": "few"
            },
            "enrolled_courses": ["course_123"]
        }
    }
    # json.dumps handles all quoting and escaping for you
    return json.dumps(data)

def stress_test(request_count=20):
    print(f"Launching {request_count} requests to {API_URL}...")
    for i in range(request_count):
        payload = make_payload(i)
        cmd = [
            "curl", "-s", "-X", "POST",
            API_URL,
            "-H", "Content-Type: application/json",
            "-d", payload
        ]
        print(f"[{i+1}/{request_count}] Sending request...")
        subprocess.Popen(cmd)  # fire and forget
    print("All requests launched.")

if __name__ == "__main__":
    # adjust the count for heavier stress
    stress_test(request_count=50)

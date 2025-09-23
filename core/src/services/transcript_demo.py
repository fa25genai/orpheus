import json
from core.src.services.voice_text_generation import (
    TranscriptFromRawRequest,
    map_user_profile_to_persona,
    map_di_raw_to_canonical,
    map_slides_raw_to_canonical,
    raw_profile_dict,
    generate_slide_messages
)

# Example data (from your curl command)
data = {
    "userProfile": {
        "id": "user",
        "role": "student",
        "language": "english",
        "preferences": {
            "answerLength": "medium",
            "languageLevel": "intermediate",
            "expertiseLevel": "beginner",
            "includePictures": "few"
        },
        "enrolledCourses": []
    },
    "diTeamMeta": {
        "courseId": "string",
        "query": "string"
    },
    "diTeamContent": {
        "content": [
            "string"
        ],
        "images": "string"
    },
    "slidesTeamScript": {
        "courseId": "string",
        "lectureId": "string",
        "lectureScript": "string",
        "assets": [
            {
                "name": "string",
                "assetDesc": "string",
                "mimetype": "string",
                "data": "string"
            }
        ]
    },
    "slidesTeamDeck": {
        "title": "string",
        "slides": [
            {
                "title": "string",
                "content": "string"
            }
        ]
    },
    "lectureId": "string"
}

# Convert dicts to Pydantic models
raw_req = TranscriptFromRawRequest(**data)
persona = map_user_profile_to_persona(raw_req.userProfile)
raw_profile = raw_profile_dict(raw_req.userProfile)
di_data = map_di_raw_to_canonical(raw_req.diTeamContent)
slides = map_slides_raw_to_canonical(raw_req.slidesTeamDeck)

slide_messages = generate_slide_messages(
    di_data=di_data,
    slides_data=slides,
    user_profile_raw=raw_profile
)

result = {
    "lectureId": raw_req.lectureId or (raw_req.slidesTeamScript.lectureId if raw_req.slidesTeamScript and raw_req.slidesTeamScript.lectureId else ""),
    "slideMessages": slide_messages,
    "userProfile": raw_profile
}

print(json.dumps(result, indent=2))

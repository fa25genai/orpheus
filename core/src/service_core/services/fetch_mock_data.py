from uuid import uuid4
from service_core.models.user_profile_preferences import UserProfilePreferences
from service_core.models.user_profile import UserProfile


demo_user = UserProfile(
        id=uuid4(),
        role="student",
        language="english", 
        preferences=UserProfilePreferences(
            answer_length="medium",
            language_level="intermediate",
            expertise_level="beginner",
            include_pictures="few"
        ),
        enrolled_courses=["SE001","cs001"]
    )


retrieved_content = [
        {
            "Question": "Definition of for loop",
            "retrieved_content": [
                "A for loop is a control flow statement for specifying iteration, which allows code to be executed repeatedly. It is typically used to iterate over a sequence (like a list, tuple, or string) or a range of numbers."
            ],
            "retrieved_images": [
                {"image": "abcd.jpg", "description": "For loop example"}
            ]
        },
        {
            "Question": "Worked example of for loop",
            "retrieved_content": [
                "In Python, a for loop is often used with the range() function to execute a block of code a specific number of times. For example, the code 'for i in range(5): print(\"Hello!\")' will run the print statement five times. In each iteration, the code inside the loop is executed. After the fifth time, the loop concludes and the program continues on to the next line."
            ],
            "retrieved_images": []
        }
    ]
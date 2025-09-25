from uuid import uuid4
from service_core.models.user_profile_preferences import UserProfilePreferences
from service_core.models.user_profile import UserProfile
from service_core.services.services_models.slides import SlidesEnvelope
from service_core.services.services_models.voice_track import VoiceTrackResponse

def create_demo_user():
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
    return demo_user

def create_demoretrieved_content():
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
    return retrieved_content

def create_context_mock(courseId, promptId, lectureScript, user: UserProfile):
    mock = {
        "courseId": courseId,
        "promptId": str(promptId),
        "lectureScript": lectureScript,
        "user": {},
        "assets": [
            {
                "name": "cat.jpg",
                "assetDescription": "the image of a cat",
                "mimeType": "image/jpeg",
                "data": "data:image/jpeg;base64,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"
            }
        ]
    }
    print("Lecture script sent")
    return mock




def create_demo_slides():
    slide_bullets = SlidesEnvelope(
        promptId=str(uuid4()),
        status="IN_PROGRESS",
        createdAt="2025-09-23T11:22:04.876434",
        structure={
            "pages": [
                {
                    "content": "For-Loops: Repeating Actions in Programming"
                },
                {
                    "content": "Repetitive Tasks in Real Life: The Push-up Example. Doing push-ups for exercise - repeating the same action multiple times."
                },
                {
                    "content": "Repetition in Computer Programs. Performing an action for each user in a system. The need to repeat the same action a certain amount of times."
                },
                {
                    "content": "Example: A Java For-Loop\\n\\n`for (int i = 0; i < 10; i++) {\\n    System.out.println(i);\\n}`"
                },
                {
                    "content": "What output may this program produce? Take a moment to think."
                },
                {
                    "content": "Output:\\n0\\n1\\n2\\n3\\n4\\n5\\n6\\n7\\n8\\n9"
                },
                {
                    "content": "Understanding the Output: It starts at 0 and ends at 9."
                },
                {
                    "content": "Section: Elements of a For-Loop"
                },
                {
                    "content": "Element 1: Initialization\\n\\nThis is the value, which is used for the first iteration of the loop."
                },
                {
                    "content": "Element 2: Condition\\n\\nAs long as this condition holds, we are repeating the loop. This condition is also checked before the first iteration, so the loop will not be entered, if it is initially false."
                },
                {
                    "content": "Element 3: Modification\\n\\nThis alters the state of the variable, so we eventually get to a terminating state."
                },
                {
                    "content": "Advantages of For-Loops:\\n- Reduction of code\\n- Concise syntax for counting\\n- Versatile usages"
                },
                {
                    "content": "Potential Uses of For-Loops:\\n- Counting\\n- Iterating over an array\\n- Periodically performing a specific action"
                },
                {
                    "content": "Thank you!"
                }
            ]
        }
    )
    return slide_bullets

def create_demo_voice_track():
    voice_track_response = VoiceTrackResponse(
        promptId=create_demo_slides().promptId,
        courseId="cs001",
        slideMessages=[
            "Willkommen zur Vorlesung über For-Loops! Wir werden heute lernen, wie man Aktionen in Programmen wiederholt – ähnlich wie beim Wiederholen von Liegestützen beim Training. For-Loops ermöglichen es uns, Code effizienter und übersichtlicher zu gestalten.",
            "Denken Sie an Liegestütze: Wir wiederholen eine Aktion so lange, bis ein Ziel erreicht ist. Dieses Prinzip nutzen wir auch in Programmen, um Aufgaben effizient zu automatisieren.",
            "Stellen Sie sich vor, Sie müssen eine Aktion für jeden Benutzer in einem System ausführen. Oder eine Aufgabe wiederholt eine bestimmte Anzahl von Malen erledigen. Genau das ermöglicht uns ein For-Loop – die Wiederholung von Aktionen im Code.",
            "Hier sehen Sie ein Beispiel für einen For-Loop in Java: `for (int i = 0; i < 10; i++) { System.out.println(i); }`. Dieser Loop startet bei 0 und wiederholt die Aktion, bis i den Wert 9 erreicht.",
            "Was glauben Sie, welche Ausgabe dieses Programm erzeugt? Nehmen Sie sich einen Moment Zeit zum Nachdenken.",
            "Die Ausgabe des Programms ist: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9. Der Loop beginnt bei 0 und endet bei 9, da die Bedingung i < 10 ist.",
            "Lassen Sie uns die Ausgabe genauer betrachten: Der Loop startet bei 0 und endet bei 9. Das bedeutet, dass die Aktion genau zehnmal ausgeführt wird.",
            "Kommen wir nun zu den Elementen eines For-Loops. Ein For-Loop besteht aus drei Hauptbestandteilen: Initialisierung, Bedingung und Modifikation.",
            "Das erste Element ist die Initialisierung. Hier wird der Startwert festgelegt, der für die erste Iteration des Loops verwendet wird.",
            "Das zweite Element ist die Bedingung. Solange  diese Bedingung wahr ist, wird der Loop wiederholt. Diese Bedingung wird auch vor der ersten Iteration überprüft.",
            "Das dritte Element ist die Modifikation. Hier wird der Wert verändert, damit wir schließlich zu einem Endzustand gelangen.",
            "For-Loops bieten viele Vorteile: Sie reduzieren den Codeumfang, bieten eine prägnante Syntax zum Zählen und sind vielseitig einsetzbar.",
            "For-Loops können für verschiedene Zwecke verwendet werden: zum Zählen, zum Durchlaufen eines Arrays oder zum periodischen Ausführen einer bestimmten Aktion.",
            "Vielen Dank für Ihre Aufmerksamkeit!"
        ],
        userProfile=create_demo_user().to_dict(),
        metadata=""
    )
    return voice_track_response
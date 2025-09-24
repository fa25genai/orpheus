from uuid import uuid4
from service_core.models.user_profile_preferences import UserProfilePreferences
from service_core.models.user_profile import UserProfile
from service_core.services.services_models.slides import SlidesEnvelope
from service_core.services.services_models.voice_track import VoiceTrackResponse


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


slide_bullets = SlidesEnvelope(
    lectureId=str(uuid4()),
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

voice_track_response = VoiceTrackResponse(
    lectureId=slide_bullets.lectureId,
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
    userProfile=demo_user.to_dict(),
    metadata=""
)
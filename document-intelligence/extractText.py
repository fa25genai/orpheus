
import ollama
from pdf2image import convert_from_path
from PIL import Image
import os
import io
from dotenv import load_dotenv  # Für .env-Unterstützung

load_dotenv()
api_key = os.getenv("KEY")

# Create a custom client with the specific URL and the API key in the headers
client = ollama.Client(
    host='https://gpu.aet.cit.tum.de/ollama',
    headers={'Authorization': f'Bearer {api_key}'}
)
# --- CORE PROCESSING FUNCTION ---
def createTextFromSingleSlide(image: Image.Image) -> str:
    # 1. Convert PIL Image object to raw bytes data
    byte_arr = io.BytesIO()
    # Save the image to the in-memory buffer as a common format like JPEG or PNG
    # PNG is lossless and generally good for slides.
    image.save(byte_arr, format='PNG') 
    image_bytes = byte_arr.getvalue()

    try:
        response = client.chat(
            model='gemma3:27b',
            messages=[
                {
                    'role': 'user',
                    'content': """Given the image of a single slide, extract all text and formulas.
                                    Consolidate the extracted content into a single, continuous string.
                                    Do not include any formatting, markdown, or commentary.
                                    Provide ONLY the raw, extracted text.""",
                    # 2. Pass the raw byte data instead of the PIL object
                    'images':[image_bytes] 
                },
            ],
        )
        return response['message']['content'] 
    except ollama.RequestError as e:
        print(f"Error: {e.error}")
        if e.status_code == 401:
            print("Authentication failed. Please check your API key.")
        else:
            print(f"An error occurred with status code {e.status_code}.")
    return "" # Ensure an empty string is returned on error


# --- PDF PROCESSING FUNCTION ---
def createTextFromSlides(pdf_path: str) -> list[str]:
    try:
        pages = convert_from_path(pdf_path, 200)
        print("successfully converted images")
    except Exception as e:
        print(f"Error converting PDF to images. Ensure Poppler is installed and the path is correct.")
        print(f"Details: {e}")
        return []
    
    texts = []
    
    for i, page in enumerate(pages):
        slide_text_block = f"page{i+1}\n"
        extracted_text = createTextFromSingleSlide(page)
        slide_text_block += extracted_text + '\n\n'
        texts.append(slide_text_block)
    saveTextsToTxt(texts,"lectureSlides/out.txt")
    #return may be unnecessary
    return texts


def saveTextsToTxt(texts, base_filename="output.txt"):
    """
    Saves a string to a file, incrementing a counter in the name if the file exists.
    e.g., output.txt, output_1.txt, output_2.txt
    """
    # 1. Separate the name and extension
    str = ""
    for s in texts:
        str +=s
    name, ext = os.path.splitext(base_filename)
    
    # 2. Start with the base filename
    filename = base_filename
    counter = 1

    # 3. Loop until a non-existent filename is found
    while os.path.exists(filename):
        # Construct the new filename (e.g., output_1.txt)
        filename = f"{name}_{counter}{ext}"
        counter += 1

    # 4. Save the string to the unique filename
    try:
        with open(filename, 'w') as file:
            file.write(str)
    except IOError as e:
        print(f"An error occurred while writing to the file: {e}")
        


# --- EXECUTION ---
# pdf_path bleibt wie gehabt
#pdf_path = "lectureSlides/lecture3.pdf"

#print(createTextFromSlides(pdf_path))
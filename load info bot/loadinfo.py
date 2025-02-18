import telebot
import requests
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
from io import BytesIO

# Set paths for OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Program Files\poppler\poppler-24.08.0\Library\bin"

# Replace with actual tokens
BOT_TOKEN = "7000898266:AAGOuOJVGZ5zkvd_wgtWZWrnCE7TNgjdxDM"
GEMINI_API_KEY = "AIzaSyCvzwtw0D8VPfjD9pnsczuMHaUAWlgILSg"

bot = telebot.TeleBot(BOT_TOKEN)
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

# Function to extract text (OCR for non-selectable PDFs)
def extract_text_from_pdf(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        text = ""

        # Try normal text extraction first
        for page in doc:
            text += page.get_text("text") + "\n"

        # If no text found, use OCR
        if not text.strip():
            images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)
            for img in images:
                text += pytesseract.image_to_string(img) + "\n"

        return text.strip() if text.strip() else "No readable text found."

    except Exception as e:
        return f"⚠️ Error extracting text: {str(e)}"

# Function to call Gemini AI
def get_load_info_from_gemini(text):
    prompt = f"""
    Extract the load details and format them exactly like this:

    Format:
[Broker's Company name]

Load# [Load Number not MC]
PU: [Pickup Reference Number]

PU: [Facility Name]
[Street Address]
[City, State ZIP Code]
TIME: [Pickup Date & Time]

DEL: [Facility Name]
[Street Address]
[City, State ZIP Code]
TIME: [Delivery Date & Time]

TOTAL MILE: [Mileage]

RATE: [Rate]

    If any field is missing, return "N/A". Here is the document text:
    {text}  
    """

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        data = response.json()

        # Extract AI response correctly
        extracted_info = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )

        if not extracted_info:
            return "⚠️ Error: AI did not return valid data."

        # Append important conditions
        conditions = """

✅ Drivers will be charged ($150) for every late for PU and DEL If He/She doesn't provide us with the issue of being late. 

✅ Drivers will be charged ($150) for not using relay app properly.

✅ Trailer/seal pictures, all pages of BOL, and POD must be sent before checkout every time. Failure of sending these required things, driver will be charged for $100

✅ Please let us know if you stop or if you have any issues
        """

        return extracted_info + conditions

    except requests.exceptions.RequestException as e:
        return f"⚠️ Error: API request failed. {str(e)}"
    except KeyError:
        return "⚠️ Error: Unable to process the document."

# Handle PDF files
@bot.message_handler(content_types=['document'])
def handle_docs(message):
    try:
        file_info = bot.get_file(message.document.file_id)
        file_data = bot.download_file(file_info.file_path)

        with open("temp.pdf", "wb") as f:
            f.write(file_data)

        extracted_text = extract_text_from_pdf("temp.pdf")
        
        if extracted_text.startswith("⚠️ Error"):
            bot.send_message(message.chat.id, extracted_text)
            return
        
        result = get_load_info_from_gemini(extracted_text)

        bot.send_message(message.chat.id, result)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error processing the document: {str(e)}")

bot.polling()

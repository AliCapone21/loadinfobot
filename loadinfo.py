import telebot
import requests
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
from io import BytesIO
import os

# Set paths for OCR
pytesseract.pytesseract.tesseract_cmd = os.getenv(
    "TESSERACT_PATH", "/usr/bin/tesseract"
)
POPPLER_PATH = os.getenv("POPPLER_PATH", None)  # Default to None for Linux (Render)


# Replace with actual tokens
BOT_TOKEN = "7000898266:AAGOuOJVGZ5zkvd_wgtWZWrnCE7TNgjdxDM"
GEMINI_API_KEY = "AIzaSyDZR8EthTy4f6xei9lK14-8cZ231wlIajo"

bot = telebot.TeleBot(BOT_TOKEN)
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

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
PU: [Pickup Reference Number, Reference Number:]

PU: [Facility Name]
[Street Address]
[City, State ZIP Code]
TIME: [Pickup Date & Time]

DEL: [Facility Name]
[Street Address]
[City, State ZIP Code]
TIME: [Delivery Date & Time]

TOTAL MILE: [Mileage]

RATE: [Total Rate]

If any field is missing, return "N/A". Here is the document text:
{text}
    """

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Extract AI response
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

✅ Drivers will be charged ($150) for every late PU and DEL if they do not inform us of the issue.

✅ Drivers will be charged ($150) for not using the relay app properly.

✅ Trailer/seal pictures, all pages of BOL, and POD must be sent before checkout every time. Failure to send these will result in a $100 charge.

✅ Please let us know if you stop or if you have any issues.
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

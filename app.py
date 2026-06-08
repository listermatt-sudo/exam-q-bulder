from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from docx import Document
from docx.shared import Inches
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

import requests
from io import BytesIO

# ✅ FastAPI app
app = FastAPI()

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Supabase public URL
BASE_URL = "https://gdcwjpkgffqmatsmuqra.supabase.co/storage/v1/object/public/question-images"


# ✅ ALL SERIES YOU SPECIFIED
MONTHS = [
    "June 2025", "June 2024", "June 2023", "June 2022",
    "June 2019", "June 2018", "June 2017",
    "November 2025", "November 2024", "November 2023",
    "November 2022", "November 2021",
    "November 2019", "November 2018", "November 2017"
]

# ✅ ALL PAPERS
PAPERS = ["1F", "2F", "3F", "1H", "2H", "3H"]


# ✅ Request model
class RequestData(BaseModel):
    entries: list
    filetype: str


# ✅ ✅ CRITICAL: match your filename format exactly
def build_filename(month_year, paper, q):
    parts = month_year.split()
    month = parts[0]
    year = parts[1][-2:]

    # ✅ Convert November → Nov (YOUR FILE FORMAT)
    if month == "November":
        month = "Nov"

    return f"{month} {year} {paper}_Q{q}.png"


# ✅ ✅ Detect actual available questions
def get_valid_questions(month_year, paper):

    valid = []

    # adjust range if needed
    for q in range(1, 25):

        filename = build_filename(month_year, paper, q)
        url = f"{BASE_URL}/{filename}"

        response = requests.get(url)

        if response.status_code == 200:
            valid.append(q)

    return valid


# ✅ ✅ MAIN STRUCTURE ENDPOINT
@app.get("/structure")
def get_structure():

    structure = {}

    for month in MONTHS:

        month_data = {}

        for paper in PAPERS:

            questions = get_valid_questions(month, paper)

            if questions:
                month_data[paper] = questions

        # ✅ only include month if it has data
        if month_data:
            structure[month] = month_data

    return structure


# ✅ Word generation
def create_word(entries, filename):

    doc = Document()
    doc.add_heading("Worksheet", 0)

    for paper, q in entries:

        doc.add_heading(f"{paper} — Q{q}", level=1)

        url = f"{BASE_URL}/{paper}_Q{q}.png"
        response = requests.get(url)

        if response.status_code == 200:
            doc.add_picture(BytesIO(response.content), width=Inches(5))

        doc.add_page_break()

    doc.save(filename)


# ✅ PDF generation
def create_pdf(entries, filename):

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    y = height - 40

    for paper, q in entries:

        url = f"{BASE_URL}/{paper}_Q{q}.png"
        response = requests.get(url)

        if response.status_code != 200:
            continue

        img_obj = ImageReader(BytesIO(response.content))
        img_w, img_h = img_obj.getSize()

        scale = (width - 80) / img_w
        new_h = img_h * scale

        if y - new_h < 50:
            c.showPage()
            y = height - 40

        c.drawImage(
            img_obj,
            40,
            y - new_h,
            width=width - 80,
            height=new_h
        )

        y -= new_h + 20

    c.save()


# ✅ Generate endpoint
@app.post("/generate")
def generate(data: RequestData):

    if data.filetype == "word":
        filename = "worksheet.docx"
        create_word(data.entries, filename)
    else:
        filename = "worksheet.pdf"
        create_pdf(data.entries, filename)

    return FileResponse(filename, filename=filename)


# ✅ Home route
@app.get("/")
def home():
    return {"message": "Worksheet Builder API is running"}

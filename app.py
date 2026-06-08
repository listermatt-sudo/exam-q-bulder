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
import json

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

# ✅ Supabase storage
BASE_URL = "https://gdcwjpkgffqmatsmuqra.supabase.co/storage/v1/object/public/question-images"


# ✅ Load pre-built structure file (instant)
def load_structure():
    with open("structure.json", "r") as f:
        return json.load(f)


# ✅ Global cache (loads once at startup)
structure_cache = load_structure()


# ✅ Request model
class RequestData(BaseModel):
    entries: list
    filetype: str


# ✅ Build filename (must match your actual files)
def build_filename(month_year, paper, q):
    parts = month_year.split()
    month = parts[0]
    year = parts[1][-2:]

    # ✅ Your files use "Nov"
    if month == "November":
        month = "Nov"

    return f"{month} {year} {paper}_Q{q}.png"


# ✅ Structure endpoint (VERY FAST)
@app.get("/structure")
def get_structure():
    return structure_cache


# ✅ Word export
def create_word(entries, filename):

    doc = Document()
    doc.add_heading("Worksheet", 0)

    for paper, q in entries:

        doc.add_heading(f"{paper} — Q{q}", level=1)

        parts = paper.split()
        month = parts[0]
        year = parts[1]
        paper_code = parts[2]

        file_name = build_filename(f"{month} {year}", paper_code, q)
        url = f"{BASE_URL}/{file_name}"

        response = requests.get(url)

        if response.status_code == 200:
            doc.add_picture(BytesIO(response.content), width=Inches(5))

        doc.add_page_break()

    doc.save(filename)


# ✅ PDF export
def create_pdf(entries, filename):

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    y = height - 40

    for paper, q in entries:

        parts = paper.split()
        month = parts[0]
        year = parts[1]
        paper_code = parts[2]

        file_name = build_filename(f"{month} {year}", paper_code, q)
        url = f"{BASE_URL}/{file_name}"

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


# ✅ Health check
@app.get("/")
def home():
    return {"message": "Worksheet Builder API is running"}

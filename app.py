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

# ✅ Create FastAPI app
app = FastAPI()

# ✅ ENABLE CORS (fixes your error)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all (OK for local testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Supabase base URL
BASE_URL = "https://gdcwjpkgffqmatsmuqra.supabase.co/storage/v1/object/public/question-images"


# ✅ Request format from frontend
class RequestData(BaseModel):
    entries: list
    filetype: str


# ✅ Generate filename
def find_image(paper, q):
    return f"{paper}_Q{q}.png"


# ✅ Create Word document
def create_word(entries, filename):

    doc = Document()
    doc.add_heading("Worksheet", 0)

    for paper, q in entries:

        doc.add_heading(f"{paper} — Q{q}", level=1)

        img = find_image(paper, q)
        url = f"{BASE_URL}/{img}"

        response = requests.get(url)

        if response.status_code == 200:
            doc.add_picture(BytesIO(response.content), width=Inches(5))

        doc.add_page_break()

    doc.save(filename)


# ✅ Create PDF document
def create_pdf(entries, filename):

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4
    y = height - 40

    for paper, q in entries:

        img = find_image(paper, q)
        url = f"{BASE_URL}/{img}"

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


# ✅ Main endpoint
@app.post("/generate")
def generate(data: RequestData):

    # ✅ Choose file type
    if data.filetype == "word":
        filename = "worksheet.docx"
        create_word(data.entries, filename)
    else:
        filename = "worksheet.pdf"
        create_pdf(data.entries, filename)

    # ✅ Return file to browser
    return FileResponse(filename, filename=filename)
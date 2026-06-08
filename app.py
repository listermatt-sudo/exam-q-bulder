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

# ✅ Supabase config
SUPABASE_URL = "https://gdcwjpkgffqmatsmuqra.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdkY3dqcGtnZmZxbWF0c211cXJhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA4ODMxMzksImV4cCI6MjA5NjQ1OTEzOX0.bpjgWe1ydbiIK2e9yOwESvMRLoK5c_lHljCpOM8q-3o"
BUCKET = "question-images"

BASE_URL = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}"

# ✅ Month mapping
MONTH_MAP = {
    "Jan": "January",
    "Feb": "February",
    "Mar": "March",
    "Apr": "April",
    "May": "May",
    "Jun": "June",
    "Jul": "July",
    "Aug": "August",
    "Sep": "September",
    "Oct": "October",
    "Nov": "November",
    "Dec": "December"
}


# ✅ Request model
class RequestData(BaseModel):
    entries: list
    filetype: str


# ✅ Fetch all files from Supabase
def get_all_files():

    url = f"{SUPABASE_URL}/storage/v1/object/list/{BUCKET}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    # ✅ IMPORTANT: send prefix = "" (root folder)
    response = requests.post(
        url,
        headers=headers,
        json={"prefix": ""}
    )

    if response.status_code != 200:
        print("ERROR:", response.status_code, response.text)
        return []

    return response.json()

# ✅ Build structured data
def build_structure(files):

    data = {}

    for item in files:
        name = item.get("name", "")

        if "_Q" not in name:
            continue

        try:
            paper_part, q_part = name.replace(".png", "").split("_Q")
            parts = paper_part.split()

            if len(parts) < 3:
                continue

            raw_month = parts[0]
            month = MONTH_MAP.get(raw_month, raw_month)

            year = parts[1]
            paper = parts[2]

            q = int(q_part)

        except:
            continue

        month_year = f"{month} 20{year}"

        # ✅ Build nested structure
        if month_year not in data:
            data[month_year] = {}

        if paper not in data[month_year]:
            data[month_year][paper] = set()

        data[month_year][paper].add(q)

    return data


# ✅ Endpoint: get full structure
@app.get("/structure")
def get_structure():

    files = get_all_files()
    return {"debug": files}


# ✅ Generate filename
def find_image(paper, q):
    return f"{paper}_Q{q}.png"


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

        c.drawImage(img_obj, 40, y - new_h,
                    width=width - 80,
                    height=new_h)

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

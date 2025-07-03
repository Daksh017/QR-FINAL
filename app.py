from flask import Flask, request, render_template
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests
import cloudinary
import cloudinary.uploader
from pymongo import MongoClient
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
# Ensure the .env file is loaded

app = Flask(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# Configure MongoDB
MONGO_URI = os.getenv("MONGO_URI", "")
client = MongoClient(MONGO_URI)
db = client["qr_db"]
collection = db["qr_codes"]

def is_valid_url(url):
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        return response.status_code < 400
    except:
        return False

@app.route("/", methods=["GET", "POST"])
def home():
    title = ""
    name = ""
    error = ""
    cloudinary_url = ""

    if request.method == "POST":
        link = request.form["link"]
        title = request.form.get("title", "")
        name = request.form.get("name", "")

        if not is_valid_url(link):
            error = "❌ Invalid or unreachable URL. Please enter a real, working website link."
            return render_template("index.html", cloudinary_url=None, title=title, name=name, error=error)

        qr_img = qrcode.make(link).convert("RGB")
        width, height = qr_img.size
        new_height = height + 100
        img_with_text = Image.new("RGB", (width, new_height), "white")
        draw = ImageDraw.Draw(img_with_text)

        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()

        draw.text((width // 2 - draw.textlength(title, font=font) // 2, 10), title, font=font, fill="black")
        img_with_text.paste(qr_img, (0, 40))
        draw.text((width // 2 - draw.textlength(name, font=font) // 2, height + 50), name, font=font, fill="black")

        buffer = BytesIO()
        img_with_text.save(buffer, format="PNG")
        buffer.seek(0)

        upload_result = cloudinary.uploader.upload(buffer, public_id=f"qr_{uuid.uuid4().hex[:8]}")
        cloudinary_url = upload_result.get("secure_url")

        # Store metadata in MongoDB
        record = {
            "title": title,
            "name": name,
            "link": link,
            "cloudinary_url": cloudinary_url[:500],
            "timestamp": datetime.utcnow()
        }
        collection.insert_one(record)

    return render_template("index.html", cloudinary_url=cloudinary_url, title=title, name=name, error=error)

if __name__ == "__main__":
    app.run(debug=True)
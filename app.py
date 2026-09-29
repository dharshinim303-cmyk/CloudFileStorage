from flask import Flask, render_template, request, send_from_directory, redirect, session
import os
import cloudinary
import cloudinary.uploader
import cloudinary.api
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")

def create_database():

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        password TEXT
    )
    """)


    conn.commit()
    conn.close()


create_database()

cloudinary.config(
    cloud_name="n9c2shuz",api_key="243236164611588",api_secret="dMeBQ7-ATIP3TfT9Lh7oEdD4q1g"
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER,exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {
    "pdf",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "jfif",
    "heic",
    "heif",
    "txt",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx"
}

MAX_FILE_SIZE = 10 * 1024 * 1024
STORAGE_LIMIT_MB = 100

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=? ORDER BY id DESC LIMIT 1", 
            (email,)
        )

        user = cursor.fetchone()

        print("USER:", user)

        if user:
            print("Password Match:", check_password_hash(user[3], password))

        conn.close()

        if user and check_password_hash(user[3], password):

            session["user"] = user[1]

            return redirect("/dashboard")

        else:

            return "Invalid Email or Password"

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        print("Register button clicked")

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        password = generate_password_hash(password)


        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("DELETE FROM users WHERE email=?", (email,))

        cursor.execute(
            "INSERT INTO users(username, email, password) VALUES(?,?,?)",
            (username, email, password)
        )

        conn.commit()

        print("Inserted:", username, email)

        cursor.execute("SELECT * FROM users")
        print(cursor.fetchall())

        conn.close()

        return "Registration Successful"

    return render_template("register.html")

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    try:

        username = session.get("user")
        user_folder = f"CloudFileStorage/{username}"

        # ---------------------------------------
        # GET IMAGE FILES
        # ---------------------------------------

        image_result = cloudinary.api.resources(
            type="upload",
            resource_type="image",
            max_results=500
        )

        # ---------------------------------------
        # GET RAW FILES
        # PDF, DOC, DOCX, XLS, XLSX, PPT, etc.
        # ---------------------------------------

        raw_result = cloudinary.api.resources(
            type="upload",
            resource_type="raw",
            max_results=500
        )

        all_images = image_result.get("resources", [])
        all_raw = raw_result.get("resources", [])

        # ---------------------------------------
        # FILTER CURRENT USER FILES
        # ---------------------------------------

        image_files = []

        for file in all_images:

            public_id = file.get("public_id", "")
            asset_folder = file.get("asset_folder", "")

            if (
                public_id.startswith(user_folder + "/")
                or asset_folder == user_folder
                or asset_folder.startswith(user_folder + "/")
            ):
                image_files.append(file)

        raw_files = []

        for file in all_raw:

            public_id = file.get("public_id", "")
            asset_folder = file.get("asset_folder", "")

            if (
                public_id.startswith(user_folder + "/")
                or asset_folder == user_folder
                or asset_folder.startswith(user_folder + "/")
            ):
                raw_files.append(file)

        # ---------------------------------------
        # COMBINE ALL FILES
        # ---------------------------------------

        files = image_files + raw_files

        # ---------------------------------------
        # IMAGE COUNT
        # ---------------------------------------

        image_count = len(image_files)

        # ---------------------------------------
        # PDF + OTHER COUNT
        # ---------------------------------------

        pdf_count = 0
        other_count = 0

        for file in raw_files:

            file_format = file.get("format", "").lower()
            public_id = file.get("public_id", "").lower()

            if (
                file_format == "pdf"
                or public_id.endswith(".pdf")
            ):
                pdf_count += 1

            else:
                other_count += 1

        # ---------------------------------------
        # TOTAL FILES
        # ---------------------------------------

        total_files = len(files)

        # ---------------------------------------
        # TOTAL STORAGE
        # ---------------------------------------

        total_size = 0

        for file in files:
            total_size += file.get("bytes", 0)

        storage_mb = round(
            total_size / (1024 * 1024),
            2
        )

        # ---------------------------------------
        # SORT RECENT FILES
        # ---------------------------------------

        files.sort(
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )

        recent_files = files[:5]

        # ---------------------------------------
        # STORAGE
        # ---------------------------------------

        storage_limit_mb = 100

        storage_percent = round(
            (storage_mb / storage_limit_mb) * 100,
            2
        )

        storage_remaining_mb = round(
            max(storage_limit_mb - storage_mb, 0),
            2
        )

        storage_warning = ""

        if storage_percent >= 90:

            storage_warning = (
                "🚨 Critical: Your storage is almost full!"
            )

        elif storage_percent >= 80:

            storage_warning = (
                "⚠️ Warning: Your storage usage is high!"
            )

        # ---------------------------------------
        # TERMINAL DEBUG
        # ---------------------------------------

        print("--------------------------------")
        print("USER:", username)
        print("USER FOLDER:", user_folder)
        print("IMAGE FILES:", len(image_files))
        print("RAW FILES:", len(raw_files))
        print("TOTAL FILES:", total_files)
        print("PDF:", pdf_count)
        print("OTHER:", other_count)
        print("STORAGE:", storage_mb, "MB")
        print("--------------------------------")

        # ---------------------------------------
        # SEND TO dashboard.html
        # ---------------------------------------

        return render_template(
            "dashboard.html",

            username=username,

            total_files=total_files,

            storage_mb=storage_mb,

            recent_files=recent_files,

            image_count=image_count,

            pdf_count=pdf_count,

            other_count=other_count,

            storage_percent=storage_percent,

            storage_warning=storage_warning,

            stoage_remaining_mb=storage_remaining_mb
        )

    except Exception as e:

        print("DASHBOARD ERROR:", e)

        return f"Dashboard error: {e}"

@app.route("/upload", methods=["GET", "POST"])
def upload():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        if "file" not in request.files:
            return "Please select a file"

        file = request.files["file"]

        if file.filename == "":
            return "Please select a file"

        # Original file name
        filename = file.filename

        # Remove unsafe characters from file name
        from werkzeug.utils import secure_filename
        filename = secure_filename(filename)

        if filename == "":
            return "Invalid file name"

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            return "File size must be less than 10 MB"

        # Check current storage - images + other files
        current_storage = 0

        image_result = cloudinary.api.resources(
            type="upload",
            resource_type="image",
            max_results=500
        )

        raw_result = cloudinary.api.resources(
            type="upload",
            resource_type="raw",
            max_results=500
        )

        user_folder = f"CloudFileStorage/{session['user']}/"

        all_existing_files = (
            image_result.get("resources", [])
            + raw_result.get("resources", [])
        )

        for existing_file in all_existing_files:

            public_id = existing_file.get("public_id", "")

            if public_id.startswith(user_folder):
                current_storage += existing_file.get("bytes", 0)

        current_storage_mb = current_storage / (1024 * 1024)

        # Check storage limit
        if current_storage_mb + (file_size / (1024 * 1024)) > STORAGE_LIMIT_MB:
            return "Storage limit reached. Cannot upload this file."

        # File name without extension
        file_name_without_extension = os.path.splitext(filename)[0]

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file,
            resource_type="auto",
            folder=f"CloudFileStorage/{session['user']}",
            use_filename=True,
            unique_filename=False,
            overwrite=True,
        )

        return f"File Uploaded Successfully!<br>Cloud URL: {result['secure_url']}"

    return render_template("upload.html")

@app.route("/myfiles")
def myfiles():

    if "user" not in session:
        return redirect("/login")

    search = request.args.get("search", "").lower()

    files = []

    # Get image files
    image_result = cloudinary.api.resources(
        type="upload",
        resource_type="image",
        max_results=500
    )

    # Get other files
    raw_result = cloudinary.api.resources(
        type="upload",
        resource_type="raw",
        max_results=500
    )

    all_files = (
        image_result.get("resources", [])
        + raw_result.get("resources", [])
    )

    user_folder = f"CloudFileStorage/{session['user']}/"

    for file in all_files:

        public_id = file.get("public_id", "")

        # Only show current user's files
        if not public_id.startswith(user_folder):
            continue

        # Get actual file name
        original_name = file.get("original_filename", "")

        if not original_name:
            original_name = public_id.split("/")[-1]

        # Add extension if needed
        file_format = file.get("format", "")

        if file_format and "." not in original_name:
            original_name = original_name + "." + file_format

        # Search
        if search and search not in original_name.lower():
            continue

        files.append({
            "name": public_id,
            "display_name": original_name,
            "url": file.get("secure_url"),
            "resource_type": file.get("resource_type")
        })

    return render_template(
        "myfiles.html",
        files=files,
        search=search
    )

@app.route("/delete/<path:public_id>")
def delete_file(public_id):

    if "user" not in session:
        return redirect("/login")

    # Security: allow deleting only the logged-in user's file
    user_folder = f"CloudFileStorage/{session['user']}/"

    if not public_id.startswith(user_folder):
        return "Unauthorized access"

    try:
        image_result = cloudinary.uploader.destroy(
            public_id,
            resource_type="image"
        )

        if image_result.get("result") == "ok":
            return redirect("/myfiles")

    except Exception as e:
        print("IMAGE DELETE ERROR:", e)

    try:
        raw_result = cloudinary.uploader.destroy(
            public_id,
            resource_type="raw"
        )

        print("RAW DELETE RESULT:", raw_result)

    except Exception as e:
        print("RAW DELETE ERROR:", e)

    return redirect("/myfiles")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

print(app.url_map)
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
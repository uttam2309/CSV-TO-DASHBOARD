from flask import Flask, render_template, request, redirect
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

import os
import pandas as pd

from config import Config
from models import db, User, Upload
app = Flask(__name__)

# Load configuration
app.config.from_object(Config)

# Initialize database
db.init_app(app)

# Create database automatically
with app.app_context():
    db.create_all()


# ---------------- HOME ---------------- #

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- REGISTER ---------------- #

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["fullname"]
        email = request.form["email"]
        password = request.form["password"]

        existing = User.query.filter_by(email=email).first()

        if existing:
            return "Email already exists."

        hashed_password = generate_password_hash(password)

        user = User(
            fullname=fullname,
            email=email,
            password=hashed_password
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGIN ---------------- #


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        # Temporary login (we'll add real authentication next)
        return redirect("/dashboard")

    return render_template("login.html")


# ---------------- DASHBOARD ---------------- #

@app.route("/dashboard")
def dashboard():

    uploads = Upload.query.all()

    return render_template(
        "dashboard.html",
        total_files=len(uploads),
        total_rows=sum(u.rows for u in uploads),
        total_columns=sum(u.columns for u in uploads)
    )

# ---------------- UPLOAD ---------------- #

# ---------------- UPLOAD ---------------- #

@app.route("/upload", methods=["GET", "POST"])
def upload():

    if request.method == "POST":

        file = request.files["csvfile"]

        if file.filename == "":
            return "Please select a CSV file."

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Read CSV
        df = pd.read_csv(
            filepath,
            header=None,
            names=["raw"]
        )

        df = df["raw"].str.split(",", expand=True)

        df.columns = [
            "Order_ID",
            "Order_Date",
            "Customer_Name",
            "Product",
            "Category",
            "City",
            "Quantity",
            "Unit_Price",
            "Total_Amount",
            "Payment_Method"
        ]

        df = df.apply(lambda col: col.str.replace('"', "", regex=False))

        # Remove header row if it exists
        if df.iloc[0]["Order_ID"] == "Order_ID":
            df = df.iloc[1:].reset_index(drop=True)

        # Convert numeric columns
        df["Quantity"] = pd.to_numeric(df["Quantity"])
        df["Unit_Price"] = pd.to_numeric(df["Unit_Price"])
        df["Total_Amount"] = pd.to_numeric(df["Total_Amount"])

        # Save upload information
        upload_data = Upload(
            filename=filename,
            filepath=filepath,
            rows=df.shape[0],
            columns=df.shape[1],
            user_id=1
        )

        db.session.add(upload_data)
        db.session.commit()

        # Detect columns
        numeric_columns = df.select_dtypes(include="number").columns.tolist()
        text_columns = df.select_dtypes(exclude="number").columns.tolist()

        # Create chart data
        chart_data = df.groupby("Category")["Total_Amount"].sum().reset_index()

        chart_labels = chart_data["Category"].tolist()
        chart_values = chart_data["Total_Amount"].tolist()

        return render_template(
            "analytics.html",
            total_files=Upload.query.count(),
            total_rows=df.shape[0],
            total_columns=df.shape[1],
            table=df.head(20).to_html(
                classes="table table-striped table-bordered",
                index=False
            ),
            numeric_columns=numeric_columns,
            text_columns=text_columns,
            chart_labels=chart_labels,
            chart_values=chart_values
        )

    return render_template("upload.html")
# ---------------- HISTORY ---------------- #

@app.route("/history")
def history():

    uploads = Upload.query.order_by(Upload.uploaded_at.desc()).all()

    return render_template(
        "history.html",
        uploads=uploads
    )

# ---------------- PROFILE ---------------- #

@app.route("/profile")
def profile():
    return render_template("profile.html")


if __name__ == "__main__":
    app.run(debug=True)
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
    Response,
    make_response,
)
from sqlalchemy import func
from datetime import datetime, timedelta
import os
import random, time
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)
from io import BytesIO
from sqlalchemy.sql import func
from flask_mail import Mail, Message

import pymysql
pymysql.install_as_MySQLdb()

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY", "fallback_secret_key"
)  # Use a secure key in production
db = SQLAlchemy(app)


# Hotel Registration Table
class tblhotelregistration(db.Model):
    hotel_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    phone_no = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    profile = db.Column(db.String(300), nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    date_of_reg = db.Column(db.DateTime, default=datetime.utcnow)
    password = db.Column(db.String(300), nullable=False)

    def __init__(
        self,
        name,
        description,
        address,
        city,
        state,
        zip_code,
        phone_no,
        email,
        profile,
        password,
    ):
        self.name = name
        self.description = description
        self.address = address
        self.city = city
        self.state = state
        self.zip_code = zip_code
        self.phone_no = phone_no
        self.email = email
        self.profile = profile
        self.password = password

    def check_password(self, password):
        """Check if the provided password matches the hashed password."""
        return self.password == password

    def set_password(self, password):
        """Hash and set the password."""
        self.password = password


class RoomType(db.Model):
    __tablename__ = "RoomTypes"  # Match the table name in the database

    room_type_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    max_occupancy = db.Column(db.Integer, nullable=False)
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<RoomType {self.name}>"


# Room Registration Table (modified relationship to RoomType)
class RoomRegistration(db.Model):
    room_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    room_number = db.Column(db.String(50), nullable=False, unique=True)
    room_type_id = db.Column(
        db.Integer,
        db.ForeignKey("RoomTypes.room_type_id", ondelete="CASCADE"),
        nullable=False,
    )
    floor = db.Column(db.Integer, nullable=False)
    area = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    service_contact_no = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, default=True)
    date_registered = db.Column(db.DateTime, default=datetime.utcnow)
    room_type = db.relationship("RoomType", backref=db.backref("rooms", lazy=True))

    def __init__(
        self, room_number, room_type_id, floor, area, price, service_contact_no
    ):
        self.room_number = room_number
        self.room_type_id = room_type_id
        self.floor = floor
        self.area = area
        self.price = price
        self.service_contact_no = service_contact_no
        self.active = True  # By default the room is active

    def __repr__(self):
        return f"<Room {self.room_number}>"


class RoomStatus(db.Model):
    __tablename__ = "roomstatus"

    id = db.Column(
        db.Integer, primary_key=True, autoincrement=True
    )  # Set auto-increment
    status_type_id = db.Column(
        db.Integer,
        db.ForeignKey("roomstatustypes.id", ondelete="SET NULL"),
        nullable=True,
    )
    room_id = db.Column(
        db.String(50), primary_key=False, nullable=False
    )  # Keep room_id as not primary_key
    status = db.Column(
        db.Enum("available", "occupied", "maintenance", name="status_enum"),
        nullable=False,
    )

    def __repr__(self):
        return f"<Room {self.room_id} - {self.status}>"


class RoomStatusTypes(db.Model):
    __tablename__ = "roomstatustypes"

    # Define the columns in the table
    id = db.Column(
        db.Integer, primary_key=True, autoincrement=True
    )  # Primary Key and Auto Increment
    status_name = db.Column(db.String(50), nullable=False)

    # Establish relationship with RoomStatus
    rooms = db.relationship(
        "RoomStatus", backref="status_type_rel", lazy=True
    )  # Changed backref to avoid conflict

    def __repr__(self):
        return f"<RoomStatusType {self.status_name}>"


with app.app_context():
    db.create_all()  # This will create all tables based on the defined models


# Function to add RoomStatusTypes if they don't exist already
def add_room_status_types():
    status_types = ["Available", "Occupied", "Maintenance"]

    with app.app_context():
        for status_name in status_types:
            # Check if the status type already exists in the database
            existing_status = RoomStatusTypes.query.filter(
    func.lower(RoomStatusTypes.status_name) == status_name.lower()
).first()
            if not existing_status:  # Only add if not already in the database
                new_status = RoomStatusTypes(status_name=status_name)
                db.session.add(new_status)
                print(f"Adding new status: {status_name}")
            else:
                print(f"Status '{status_name}' already exists. Skipping.")

        # Commit the session after adding new statuses
        db.session.commit()
        print("RoomStatusTypes have been added or skipped as necessary.")


# Call the function to add the status types
add_room_status_types()


# Ensure there are room types in the database (you can call this function during app initialization or setup)
def create_sample_room_types():
    room_types = RoomType.query.all()
    if not room_types:  # If no room types exist, insert some sample room types
        sample_room_types = [
            RoomType(
                name="Single",
                description="A single room for one person",
                max_occupancy=1,
                base_price=1300.00,
            ),
            RoomType(
                name="Double",
                description="A room with two beds for two people",
                max_occupancy=2,
                base_price=2400.00,
            ),
            RoomType(
                name="Suite",
                description="A luxurious suite",
                max_occupancy=4,
                base_price=7000.00,
            ),
        ]
        db.session.add_all(sample_room_types)
        db.session.commit()
        print("Sample room types added.")


# Create the tables and add a test hotel if not already present
def create_initial_hotel():
    with app.app_context():
        db.create_all()

        # Ensure room types are created if not already present
        create_sample_room_types()

        # Check if hotel already exists with the given email
        hotel = tblhotelregistration.query.filter_by(
            email="info@abc.com"
        ).first()  # Use the actual email here
        if not hotel:
            new_hotel = tblhotelregistration(
                name="Oceanview Resort",
                description="Relax by the ocean with a breathtaking view.",
                address="456 Ocean Blvd, Seaside, FL",
                city="Seaside",
                state="FL",
                zip_code="67890",
                phone_no="234-567-8901",
                email="info@abc.com",  # This is the email that will be checked
                profile="path/to/profile/oceanview.jpg",
                password="oceanview123",  # This password will be hashed
            )
            new_hotel.set_password("oceanview123")  # Hash the password
            db.session.add(new_hotel)
            db.session.commit()
            print("New hotel added successfully!")
            return new_hotel
        else:
            print("Hotel already exists.")
            return hotel


# Route for the Login page
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Check if both email and password are provided
        if not email or not password:
            flash("Email and password are required.", "danger")
            return redirect(url_for("login"))

        # Check if the email exists in the database
        hotel = tblhotelregistration.query.filter_by(email=email).first()
        if hotel:
            # Check if the password matches the entered password
            if hotel.check_password(password):
                print(f"Password match successful for {email}")  # Debugging
                session["hotel_id"] = hotel.hotel_id  # Store hotel ID in session
                session["hotel_email"] = (
                    hotel.email
                )  # Optionally store email or any other info
                return redirect(url_for("dashboard"))
            else:
                print(f"Password mismatch for {email}")  # Debugging
                flash("Invalid email or password", "danger")
                return redirect(url_for("login"))
        else:
            print(f"No hotel found with email: {email}")  # Debugging
            flash("Invalid email or password", "danger")
            return redirect(url_for("login"))
    new_hotel = create_initial_hotel()
    return render_template("login.html", new_hotel=new_hotel)


# Route for the dashboard page
@app.route("/dashboard")
def dashboard():
    bookings = Customer.query.count()
    rooms = RoomStatus.query.filter(RoomStatus.status_type_id == 1).count()
    staffs = Staff.query.count()
    if "hotel_id" not in session:
        flash("You need to login first.", "warning")
        return redirect(url_for("login"))

    new_hotel = create_initial_hotel()
    return render_template(
        "index.html", new_hotel=new_hotel, bookings=bookings, rooms=rooms, staffs=staffs
    )


@app.route("/profile")
def profile():
    if "hotel_id" not in session:
        flash("You need to login first.", "warning")
        return redirect(url_for("login"))

    new_hotel = create_initial_hotel()
    return render_template("profile.html", new_hotel=new_hotel)


@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if "hotel_id" not in session:
        flash("You need to login first.", "warning")
        return redirect(url_for("login"))

    hotel = tblhotelregistration.query.filter_by(hotel_id=session["hotel_id"]).first()
    if not hotel:
        flash("User not found.", "danger")
        return redirect(url_for("profile"))

    if request.method == "POST":
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]
        new_password_repeat = request.form["new_password_repeat"]

        if not hotel.check_password(old_password):
            flash("Incorrect old password.", "danger")
        elif new_password != new_password_repeat:
            flash("New passwords do not match.", "warning")
        else:
            hotel.set_password(new_password)  # Hash the new password
            db.session.commit()
            flash("Password changed successfully!", "success")
            return redirect(url_for("profile"))

    return render_template("profile.html")


# Route for adding a room
@app.route("/add-room", methods=["GET", "POST"])
def add_room():
    new_hotel = create_initial_hotel()
    room_types = RoomType.query.filter_by(
        active=True
    ).all()  # Fetch active room types from database

    if request.method == "POST":
        room_no = request.form["room_number"]
        room_type_id = request.form["room_type_id"]
        floor = request.form["floor"]
        area = request.form["area"]
        price = request.form["price"]
        service_no = request.form["service_contact_no"]

        # Check if the room type exists before adding the room
        room_type = RoomType.query.filter_by(room_type_id=room_type_id).first()
        if not room_type:
            flash(
                "Invalid room type selected. Please choose a valid room type.", "danger"
            )
            return redirect(url_for("add_room"))

        new_room = RoomRegistration(
            room_number=room_no,
            room_type_id=room_type_id,
            floor=floor,
            area=area,
            price=price,
            service_contact_no=service_no,
        )
        db.session.add(new_room)
        db.session.commit()
        flash("Room added successfully!", "success")
        return redirect(
            url_for("dashboard")
        )  # Redirect back to dashboard or another page

    return render_template("add-room.html", new_hotel=new_hotel, room_types=room_types)


@app.route("/room-status")
def room_status():
    new_hotel = create_initial_hotel()
    rooms = RoomRegistration.query.all()
    return render_template("room-status.html", new_hotel=new_hotel, rooms=rooms)


@app.route("/<string:room_number>/<string:status>", methods=["GET", "POST"])
def update_room_status(room_number, status):
    status = (
        status.lower()
    )  # Convert the status to lowercase to handle case insensitivity

    # Define valid statuses
    valid_statuses = ["available", "occupied", "maintenance"]

    # Check if the status is valid
    if status not in valid_statuses:
        flash(
            f"Invalid status '{status}', valid statuses are: {', '.join(valid_statuses)}",
            "danger",
        )
        return redirect(url_for("room_status"))  # Redirect back to the room status page

    # Find the room by room_number in the RoomRegistration table
    room = RoomRegistration.query.filter_by(room_number=room_number).first()
    if not room:
        flash(f"Room with number {room_number} not found.", "danger")
        return redirect(url_for("room_status"))  # Redirect back to the room status page

    # Now find the corresponding RoomStatus entry for this room
    room_status = RoomStatus.query.filter_by(room_id=room_number).first()

    # Check if the room already has a RoomStatus entry
    if room_status:
        # If the room already has a RoomStatus entry, update it
        if room_status.status == status:
            flash(
                f"Room {room_number} already has the status '{status}', no update necessary.",
                "warning",
            )
            return redirect("/room-status")

        room_status.status = status  # Update the status

        # Optionally, update the status_type_id (link to RoomStatusTypes)
        statustype = RoomStatusTypes.query.filter(
    func.lower(RoomStatusTypes.status_name) == status
).first()
        if statustype:
            room_status.status_type_id = statustype.id
        else:
            flash(f"Status type '{status}' not found.", "danger")
            return redirect(url_for("room_status"))
    else:
        # If no RoomStatus entry exists for this room, create a new entry
        statustype = RoomStatusTypes.query.filter(
    func.lower(RoomStatusTypes.status_name) == status
).first()
        if statustype:
            status_add = RoomStatus(
                room_id=room_number, status=status, status_type_id=statustype.id
            )
            db.session.add(status_add)
        else:
            flash(f"Status type '{status}' not found.", "danger")
            return redirect(url_for("room_status"))

    # Commit the changes to the database
    try:
        db.session.commit()
        flash(f"Room {room_number} status updated to '{status}'.", "success")
    except Exception as e:
        db.session.rollback()  # Rollback if there's any issue
        flash(f"An error occurred: {str(e)}", "danger")

    return redirect("/room-status")  # Redirect back to the room status page


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Primary key
    booking_id = db.Column(db.String(100), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)

    # Foreign key referencing the RoomType table
    room_type_id = db.Column(
        db.Integer, db.ForeignKey("RoomTypes.room_type_id"), nullable=False
    )

    # Relationship to RoomType
    room_type = relationship("RoomType", backref=db.backref("customers", lazy=True))

    room_number = db.Column(db.String(100), nullable=False)
    total_no = db.Column(db.Integer, nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_in_time = db.Column(db.Time, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    check_out_time = db.Column(db.Time, nullable=False)
    email = db.Column(db.String(200), nullable=False)
    phone_no = db.Column(db.String(15), nullable=False)
    filename = db.Column(db.String(255), nullable=True)
    price = db.Column(db.Float, nullable=False)
    due_price = db.Column(db.Float, nullable=False)
    active = db.Column(db.Boolean, default=True)  # Active status
    registration_date = db.Column(
        db.DateTime, default=datetime.utcnow
    )  # Auto-set registration date

    def __repr__(self):
        return f"<Customer {self.name}, Room Type: {self.room_type.name}>"

    def __init__(
        self,
        booking_id,
        name,
        room_type_id,
        room_number,
        total_no,
        check_in_date,
        check_in_time,
        check_out_date,
        check_out_time,
        email,
        phone_no,
        filename,
        price,
        due_price,
    ):

        self.booking_id = booking_id
        self.name = name
        self.room_type_id = room_type_id
        self.room_number = room_number
        self.total_no = total_no
        self.check_in_date = check_in_date
        self.check_in_time = check_in_time
        self.check_out_date = check_out_date
        self.check_out_time = check_out_time
        self.email = email
        self.phone_no = phone_no
        self.filename = filename
        self.price = price
        self.due_price = due_price


from flask import request, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from datetime import datetime
import os

# Define your upload folder (you can change this)
UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist

@app.route("/add-customer", methods=["GET", "POST"])
def add_customer():
    if request.method == "POST":
        try:
            # Extract form data
            bookingId = request.form["bookingId"]
            name = request.form["name"]
            roomType = request.form["roomType"]
            roomNumber = request.form["roomNumber"]
            totalNo = int(request.form["totalNo"])
            checkInDate = datetime.strptime(request.form["checkInDate"], "%d/%m/%Y").date()
            checkInTime = datetime.strptime(request.form["checkInTime"], "%H:%M").time()
            checkOutDate = datetime.strptime(request.form["checkOutDate"], "%d/%m/%Y").date()
            checkOutTime = datetime.strptime(request.form["checkOutTime"], "%H:%M").time()
            email = request.form["email"]
            phoneNo = request.form["phoneNo"]
            price = float(request.form["price"])
            duePrice = float(request.form["duePrice"])

            # Handle file upload
            uploaded_file = request.files.get("filename")
            filename = None
            if uploaded_file and uploaded_file.filename:
                filename = secure_filename(uploaded_file.filename)
                uploaded_file.save(os.path.join(UPLOAD_FOLDER, filename))

            # Create new customer instance
            newCustomer = Customer(
                booking_id=bookingId,
                name=name,
                room_type_id=roomType,
                room_number=roomNumber,
                total_no=totalNo,
                check_in_date=checkInDate,
                check_in_time=checkInTime,
                check_out_date=checkOutDate,
                check_out_time=checkOutTime,
                email=email,
                phone_no=phoneNo,
                filename=filename,
                price=price,
                due_price=duePrice,
            )

            db.session.add(newCustomer)

            # Check and update room status
            room_status = RoomStatus.query.filter_by(room_id=roomNumber).first()

            if room_status:
                if room_status.status == "available":
                    room_status.status = "occupied"
                    room_status.status_type_id = 2
                    flash(f"Room {roomNumber} status updated to 'occupied'.", "success")
                else:
                    flash(
                        f"Room {roomNumber} is not available. Current status: {room_status.status}.",
                        "error",
                    )
            else:
                flash(f"Room {roomNumber} not found in RoomStatus.", "error")

            # ✅ Final commit (after all DB changes)
            db.session.commit()
            flash("Customer added successfully!", "success")

        except Exception as e:
            db.session.rollback()
            flash(f"Error: {str(e)}", "error")
            print(f"Error: {str(e)}")

        return redirect(url_for("add_customer"))

    # GET request: render the form
    new_hotel = create_initial_hotel()
    room = RoomType.query.all()
    status = RoomStatus.query.filter(RoomStatus.status == "available").all()

    return render_template(
        "add-customer.html", new_hotel=new_hotel, room=room, status=status
    )


# def generate_hotel_receipt(
#     bookingId,
#     name,
#     phoneNo,
#     email,
#     roomNumber,
#     checkInDate,
#     checkOutDate,
#     checkInTime,
#     checkOutTime,
#     price,
# ):
#     buffer = BytesIO()
#     doc = SimpleDocTemplate(buffer, pagesize=letter)
#     styles = getSampleStyleSheet()

#     # Title Styles
#     title_style = ParagraphStyle(
#         "TitleStyle",
#         parent=styles["Title"],
#         fontSize=18,
#         alignment=1,
#         textColor=colors.HexColor("#004d4d"),
#     )
#     subtitle_style = ParagraphStyle(
#         "SubtitleStyle",
#         parent=styles["Normal"],
#         fontSize=10,
#         alignment=1,
#         textColor=colors.grey,
#     )

#     # Header Content
#     head = Paragraph("OCEAN VIEW RESORT", title_style)
#     title = Paragraph("HOTEL RECEIPT", title_style)
#     subtitle = Paragraph(
#         "4162 Masonic Drive, BroadView, MT, 59015<br/>"
#         "(123)123-4567 - info@123hotel.com - www.123hotel.com",
#         subtitle_style,
#     )

#     # Spacer
#     space_small = Spacer(1, 8)
#     space_medium = Spacer(1, 12)

#     # BILL TO Section
#     bill_to_title = Paragraph("<b>BILL TO</b>", styles["Heading2"])
#     bill_to_data = [
#         ["Name:", name],
#         ["Phone Number:", phoneNo],
#         ["Email:", email],
#         # ['Address:', address],
#     ]
#     bill_to_table = Table(bill_to_data, colWidths=[100, 300])
#     bill_to_table.setStyle(
#         TableStyle(
#             [
#                 ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
#                 ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
#                 ("FONTSIZE", (0, 0), (-1, -1), 10),
#                 ("VALIGN", (0, 0), (-1, -1), "TOP"),
#             ]
#         )
#     )

#     # Ensure that checkInDate and checkOutDate are datetime.date objects
#     if isinstance(checkInDate, str):
#         check_in = datetime.strptime(checkInDate, "%Y-%m-%d").date()
#     else:
#         check_in = checkInDate

#     if isinstance(checkOutDate, str):
#         check_out = datetime.strptime(checkOutDate, "%Y-%m-%d").date()
#     else:
#         check_out = checkOutDate

#     # Calculate number of nights
#     nights = (check_out - check_in).days

#     # Calculate total amount based on price per night and nights
#     totalAmount = nights * price

#     # Table for Room Details
#     room_table_data = [
#         ["Room Number", "Number of Nights", "Price per Night ($)", "Total ($)"],
#         [roomNumber, nights, f"{price:.2f}", f"{totalAmount:.2f}"],
#     ]
#     room_table = Table(room_table_data, colWidths=[150, 150, 150, 100])
#     room_table.setStyle(
#         TableStyle(
#             [
#                 ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#004d4d")),
#                 ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
#                 ("ALIGN", (0, 0), (-1, -1), "CENTER"),
#                 ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
#                 ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
#                 ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
#             ]
#         )
#     )

#     # Check-In and Check-Out Table
#     check_in_out_data = [
#         ["Check-In Date:", checkInDate],
#         ["Check-Out Date:", checkOutDate],
#         ["Check-In Time:", checkInTime],
#         ["Check-Out Time:", checkOutTime],
#     ]
#     check_in_out_table = Table(check_in_out_data, colWidths=[100, 300])

#     # Total Amount Section
#     total_data = [["Total Amount ", f"{totalAmount:.2f}"]]
#     total_table = Table(total_data, colWidths=[400, 100])
#     total_table.setStyle(
#         TableStyle(
#             [
#                 ("ALIGN", (1, 0), (1, 0), "RIGHT"),
#                 ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
#                 ("FONTSIZE", (0, 0), (-1, -1), 12),
#                 ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
#                 ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5d76e")),
#             ]
#         )
#     )

#     # Signature Section
#     signature_data = [
#         ["Cashier's Signature", "Customer's Signature"],
#         ["____________________", "____________________"],
#     ]
#     signature_table = Table(signature_data, colWidths=[250, 250])
#     signature_table.setStyle(
#         TableStyle(
#             [
#                 ("ALIGN", (0, 0), (-1, -1), "CENTER"),
#                 ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
#                 ("FONTSIZE", (0, 0), (-1, -1), 10),
#             ]
#         )
#     )

#     # Combine All Elements
#     elements = [
#         head,
#         title,
#         subtitle,
#         space_medium,
#         bill_to_title,
#         space_small,
#         bill_to_table,
#         space_medium,
#         room_table,
#         space_medium,
#         check_in_out_table,
#         space_medium,
#         total_table,
#         space_medium,
#         signature_table,
#     ]

#     # Build Document
#     doc.build(elements)
#     buffer.seek(0)

#     # Return PDF as Response
#     response = make_response(buffer.getvalue())
#     response.headers["Content-Type"] = "application/pdf"
#     response.headers["Content-Disposition"] = (
#         f"attachment; filename=booking_{bookingId}.pdf"
#     )
#     return response


def generate_hotel_receipt(
    bookingId,
    name,
    phoneNo,
    email,
    roomNumber,
    checkInDate,
    checkOutDate,
    # checkInTime,
    # checkOutTime,
    price,
    food_orders
):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    # Title Styles
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=18,
        alignment=1,
        textColor=colors.HexColor("#004d4d"),
    )
    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["Normal"],
        fontSize=10,
        alignment=1,
        textColor=colors.grey,
    )

    # Header Content
    head = Paragraph("OCEAN VIEW RESORT", title_style)
    title = Paragraph("HOTEL RECEIPT", title_style)
    subtitle = Paragraph(
        "456 Ocean Blvd, Seaside, FL, 67890<br/>"
        "(234) 567-8901 - info@oceanviewresort.com - www.oceanviewresort.com",
        subtitle_style,
    )
    invoice_number = Paragraph("<b>Invoice Number: #12345</b>", styles["Normal"])

    # Spacer
    space_small = Spacer(1, 8)
    space_medium = Spacer(1, 12)

    # BILL TO Section
    bill_to_title = Paragraph("<b>BILL TO</b>", styles["Heading2"])
    bill_to_data = [
        ["Name:", name],
        ["Phone Number:", phoneNo],
        ["Email:", email],
    ]
    bill_to_table = Table(bill_to_data, colWidths=[100, 300])
    bill_to_table.setStyle(
        TableStyle(
            [
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    # Ensure that checkInDate and checkOutDate are datetime.date objects
    if isinstance(checkInDate, str):
        check_in = datetime.strptime(checkInDate, "%Y-%m-%d").date()
    else:
        check_in = checkInDate

    if isinstance(checkOutDate, str):
        check_out = datetime.strptime(checkOutDate, "%Y-%m-%d").date()
    else:
        check_out = checkOutDate

    # Calculate number of nights
    nights = (check_out - check_in).days

    # Calculate total amount based on price per night and nights
    totalAmount = nights * price

    # Add Food Order Data
    food_total = 0
    food_data = [["Food Item", "Price", "Quantity", "Total"]]
    
    for item, quantity, price_per_item in food_orders:
        food_total += quantity * price_per_item
        food_data.append([item, f"{price_per_item:.2f}", quantity, f"{quantity * price_per_item:.2f}"])

    # Combine Room and Food Details
    rent_and_food_total = totalAmount + food_total

    # Add GST (18%)
    gst = rent_and_food_total * 0.18
    total_with_gst = rent_and_food_total + gst

    # Room Details Table
    room_table_data = [
        ["Room Number", "Number of Nights", "Price per Night ($)", "Total ($)"],
        [roomNumber, nights, f"{price:.2f}", f"{totalAmount:.2f}"],
    ]
    room_table = Table(room_table_data, colWidths=[150, 150, 150, 100])
    room_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#004d4d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ]
        )
    )

    # Food Order Table
    food_table = Table(food_data, colWidths=[200, 100, 100, 100])
    food_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#004d4d")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ]
        )
    )

    # Total Amount Section
    total_data = [
        ["Total Amount (Room)", f"{totalAmount:.2f}"],
        ["Total Amount (Food)", f"{food_total:.2f}"],
        ["GST (18%)", f"{gst:.2f}"],
        ["Total Amount Due", f"{total_with_gst:.2f}"]
    ]
    total_table = Table(total_data, colWidths=[400, 100])
    total_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 12),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5d76e")),
            ]
        )
    )

    # Signature Section
    signature_data = [
        ["Cashier's Signature", "Customer's Signature"],
        ["____________________", "____________________"],
    ]
    signature_table = Table(signature_data, colWidths=[250, 250])
    signature_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]
        )
    )

    # Additional Footer Notes
    footer = Paragraph(
        "<b>Description / Copyrights:</b> Read all the Terms and Conditions and Privacy Policies<br/>"
        "<b>Make all checks payable to:</b> Oceanview Resort",
        styles["Normal"],
    )

    # Combine All Elements
    elements = [
        head,
        title,
        subtitle,
        invoice_number,
        space_medium,
        bill_to_title,
        space_small,
        bill_to_table,
        space_medium,
        room_table,
        space_medium,
        food_table,
        space_medium,
        total_table,
        space_medium,
        signature_table,
        space_medium,
        footer,
    ]

    # Build Document
    doc.build(elements)
    buffer.seek(0)

    # Return PDF as Response
    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f"attachment; filename=booking_{bookingId}.pdf"
    )
    return response

@app.route("/room-view")
def room_view():
    rooms = RoomStatus.query.all()  # Contains room statuses
    allRoom = RoomRegistration.query.all()  # Contains all room details
    maxFloor = db.session.query(
        func.max(RoomRegistration.floor)
    ).scalar()  # Get max floor

    new_hotel = create_initial_hotel()

    # Return the template with the data
    return render_template(
        "room-view.html",
        new_hotel=new_hotel,
        rooms=rooms,
        allRoom=allRoom,
        maxFloor=maxFloor,
    )


@app.route("/food-services/<string:bookingid>")
def food_services(bookingid):
    new_hotel = create_initial_hotel()
    randotp = sendemail(bookingid)
    session["otp"] = randotp
    return render_template(
        "food-services.html", new_hotel=new_hotel, bookingid=bookingid, randotp=randotp
    )


@app.route("/food-booking")
def food_booking():
    new_hotel = create_initial_hotel()
    booking = Customer.query.all()
    return render_template("food-booking.html", new_hotel=new_hotel, booking=booking)


@app.route("/all-booking")
def all_booking():
    new_hotel = create_initial_hotel()
    booking = Customer.query.all()
    return render_template("all-booking.html", new_hotel=new_hotel, booking=booking)


# @app.route("/search", methods=["GET", "POST"])
# def search():
#     booking = []  # Default to an empty list of bookings

#     if request.method == "POST":
#         # Get the search inputs
#         booking_id = request.form["bookingId"]
#         booking_name = request.form["bookingName"]

#         # Filter bookings based on input
#         if booking_id:  # Search by booking ID if provided
#             booking = Customer.query.filter(Customer.booking_id == booking_id).all()
#         elif booking_name:  # Search by booking name if provided
#             booking = Customer.query.filter(
#                 Customer.name.ilike(f"%{booking_name}%")
#             ).all()
#         else:
#             booking = Customer.query.all()  # If nothing is entered, show all bookings
#     new_hotel = create_initial_hotel()
#     return render_template("food-booking.html", booking=booking, new_hotel=new_hotel)


class FoodMenu(db.Model):
    id = db.Column(
        db.Integer, primary_key=True, autoincrement=True
    )  # Primary key for each menu item
    menu_item = db.Column(db.String(100), nullable=False)  # Name of the food item
    price = db.Column(db.Float, nullable=False)  # Price of the menu item

    def __init__(self, menu_item, price):
        self.menu_item = menu_item
        self.price = price

    def __repr__(self):
        return f"<FoodMenu {self.menu_item} - ₹{self.price}>"


# Create the database table
with app.app_context():
    db.create_all()

    if not FoodMenu.query.first():  # Check if the table is empty
        drink = FoodMenu(menu_item="Drink", price=199)
        breakfast = FoodMenu(menu_item="Breakfast", price=299)
        lunch = FoodMenu(menu_item="Lunch", price=399)
        dinner = FoodMenu(menu_item="Dinner", price=499)

        db.session.add(drink)
        db.session.add(breakfast)
        db.session.add(lunch)
        db.session.add(dinner)
        db.session.commit()


# OrderFood Table (New table to track food orders)
class OrderFood(db.Model):
    id = db.Column(
        db.Integer, primary_key=True, autoincrement=True
    )  # Primary key for each order
    booking_id = db.Column(db.String(50), nullable=False)  # Booking ID
    name = db.Column(db.String(100), nullable=False)  # Customer Name
    room_number = db.Column(db.String(20), nullable=False)  # Room Number
    phone_no = db.Column(db.String(15), nullable=False)  # Phone Number
    meal_type_id = db.Column(
        db.Integer, db.ForeignKey("food_menu.id"), nullable=False
    )  # Foreign key to FoodMenu
    meal_type = db.relationship(
        "FoodMenu", backref=db.backref("orders", lazy=True)
    )  # Relationship with FoodMenu
    price = db.Column(
        db.Float, nullable=False
    )  # Price of the ordered food (will be taken from FoodMenu)

    def __init__(self, booking_id, name, room_number, phone_no, meal_type_id, price):
        self.booking_id = booking_id
        self.name = name
        self.room_number = room_number
        self.phone_no = phone_no
        self.meal_type_id = meal_type_id
        self.price = price

    def __repr__(self):
        return f"<OrderFood {self.name} ({self.meal_type.menu_item}) - ₹{self.price}>"


# Create the database tables
with app.app_context():
    db.create_all()


# Generate OTP
def generate_otp():
    return random.randint(100000, 999999)


@app.route("/order-food", methods=["GET", "POST"])
def order_food():
    new_hotel = (
        create_initial_hotel()
    )  # Ensure this is available for both GET and POST requests.

    if request.method == "POST":
        # Get form data
        randotp = session["otp"]
        meal_type = request.form["meal_type"]
        bookingid = request.form["bookingid"]
        otp = request.form["otp"]

        if randotp:
            print("OTP received:", randotp)  # You can process the OTP here
        else:
            print("No OTP received.")
        print(int(otp) == int(randotp))
        # Validate input
        if not meal_type or not bookingid or not otp:
            flash("Missing required form data.", "error")
            return render_template("food-services.html", new_hotel=new_hotel)

        # Query for meal and booking details
        meal = FoodMenu.query.filter_by(menu_item=meal_type).first()
        bookingid = Customer.query.filter_by(booking_id=bookingid).first()
        booking = Customer.query.all()

        # Validate queries
        if not meal:
            flash("Selected meal type not found.", "error")
            return render_template("food-services.html", new_hotel=new_hotel)
        if not bookingid:
            flash("Invalid booking ID.", "error")
            return render_template("food-services.html", new_hotel=new_hotel)

        # Validate OTP and create order
        if int(otp) != int(randotp):
            flash("Incorrect OTP!", "danger")
            return render_template(
                "food-booking.html", new_hotel=new_hotel, booking=booking
            )

        try:
            order = OrderFood(
                booking_id=bookingid.booking_id,
                name=bookingid.name,
                room_number=bookingid.room_number,
                phone_no=bookingid.phone_no,
                meal_type_id=meal.id,
                price=meal.price,
            )
            db.session.add(order)
            db.session.commit()

            flash(f"{bookingid.booking_id} Order placed successfully!", "success")
            return render_template(
                "food-booking.html", new_hotel=new_hotel, booking=booking
            )

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", "error")
            return render_template("food-services.html", new_hotel=new_hotel)

    # Handle GET request
    return render_template("food-services.html", new_hotel=new_hotel)


def sendemail(bookingid):

    try:
        app.config["MAIL_SERVER"] = "smtp.gmail.com"
        app.config["MAIL_PORT"] = 587
        app.config["MAIL_USE_TLS"] = True
        app.config["MAIL_USERNAME"] = "ashutoshhsharma2005@gmail.com"
        app.config["MAIL_PASSWORD"] = (
            "emwe ugzu dddu oyqi"  # Use App Passwords if 2FA is enabled
        )
        booking = Customer.query.filter(Customer.booking_id == bookingid).first()
        print(booking.booking_id, booking.email, booking.name)
        mail = Mail(app)

        randotp = generate_otp()
        msg = Message(
            "This is your OTP Verification code: ",
            # sender="ashutoshhsharma2005@gmail.com",
            sender="ashutoshhsharma2005@gmail.com",
            recipients=[booking.email],
        )
        msg.body = f"Your OTP code is: {randotp}"
        mail.send(msg)
        print(booking.email, bookingid)
        return randotp
    except Exception as e:
        print(f"An error occurred: {e}")


@app.route("/invoice-reports")
def invoice_reports():
    # Capture the 'from_date' and 'to_date' from the request arguments (if any)
    from_date = request.args.get("from_date", None)
    to_date = request.args.get("to_date", None)

    # Convert the string dates to datetime objects for comparison
    if from_date:
        from_date = datetime.strptime(from_date, "%d%m%Y")
    if to_date:
        to_date = datetime.strptime(to_date, "%d%m%Y")

    # Query the Customer and filter based on the dates (if provided)
    query = Customer.query

    # If 'from_date' is provided, filter by check-in date
    if from_date:
        query = query.filter(Customer.check_in_date >= from_date)

    # If 'to_date' is provided, filter by check-out date
    if to_date:
        query = query.filter(Customer.check_out_date <= to_date)

    # Execute the query and get the filtered bookings
    booking = query.all()

    # You may also want to call `create_initial_hotel` if needed for the template
    new_hotel = create_initial_hotel()

    # Pass the filtered bookings to the template
    return render_template("invoice-reports.html", new_hotel=new_hotel, booking=booking)


class Staff(db.Model):
    id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    staff_id = db.Column(
        db.String(100), unique=True, nullable=False
    )  # Ensures uniqueness
    email = db.Column(db.String(100), unique=True, nullable=False)  # Ensures uniqueness
    joining_date = db.Column(db.Date, nullable=False)
    phone_no = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.String(200), nullable=False)
    file_upload = db.Column(db.String(255), nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)

    def __repr__(self):
        return f"<Staff(name={self.name}, staff_id={self.staff_id}, email={self.email}, role={self.role})>"


@app.route("/add-staff", methods=["GET", "POST"])
def add_staff():
    if request.method == "POST":
        name = request.form["name"]
        staffId = request.form["staff_id"]
        email = request.form["email"]
        joiningDate = datetime.strptime(request.form["joining_date"], "%d/%m/%Y").date()
        phoneNO = request.form["phone_no"]
        role = request.form["role"]
        salary = request.form["salary"]
        file = request.form["filename"]

        new_staff = Staff(
            name=name,
            staff_id=staffId,
            email=email,
            joining_date=joiningDate,
            phone_no=phoneNO,
            role=role,
            file_upload=file,
            salary = salary,
        )

        db.session.add(new_staff)
        db.session.commit()

        flash(f"{staffId} staff added successfully!", "success")
        return redirect(url_for("add_staff"))

    new_hotel = create_initial_hotel()

    return render_template("add-staff.html", new_hotel=new_hotel)


@app.route("/all-staff")
def all_staffs():
    staffs = Staff.query.all()
    new_hotel = create_initial_hotel()
    return render_template("all-staff.html", new_hotel=new_hotel, staffs=staffs)

@app.route("/staff-profile/<string:staff_id>")
def staff_profile(staff_id):
    new_hotel = tblhotelregistration.query.all()
    staff = Staff.query.filter(Staff.staff_id == staff_id).first()

    return render_template(
        "staff-profile.html",
        new_hotel=new_hotel,
        staff = staff
    )


@app.route("/edit-staff/<int:sno>", methods=['GET','POST'])
def edit_staff(sno):
    staff = Staff.query.filter(Staff.id == sno).first()
    if not staff:
        return "Staff member not found", 404
    new_hotel = create_initial_hotel()
    if request.method == "POST":
        staff.name = request.form["name"]
        staff.staff_id = request.form["staff_id"]
        staff.email = request.form["email"]
        staff.phone_no = request.form["phone_no"]
        staff.role = request.form["role"]

        db.session.commit()
        return redirect(url_for("all_staffs"))

    return render_template("edit-staff.html", new_hotel=new_hotel,staff=staff)

@app.route("/all-rooms")
def all_rooms():
    new_hotel = create_initial_hotel()
    rooms = RoomRegistration.query.all()
    return render_template("all-rooms.html",new_hotel=new_hotel,rooms=rooms)

@app.route("/edit-room/<int:sno>", methods=['GET', 'POST'])
def edit_room(sno):
    # Fetch the room by its ID (room_id)
    room = RoomRegistration.query.filter(RoomRegistration.room_id == sno).first()
    if not room:
        return "Room not found", 404  # Correct error message

    # For displaying related hotel information (if needed)
    new_hotel = create_initial_hotel()
    room_types = RoomType.query.all()
    if request.method == "POST":
        room.room_number = request.form["room_number"]
        room.room_type_id = request.form["room_type_id"]  
        room.floor = request.form["floor"]
        room.area = request.form["area"]
        room.price = request.form["price"]
        room.service_contact_no = request.form["service_contact_no"]

        db.session.commit()

        return redirect(url_for("all_rooms"))

    return render_template("edit-room.html", new_hotel=new_hotel, room=room, room_types=room_types)


@app.route("/payslip")
def payslip():
    new_hotel = create_initial_hotel()
    customer = Customer.query.all()
    return render_template("payslip.html", new_hotel=new_hotel, customer=customer)


@app.route("/final-bill/<string:booking_id>")
def final_bill(booking_id):
    new_hotel = tblhotelregistration.query.all()
    customer = Customer.query.filter(Customer.booking_id == booking_id).first()
    order = OrderFood.query.filter(
        OrderFood.booking_id == booking_id
    ).all()  # Change to .all() to get all orders for the booking ID
    food_type = FoodMenu.query.all()

    # Initialize counters and totals
    welcomeCount = 0
    breakCount = 0
    lunchCount = 0
    dinnerCount = 0
    total_price = 0  # Total price for all food orders

    # Iterate through the order items and count each food type and calculate the total price
    for order_item in order:
        food = FoodMenu.query.filter(FoodMenu.id == order_item.meal_type_id).first()
        if food:
            if food.menu_item == "Welcome drink":
                welcomeCount += 1
            elif food.menu_item == "Breakfast":
                breakCount += 1
            elif food.menu_item == "Lunch":
                lunchCount += 1
            elif food.menu_item == "Dinner":
                dinnerCount += 1

            # Add the price of the food item to the total price
            total_price += food.price  # Assuming 'price' is the attribute of FoodType

    ran = generate_otp()
    return render_template(
        "final-bill.html",
        new_hotel=new_hotel,
        order=order,
        customer=customer,
        ran=ran,
        food_type=food_type,
        welcomeCount=welcomeCount,
        breakCount=breakCount,
        lunchCount=lunchCount,
        dinnerCount=dinnerCount,
        total_price=total_price,
    )


@app.route("/view-notification")
def view_notifications():
    # Ensure that notifications are only created once and avoid duplication
    # Create notifications only once or based on certain conditions
    create_notifications_once()
    
    # notifications = NewNotification.query.all()
    # ac= NewNotification.query.filter(NewNotification.active==False).first()
    # ac.active=True
    # db.session.commit()
    # Initialize the hotel info (you can adjust this if needed)
    new_hotel = create_initial_hotel()
    notifications = NewNotification.query.filter(NewNotification.active==True).order_by(NewNotification.created_at.desc()).all()
    # Render the notification page with all the notifications
    return render_template(
        "view-notification.html", new_hotel=new_hotel, notifications=notifications
    )    

class NewNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    booking_id = db.Column(
        db.String(100),
        db.ForeignKey("customer.booking_id", ondelete="CASCADE"),
        nullable=False,
    )
    message = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    active = db.Column(db.String(255), nullable=False, default=True)
    # Relationship to the AddCustomer model
    customer = db.relationship(
        "Customer", backref=db.backref("notifications", lazy=True)
    )

    def __init__(self, booking_id, message, active):
        self.booking_id = booking_id
        self.message = message
        self.active = active

    def __repr__(self):
        return f"<Notification {self.id} - User {self.booking_id}>"


with app.app_context():
    db.create_all()


def create_notifications_once():
    """
    Create notifications only if they don't already exist.
    This function is designed to be called once to insert notifications if necessary.
    It prevents duplicate notifications when the page is refreshed.
    """
    customers = Customer.query.all()
    orders = OrderFood.query.all()
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    for customer in customers:
        if customer.check_out_date == today:
            existing_notification = NewNotification.query.filter_by(
                    booking_id=customer.booking_id, message="Check Out date is Today", active=True
                ).first()

            if not existing_notification:  # If no such notification exists
                # Create and add the notification
                new_notification = NewNotification(
                    message="Check Out date is Today",
                    booking_id=customer.booking_id,
                    active=True,
                )
                db.session.add(new_notification)
                
        if customer.check_out_date == tomorrow:
            existing_notification = NewNotification.query.filter_by(
                    booking_id=customer.booking_id, message="Check Out date is Tomorrow", active=True
                ).first()

            if not existing_notification:  # If no such notification exists
                # Create and add the notification
                new_notification = NewNotification(
                    message="Check Out date is Tomorrow",
                    booking_id=customer.booking_id,
                    active=True,
                )
                db.session.add(new_notification)
        # Check if the customer has any orders
        for order in orders:
            if order.booking_id == customer.booking_id:
                food_type = FoodMenu.query.filter_by(id=order.meal_type_id).first()
                if food_type:
                    food_name = food_type.menu_item
                    # Check if a notification already exists for this booking_id and message
                    existing_notification = NewNotification.query.filter_by(
                        booking_id=customer.booking_id, message=f"Order food for meal {food_name}", active=True
                    ).first()

                    if not existing_notification:  # If no such notification exists
                        # Create and add the notification
                        new_notification = NewNotification(
                            message=f"Order food for meal {food_name}",
                            booking_id=customer.booking_id,
                            active=True,
                        )
                        db.session.add(new_notification)

    # Commit changes to the database only if new notifications were added
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while creating notifications: {str(e)}", "error")

    # return message

@app.route('/remove/<string:id>')
def remove(id):
    # Fetch the notification that corresponds to the booking_id
    notification = NewNotification.query.filter(NewNotification.id==id).first()

    if notification:
        try:
            # Ensure you're updating the existing notification
            notification.active = False  # Set active to False to mark as inactive

            db.session.commit()  # Commit the changes to the database
            print(f"Notification with booking_id {id} has been deactivated.")
        except Exception as e:
            db.session.rollback()  # Rollback in case of error
            print(f"Error occurred while removing notification: {e}")
    else:
        print(f"No notification found with booking_id {id}")

    # Redirect back to the notifications page
    return redirect(url_for('view_notifications'))




    

@app.route("/customer-profile/<string:booking_id>")
def customer_profile(booking_id):
    new_hotel = tblhotelregistration.query.all()
    customer = Customer.query.filter(Customer.booking_id == booking_id).first()
    order = OrderFood.query.filter(
        OrderFood.booking_id == booking_id
    ).all()  # Change to .all() to get all orders for the booking ID
    food_type = FoodMenu.query.all()

    # Initialize counters and totals
    welcomeCount = 0
    breakCount = 0
    lunchCount = 0
    dinnerCount = 0
    total_price = 0  # Total price for all food orders

    # Iterate through the order items and count each food type and calculate the total price
    for order_item in order:
        food = FoodMenu.query.filter(FoodMenu.id == order_item.meal_type_id).first()
        if food:
            if food.menu_item == "Welcome drink":
                welcomeCount += 1
            elif food.menu_item == "Breakfast":
                breakCount += 1
            elif food.menu_item == "Lunch":
                lunchCount += 1
            elif food.menu_item == "Dinner":
                dinnerCount += 1

            # Add the price of the food item to the total price
            total_price += food.price  # Assuming 'price' is the attribute of FoodType
    return render_template(
        "customer-profile.html",
        new_hotel=new_hotel,
        order=order,
        customer=customer,
        food_type=food_type,
        welcomeCount=welcomeCount,
        breakCount=breakCount,
        lunchCount=lunchCount,
        dinnerCount=dinnerCount,
    )


with app.app_context():
    db.create_all()

@app.route("/generate-pdf/<string:id>")
def generate_pdf(id):
    booking = Customer.query.filter(Customer.booking_id==id).first()
    food_orders = FoodMenu.query.all()
    return generate_hotel_receipt(
            booking.booking_id,
            booking.name,
            booking.phone_no,
            booking.email,
            booking.room_number,
            booking.check_in_date,
            booking.check_out_date,
            booking.price,
            food_orders
        )
# Run the app
if __name__ == "__main__":
    create_initial_hotel()
    app.run(debug=True)

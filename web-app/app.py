"""
File that houses python backend (Flask)
"""

import os
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo.server_api import ServerApi
from pymongo.errors import ConnectionFailure, ConfigurationError
import requests

app = Flask(__name__)

def connect_mongodb():
    """
    Connect to the mongodb atlas database
    """
    # MongoDB connection with error handling
    try:
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGO_URI not found in environment variables")

        db_name = os.getenv("MONGO_DBNAME")
        if not db_name:
            raise ValueError("MONGO_DBNAME not found in environment variables")

        # Update MongoDB connection to use retry writes and server API
        cxn = pymongo.MongoClient(
            mongo_uri, server_api=ServerApi("1"), retryWrites=True, w="majority"
        )
        db = cxn[db_name]
        # Test connection
        cxn.admin.command("ping")
        print(" * Connected to MongoDB Atlas!")

        # Create text index for search functionality
        # db.messages.create_index([("workout_description", "text"), ("meal_name", "text")])
    except (ConnectionFailure, ConfigurationError) as e:
        print(" * MongoDB connection error:", e)
        db = None
    return db


def create_app():
    """
    Create Flask App
    """
    app = Flask(__name__, static_folder="static")
    app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")
    title = ""

    # Load environment variables
    load_dotenv()

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"

    class User(UserMixin):
        """
        User object class for login
        """

        def __init__(self, user_id, username):
            self.id = user_id
            self.username = username

    @login_manager.user_loader
    def load_user(user_id):
        db = app.config["db"]
        if db is not None:
            user_data = db.users.find_one({"_id": ObjectId(user_id)})
            if user_data:
                return User(user_id, user_data["username"])
        return None

    db = connect_mongodb()

    # Store db connection in app config
    app.config["db"] = db

    @app.route("/")
    @login_required
    def home():
        """
        Renders the 'home.html' template and shows a list of .
        """
        db = app.config["db"]
        if db is not None:
            query = {"user": current_user.username}
            docs = db.messages.find(query)
            return render_template("home.html", docs=docs, username=current_user.username)
        return render_template("home.html", docs=[], username=current_user.username)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            db = app.config["db"]
            if db is not None:
                user_data = db.users.find_one({"username": username})
                if user_data and check_password_hash(user_data["password"], password):
                    user = User(user_id=str(user_data["_id"]), username=username)
                    login_user(user)
                    return redirect(url_for("home"))
                return render_template("login.html", error="Invalid credentials")
        return render_template("login.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            db = app.config["db"]
            if db is not None:
                existing_user = db.users.find_one({"username": username})
                if existing_user:
                    return render_template("signup.html", error="User already exists")
                hashed_password = generate_password_hash(password)
                db.users.insert_one({"username": username, "password": hashed_password})
                user_data = db.users.find_one({"username": username})
                user = User(user_id=str(user_data["_id"]), username=username)
                login_user(user)
                return redirect(url_for("onboard"))
        return render_template("signup.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/recordNew")
    @login_required
    def recordNew():
        """
        Renders the 'record.html' template for recording a new workout.
        """
        return render_template("record.html")

    @app.route("/finishRecord")
    @login_required
    def finishRecord():
        # let api finish uploading
        # wait
        # and the route back home
        return render_template("home.html")

    @app.route("/deleteRecord/<recording_id>")
    @login_required
    def deleteRecord(recording_id):
        """Delete a recording"""
        db = app.config["db"]
        if db is not None:
            try:
                # Convert the recording_id to ObjectId
                result = db.speechSummary.delete_one({
                    "_id": ObjectId(recording_id), 
                    "user": current_user.username
                })
            
                if result.deleted_count == 1:
                    # Successfully deleted
                    flash("Recording deleted successfully.", "success")
                else:
                    # No matching recording found
                    flash("Recording not found or you don't have permission to delete it.", "error")
            except Exception as e:
                # Handle any potential errors (e.g., invalid ObjectId)
                flash(f"An error occurred: {str(e)}", "error")
    
        # Redirect back to home page
        return redirect(url_for("home"))

    @app.route("/startRecord", methods=["POST"])
    @login_required
    def start_record():
        title = request.form.get('recording-title')
        response = requests.post(
            'http://voiceai:5001/startRecording',
            timeout=50
        )
        doc = response.json().get("response", "Error")
        doc["title"] = title
        doc["user"] = current_user.username
        db = app.config["db"]
        if db is not None:
            db.speechSummary.insert_one(doc)
        return '', 204

    @app.route("/summaryPage")
    @login_required
    def summary_page(post_id):
        """
        Renders summary page showing the summary of a specific meeting.
        """
        db = app.config["db"]
        if db is not None:
            docs = db.messages.find_one(
                {"_id": ObjectId(post_id), "user": current_user.username}
            )
            return render_template("summary.html", docs=docs)
        return render_template("summary.html", docs=[])

    @app.route("/stop-recording", methods=["POST"])
    def stop_recording():
        requests.post(
            'http://voiceai:5001/stopRecording',
            timeout=50
        )
        print("Received stop signal from frontend.")
        #return jsonify({"status": "recording stopped"})
        return '', 204

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5002)
"""
File that houses python backend (Flask)
"""

import os
import datetime
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
        db = app.config["db"]
        if db is not None:
            # Query the speechSummary collection instead of messages
            query = {"user": current_user.username}
            # Sort by timestamp in descending order (newest first)
            docs = list(db.speechSummary.find(query).sort("timestamp", -1))
        
            # Add this debug print
            for doc in docs:
                print(f"Home page document: {doc['_id']}, title: {doc.get('title')}")
        
            return render_template("home.html", docs=docs, username=current_user.username)
        return render_template("home.html", docs=[], username=current_user.username)

    @app.route("/onboard")
    @login_required
    def onboard():
        """
        Renders the onboarding page for new users.
        """
        return render_template("onboard.html", username=current_user.username)
    
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
                # Convert the recording_id back to ObjectId
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
        transcript = request.form.get('transcript', '')
        response = requests.post(
            'http://localhost:5001/summarize',
            json={"transcript": transcript},
            timeout=60
        )
        doc = response.json().get("response", "Error")
        doc["title"] = title
        doc["user"] = current_user.username
        db = app.config["db"]
        if db is not None:
            db.speechSummary.insert_one(title)
            db.speechSummary.insert_one(doc)
        return '', 204

    @app.route("/summaryPage/<post_id>")
    @login_required
    def summaryPage(post_id):
        db = app.config["db"]
        if db is not None:
            try:
                # Detailed logging
                print("Attempting to retrieve recording:")
                print(f"post_id: {post_id}")
                print(f"Current user: {current_user.username}")
            
                # Find the document
                doc = db.speechSummary.find_one(
                    {"_id": ObjectId(post_id), "user": current_user.username}
                )
            
                # More detailed logging
                if doc:
                    # Convert ObjectId to string
                    doc['_id'] = str(doc['_id'])
                
                    print("Document found:")
                    print(f"Title: {doc.get('title')}")
                    print(f"Transcript length: {len(doc.get('transcript', ''))}")
                    print(f"Summary length: {len(doc.get('summary', ''))}")
                else:
                    print("No document found")
            
                if doc:
                    return render_template("summary.html", doc=doc)
                else:
                    flash("Recording not found.", "error")
                    return redirect(url_for("home"))
        
            except Exception as e:
                print(f"Error retrieving recording: {str(e)}")
                flash("Error retrieving recording details.", "error")
                return redirect(url_for("home"))
    
        flash("Database connection unavailable.", "error")
        return redirect(url_for("home"))

    @app.route("/stop-recording", methods=["POST"])
    def stop_recording():
        requests.post(
            'http://localhost:5001/stopRecording',
            timeout=50
        )
        print("Received stop signal from frontend.")
        return '', 204
    
    @app.route("/summarize-transcript", methods=["POST"])
    @login_required
    def summarize_transcript():
        """
        Receives a transcript from the frontend and sends it to the voiceai service for summarization.
        """
        title = request.form.get('title')
        transcript = request.form.get('transcript')
    
        print(f"Transcript length: {len(transcript)} characters")
    
        try:
            # Send transcript to voiceai service for summarization
            print("Sending transcript to voiceai service...")
            response = requests.post(
                'http://localhost:5001/summarize',
                json={
                    "transcript": transcript
                },
                timeout=60
            )
        
            # Print response status for debugging
            print(f"Response status code: {response.status_code}")
        
            # Get response data
            result = response.json()
            print(f"Response from voiceai: {result}")
        
            summary = result.get("summary", "No summary available")
        
            # Store in database
            db = app.config["db"]
            if db is not None:
                doc = {
                    "title": title or "Voice Recording",
                    "transcript": transcript,
                    "summary": summary,
                    "timestamp": datetime.datetime.now(datetime.UTC),
                    "user": current_user.username
                }
                # Insert the document and get the inserted ID
                inserted_id = db.speechSummary.insert_one(doc).inserted_id
            
                print(f"Recording saved to database with ID: {inserted_id}")
            else:
                print("Warning: Database connection not available")
        
            return jsonify({
                "success": True,
                "summary": summary,
                "recording_id": str(inserted_id) if 'inserted_id' in locals() else None
            })
        
        except Exception as e:
            print(f"Error summarizing transcript: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5002)
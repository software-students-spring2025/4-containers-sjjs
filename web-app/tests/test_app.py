"""program to test app.py file"""
from unittest.mock import patch, MagicMock
import datetime
import pytest
from bson import ObjectId
from werkzeug.security import generate_password_hash
import pymongo
from app import create_app, connect_mongodb  # pylint: disable=import-error


@pytest.fixture(name="app")
def fixture_app(mock_db):
    """Create and configure a new app instance for each test."""
    with patch("app.connect_mongodb", return_value=mock_db):
        app = create_app()
        app.config.update(
            {
                "TESTING": True,
                "WTF_CSRF_ENABLED": False,
            }
        )
    app.config["db"] = mock_db
    return app


@pytest.fixture(name="client")
def fixture_client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(name="mock_db")
def fixture_mock_db():
    """Mock MongoDB connection and database."""
    with patch("pymongo.MongoClient") as mock_client:
        mock_db = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        yield mock_db


def test_mongodb_connection_success():
    """Test successful MongoDB connection."""
    with patch("os.getenv") as mock_getenv:
        mock_getenv.side_effect = ["mongodb://test", "test_db"]

        mock_client = MagicMock()
        mock_client.admin.command.return_value = True
        with patch("pymongo.MongoClient", return_value=mock_client):
            db = connect_mongodb()
            assert db is not None
            mock_client.admin.command.assert_called_once_with("ping")


def test_mongodb_connection_failure():
    """Test MongoDB connection failure."""
    with patch("os.getenv") as mock_getenv:
        mock_getenv.side_effect = ["mongodb://test", "test_db"]

        with patch(
            "pymongo.MongoClient",
            side_effect=pymongo.errors.ConnectionFailure("Connection failed"),
        ):
            db = connect_mongodb()
            assert db is None


def test_home_route_authorized(client, mock_db, app):
    """Test home route with authentication."""
    test_user_id = ObjectId()

    app.config["db"] = mock_db

    hashed_password = generate_password_hash("testpass")

    mock_db.users.find_one.return_value = {
        "_id": test_user_id,
        "username": "testuser",
        "password": hashed_password,
    }

    login_response = client.post(
        "/login", data={"username": "testuser", "password": "testpass"}
    )

    assert login_response.status_code == 302, "Login did not redirect"
    assert login_response.location.endswith("/"), "Did not redirect to home page"

    with client.session_transaction() as session:
        session["_user_id"] = str(test_user_id)

    mock_db.speechSummary.find.return_value.sort.return_value = [
        {
            "_id": ObjectId(),
            "title": "Test Recording",
            "summary": "Test summary",
            "transcript": "Test transcript",
            "user": "testuser",
            "timestamp": datetime.datetime.utcnow(),
        }
    ]

    response = client.get("/")
    assert response.status_code == 200, "Home page access failed"

    mock_db.speechSummary.find.assert_called_once()
    call_args = mock_db.speechSummary.find.call_args[0][0]
    assert call_args == {"user": "testuser"}, "Database query had incorrect parameters"

    mock_db.speechSummary.find.return_value.sort.assert_called_once()
    response_text = response.data.decode("utf-8")
    assert "Test Recording" in response_text, "Recording title not found in response"
    assert "Test summary" in response_text, "Summary not found in response"


def test_login_route_get(client):
    """Test login page access."""
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Login - Speech Summary App" in response.data


def test_login_success(client, mock_db):
    """Test successful login."""
    mock_db.users.find_one.return_value = {
        "_id": ObjectId(),
        "username": "testuser",
        "password": generate_password_hash("testpass"),
    }

    response = client.post(
        "/login", data={"username": "testuser", "password": "testpass"}
    )
    assert response.status_code == 302  # Redirect to home
    assert response.location.endswith("/")


def test_login_invalid_credentials(client, mock_db):
    """Test login with invalid credentials."""
    mock_db.users.find_one.return_value = None

    response = client.post(
        "/login", data={"username": "wronguser", "password": "wrongpass"}
    )
    assert response.status_code == 200
    assert b"Invalid credentials" in response.data


def test_signup_route_get(client):
    """Test signup page access."""
    response = client.get("/signup")
    assert response.status_code == 200
    assert b"Create an Account" in response.data


def test_signup_success(client, mock_db):
    """Test successful signup."""
    mock_db.users.find_one.side_effect = [
        None,
        {"_id": ObjectId(), "username": "newuser"},
    ]
    mock_db.users.insert_one.return_value = MagicMock(inserted_id=ObjectId())

    response = client.post(
        "/signup", data={"username": "newuser", "password": "newpass"}
    )
    assert response.status_code == 302  # Redirect to onboard
    assert response.location.endswith("/onboard")


def test_signup_existing_user(client, mock_db):
    """Test signup with existing username."""
    mock_db.users.find_one.return_value = {"username": "existinguser"}

    response = client.post(
        "/signup", data={"username": "existinguser", "password": "newpass"}
    )
    assert response.status_code == 200
    assert b"User already exists" in response.data


def test_onboard_route_authorized(client, mock_db):
    """Test onboard route with authentication."""
    # Login
    mock_db.users.find_one.return_value = {
        "_id": ObjectId(),
        "username": "testuser",
        "password": generate_password_hash("testpass"),
    }
    client.post("/login", data={"username": "testuser", "password": "testpass"})

    response = client.get("/onboard")
    assert response.status_code == 200
    assert b"Let's get you started with creating your first recording." in response.data


def test_logout(client, mock_db):
    """Test logout functionality."""
    # login
    mock_db.users.find_one.return_value = {
        "_id": ObjectId(),
        "username": "testuser",
        "password": generate_password_hash("testpass"),
    }
    client.post("/login", data={"username": "testuser", "password": "testpass"})

    # logout
    response = client.get("/logout")
    assert response.status_code == 302  # Redirect to login
    assert response.location.endswith("/login")


def test_summary_page_route(client, mock_db):
    """Test summary page route with authentication."""
    # Login
    mock_db.users.find_one.return_value = {
        "_id": ObjectId(),
        "username": "testuser",
        "password": generate_password_hash("testpass"),
    }
    client.post("/login", data={"username": "testuser", "password": "testpass"})

    test_id = ObjectId()
    mock_db.speechSummary.find_one.return_value = {
        "_id": test_id,
        "user": "testuser",
        "title": "Test Recording",
        "summary": "Test summary",
        "transcript": "Test transcript",
        "timestamp": datetime.datetime.utcnow(),
    }

    response = client.get(f"/summaryPage/{str(test_id)}")
    html = response.data.decode("utf-8")
    assert response.status_code == 200
    assert "Test Recording" in html
    assert "Test summary" in html
    assert "Test transcript" in html


def test_delete_record_route(client, mock_db):
    """Test delete_record route"""
    # Login
    mock_db.users.find_one.return_value = {
        "_id": ObjectId(),
        "username": "testuser",
        "password": generate_password_hash("testpass"),
    }
    client.post("/login", data={"username": "testuser", "password": "testpass"})

    # Create a test record ID
    test_id = str(ObjectId())

    response = client.get(f"/deleteRecord/{test_id}")

    # Verify redirect to home page
    assert response.status_code == 302
    assert response.location.endswith("/")

    # Verify deletion was called with correct parameters
    mock_db.speechSummary.delete_one.assert_called_once_with(
        {"_id": ObjectId(test_id), "user": "testuser"}
    )

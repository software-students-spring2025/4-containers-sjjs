import pytest
from unittest.mock import patch, MagicMock
from flask import url_for, session
from bson import ObjectId
from werkzeug.security import generate_password_hash
from app import create_app, connect_mongodb

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    return app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def mock_db():
    """Mock MongoDB connection and database."""
    with patch('pymongo.MongoClient') as mock_client:
        mock_db = MagicMock()
        mock_client.return_value.__getitem__.return_value = mock_db
        yield mock_db

def test_mongodb_connection_success(mock_db):
    """Test successful MongoDB connection."""
    with patch('os.getenv') as mock_getenv:
        mock_getenv.side_effect = ['mongodb://test', 'test_db']
        
        db = connect_mongodb()
        assert db is not None
        mock_db.admin.command.assert_called_once_with('ping')

def test_mongodb_connection_failure():
    """Test MongoDB connection failure."""
    with patch('pymongo.MongoClient', side_effect=Exception('Connection failed')):
        db = connect_mongodb()
        assert db is None

def test_home_route_unauthorized(client):
    """Test home route without authentication."""
    response = client.get('/')
    assert response.status_code == 302#Redirect to login
    assert response.location.endswith('/login')

def test_home_route_authorized(client, mock_db):
    """Test home route with authentication."""
    #Login
    mock_db.users.find_one.return_value = {
        '_id': ObjectId(),
        'username': 'testuser',
        'password': generate_password_hash('testpass')
    }
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    #Mock recordings
    mock_db.messages.find.return_value = [{
        '_id': ObjectId(),
        'title': 'Test Recording',
        'status': 'completed',
        'summary': 'Test summary',
        'transcript': 'Test transcript'
    }]
    
    response = client.get('/')
    html_content = response.data.decode('utf-8')
    
    # Check template elements
    assert 'Welcome, testuser!' in html_content
    assert 'Test Recording' in html_content
    assert 'Test summary' in html_content
    assert 'Test transcript' in html_content
    assert 'New Recording' in html_content

def test_login_route_get(client):
    """Test login page access."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Login - Speech Summary App' in response.data

def test_login_success(client, mock_db):
    """Test successful login."""
    mock_db.users.find_one.return_value = {
        '_id': ObjectId(),
        'username': 'testuser',
        'password': generate_password_hash('testpass')
    }
    
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    assert response.status_code == 302#Redirect to home
    assert response.location.endswith('/')

def test_login_invalid_credentials(client, mock_db):
    """Test login with invalid credentials."""
    mock_db.users.find_one.return_value = None
    
    response = client.post('/login', data={
        'username': 'wronguser',
        'password': 'wrongpass'
    })
    assert response.status_code == 200
    assert b'Invalid credentials' in response.data

def test_signup_route_get(client):
    """Test signup page access."""
    response = client.get('/signup')
    assert response.status_code == 200
    assert b'Create an Account' in response.data

def test_signup_success(client, mock_db):
    """Test successful signup."""
    mock_db.users.find_one.return_value = None #User doesn't exist
    mock_db.users.insert_one.return_value = MagicMock(inserted_id=ObjectId())
    
    response = client.post('/signup', data={
        'username': 'newuser',
        'password': 'newpass'
    })
    assert response.status_code == 302 #Redirect to onboard
    assert response.location.endswith('/onboard')

def test_signup_existing_user(client, mock_db):
    """Test signup with existing username."""
    mock_db.users.find_one.return_value = {'username': 'existinguser'}
    
    response = client.post('/signup', data={
        'username': 'existinguser',
        'password': 'newpass'
    })
    assert response.status_code == 200
    assert b'User already exists' in response.data

def test_onboard_route_unauthorized(client):
    """Test onboard route without authentication."""
    response = client.get('/onboard')
    assert response.status_code == 302 #Redirect to login
    assert response.location.endswith('/login')

def test_onboard_route_authorized(client, mock_db):
    """Test onboard route with authentication."""
    #Login
    mock_db.users.find_one.return_value = {
        '_id': ObjectId(),
        'username': 'testuser',
        'password': generate_password_hash('testpass')
    }
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    response = client.get('/onboard')
    assert response.status_code == 200
    assert b'Onboard' in response.data

def test_logout(client, mock_db):
    """Test logout functionality."""
    #login
    mock_db.users.find_one.return_value = {
        '_id': ObjectId(),
        'username': 'testuser',
        'password': generate_password_hash('testpass')
    }
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    #logout
    response = client.get('/logout')
    assert response.status_code == 302 #Redirect to login
    assert response.location.endswith('/login')

"""def test_summary_page_route_authorized(client, mock_db):
    Test summary page route with authentication.
    #Login
    mock_db.users.find_one.return_value = {
        '_id': ObjectId(),
        'username': 'testuser',
        'password': generate_password_hash('testpass')
    }
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    
    test_id = ObjectId()
    mock_db.messages.find_one.return_value = {
        '_id': test_id,
        'user': 'testuser',
        'content': 'Test content'
    }
    
    response = client.get(f'/summaryPage?post_id={str(test_id)}')
    assert response.status_code == 200
    assert b'Summary' in response.data"""

"""def test_summary_page_not_found(client, mock_db):
    #Test summary page with non-existent post.
    #Login
    mock_db.users.find_one.return_value = {
        '_id': ObjectId(),
        'username': 'testuser',
        'password': generate_password_hash('testpass')
    }
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    #Mock no message found
    mock_db.messages.find_one.return_value = None
    
    response = client.get(f'/summaryPage?post_id={str(ObjectId())}')
    assert response.status_code == 200
    assert b'Summary' in response.data"""

"""
def test_record_new_route_authorized(client, mock_db):
    #Test record_new route with authentication.
    #Login
    mock_db.users.find_one.return_value = {
        '_id': ObjectId(),
        'username': 'testuser',
        'password': generate_password_hash('testpass')
    }
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    response = client.get('/recordNew')
    assert response.status_code == 200
    assert b'Record' in response.data

def test_finish_record_route_authorized(client, mock_db):
    #Test finish_record route with authentication.
    #Login
    mock_db.users.find_one.return_value = {
        '_id': ObjectId(),
        'username': 'testuser',
        'password': generate_password_hash('testpass')
    }
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    response = client.get('/finishRecord')
    assert response.status_code == 200
    assert b'Home' in response.data

def test_start_record_route_authorized(client, mock_db):
    #Test start_record route with authentication.
    #Login
    mock_db.users.find_one.return_value = {
        '_id': ObjectId(),
        'username': 'testuser',
        'password': generate_password_hash('testpass')
    }
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    response = client.get('/startRecord')
    assert response.status_code == 200

def test_delete_record_route_authorized(client, mock_db):
    #Test delete_record route with authentication.
    #Login
    mock_db.users.find_one.return_value = {
        '_id': ObjectId(),
        'username': 'testuser',
        'password': generate_password_hash('testpass')
    }
    client.post('/login', data={
        'username': 'testuser',
        'password': 'testpass'
    })
    
    response = client.get('/deleteRecord')
    assert response.status_code == 200
"""

![Lint-free](https://github.com/nyu-software-engineering/containerized-app-exercise/actions/workflows/lint.yml/badge.svg)
[![Web App CI](https://github.com/software-students-spring2025/4-containers-sjjs/actions/workflows/web-app.yaml/badge.svg)](https://github.com/software-students-spring2025/4-containers-sjjs/actions/workflows/web-app.yaml)
[![ML Client CI](https://github.com/software-students-spring2025/4-containers-sjjs/actions/workflows/ml-client.yaml/badge.svg)](https://github.com/software-students-spring2025/4-containers-sjjs/actions/workflows/ml-client.yaml)

# Containerized App Exercise

This project is a containerized web application that gathers data through the microphone and uses machine learning to summarize and organize the speech data into coherent and organized notes. The system consists of three main components:

1. A web application that provides a user interface for uploading and managing speech data
2. A machine learning service that processes the speech data
3. A MongoDB database that stores the processed results

## Team Members

* [Jake Chang](https://github.com/jakechang1284)
* [Jeffrey Chen](https://github.com/JeffreyChen112)
* [Samir Hussain](https://github.com/Samir2324)
* [Shaurya Srivastava](https://github.com/shauryasr04)

## Project Setup and Configuration

### Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/software-students-spring2025/4-containers-sjjs.git
cd 4-containers-sjjs
```

2. Create environment files:
   - Create a `.env` file in the root directory with the following content:
```
MONGO_URI="your_mongodb_connection_string"
MONGO_DBNAME="speechSummary"
SECRET_KEY="your_secret_key_here"
FLASK_APP=app.py
FLASK_ENV=development
FLASK_PORT=5002
```

3. Build and start the containers:
```bash
docker-compose up --build
```

The application will be available at http://localhost:5002/ where you can interact with the web app. 

### Database Setup

The MongoDB database will be automatically initialized when the containers start.

### Environment Variables

The following environment variables are required for the application to function:

- `MONGO_URI`: MongoDB connection string
- `MONGO_DBNAME`: Name of the MongoDB database
- `SECRET_KEY`: Flask secret key for session management
- `FLASK_APP`: Name of the Flask application file
- `FLASK_ENV`: Flask environment (development/production)
- `FLASK_PORT`: Port number for the Flask application

### Troubleshooting

If you encounter any issues:

1. Check if all containers are running:
```bash
docker-compose ps
```

2. View container logs:
```bash
docker-compose logs
```

3. Rebuild containers if needed:
```bash
docker-compose down
docker-compose up --build
```

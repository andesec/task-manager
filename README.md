# Task Manager

A simple web-based task manager application built with FastAPI, PostgreSQL, and Docker.

## Features

*   **Web-based UI:** A clean, mobile-friendly interface for managing tasks.
*   **Task Management:** Create, view, complete, and delete tasks.
*   **Pending and Completed Views:** Tasks are separated into pending and completed lists.
*   **Database Persistence:** Tasks are stored in a PostgreSQL database.
*   **Containerized:** The entire application and database are containerized using Docker and Docker Compose for easy setup and deployment.
*   **Hot Reloading:** The application automatically reloads on code changes for a smooth development experience.

## Technologies Used

*   **Backend:** FastAPI
*   **Database:** PostgreSQL
*   **ORM:** SQLAlchemy
*   **Frontend:** Jinja2 Templates, Bootstrap
*   **Containerization:** Docker, Docker Compose
*   **Python Environment:** uv

## Getting Started

### Prerequisites

*   Docker
*   Docker Compose
*   An internet connection (to pull Docker images and download dependencies)

### Running the Application

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/andesec/task-manager.git
    cd task-manager
    ```

2.  **Run with Docker Compose:**
    ```bash
    docker-compose up --build
    ```

3.  **Access the application:**
    *   Open your browser and navigate to `http://localhost:8000`.
    *   If you are using OrbStack, you can also access the application at `http://app.task-manager.orb.local`.

## Development

The application is configured for hot reloading. Simply make changes to the source code, and the application will automatically restart to apply the changes.

## API Endpoints

*   `GET /`: Renders the main page with the task lists.
*   `POST /add`: Adds a new task.
*   `GET /complete/{task_id}`: Marks a task as complete.
*   `GET /delete/{task_id}`: Deletes a task.
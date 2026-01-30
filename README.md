# Cloud Storage

## About

Cloud Storage is a web application for uploading, storing, and sharing files securely.  
Users can manage their personal files, collaborate with other users, and view analytical statistics about their storage usage.

The project is built with Django REST Framework and integrates with a [centralized authentication service](https://github.com/preobart/id), providing both JWT and session-based authentication for secure and unified user access.

## Setup

1. Set up environment variables in the `.env` file.

2. Run the services with the following command and navigate to [`http://localhost:8082`](http://localhost:8082):
    ```bash
    make up
    ```

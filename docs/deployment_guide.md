# CI Orchestrator - Deployment Guide

This guide provides instructions for deploying the CI Orchestrator agent.

## Prerequisites

- Python 3.9+
- Pip (Python package installer)
- A Manus account and API key

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd ci_orchestrator
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Set up environment variables:**

    Create a `.env` file in the root of the project and add the following:

    ```
    MANUS_API_KEY=your_manus_api_key
    ```

2.  **Configure the agent:**

    The agent is configured through the API request body. Refer to the [API Documentation](api_documentation.md) for details on the request parameters.

## Running the Agent

The agent is designed to be run as a service that listens for API requests. You can use a production-ready ASGI server like Uvicorn to run the agent.

```bash
cd src
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

This will start the agent on `http://0.0.0.0:8000`.

## Deployment to Production

For production deployment, it is recommended to use a process manager like Gunicorn or Supervisor to manage the Uvicorn process.

### Example with Gunicorn

1.  **Install Gunicorn:**

    ```bash
    pip install gunicorn
    ```

2.  **Run the agent with Gunicorn:**

    ```bash
    cd src
    gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.main:app --bind 0.0.0.0:8000
    ```

    This will start 4 worker processes to handle requests.

## Testing

The agent includes a suite of tests to ensure its functionality and brand-neutrality. To run the tests, use `pytest`:

```bash
pytest
```

You can also run the brand-neutral test script directly:

```bash
python3 test_brand_neutral.py
```

## Monitoring

The agent uses `structlog` for structured logging. Logs are printed to standard output and can be collected and forwarded to a logging service of your choice.

## Error Handling

The agent is designed to be resilient and handle errors gracefully. Refer to the [API Documentation](api_documentation.md) for details on the error handling strategy.



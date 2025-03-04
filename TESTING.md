# Testing Environment for Neutral News

This document describes how to set up and use the testing environment for the Neutral News application.

## Overview

The testing environment allows you to run and test the Neutral News application locally without affecting the production environment on render.com. It provides:

1. A separate configuration system for testing
2. Mock implementations of API services to avoid making real API calls
3. A test server that runs on a different port than the production server
4. Comprehensive test cases for unit and integration testing

## Setup

To set up the testing environment, follow these steps:

1. Run the setup script:

```bash
python setup_test_env.py
```

This will create:
- A `.env.test` file with test environment variables
- A `test.sh` script to run the test server
- A `tests` directory with test files
- A `pytest.ini` configuration file

2. If you want to use real API keys for some tests, run:

```bash
python setup_test_env.py --use-real-apis
```

This will add placeholders for real API keys in the `.env.test` file that you can fill in.

## Configuration

The testing environment uses a separate configuration file (`config_test.py`) that is designed for testing:

- It uses mock API keys by default
- It has reduced limits for faster testing (fewer articles, shorter summaries)
- It enables debug mode
- It uses an in-memory cache

You can modify the test configuration in `config_test.py` without affecting the production configuration.

## Running the Test Server

To run the test server:

```bash
./test.sh
```

This will start the Flask application using the test configuration on port 10001 (by default).

You can access the test server at http://localhost:10001

## Running Tests

The testing environment includes comprehensive tests using both unittest and pytest:

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_comprehensive.py

# Run a specific test
pytest tests/test_comprehensive.py::test_search_functionality_pytest
```

## Mock Services

The testing environment includes mock implementations of key services:

- `mock_data.py`: Contains mock data for testing (articles, API responses)
- `mock_services.py`: Contains mock implementations of API fetchers and processors

These mock services allow you to test the application without making real API calls.

## Using Real APIs in Testing

If you want to test with real APIs:

1. Edit the `.env.test` file and add your test API keys
2. Set the corresponding feature flags to 1 (e.g., `TEST_USE_NEWSAPI_ORG=1`)
3. Run the test server or tests as usual

## Debugging

The test server runs in debug mode, which provides:

- Detailed error messages
- Auto-reloading when code changes
- A debugger interface in the browser

You can also use logging for debugging:

```python
import logging
logger = logging.getLogger(__name__)
logger.debug("Debug message")
```

## Adding New Tests

To add new tests:

1. Create a new file in the `tests` directory with a name starting with `test_`
2. Write your tests using unittest or pytest
3. Run the tests with pytest

## Troubleshooting

If you encounter issues with the testing environment:

1. Check the logs for error messages
2. Verify that the `.env.test` file has the correct configuration
3. Make sure the test server is running on the correct port
4. Check that the mock services are properly configured

## Keeping Test and Production Environments Separate

The testing environment is designed to be completely separate from the production environment:

- It uses different configuration files
- It runs on a different port
- It uses mock services by default
- Test-specific files are excluded from git

This ensures that your testing activities won't affect the production environment on render.com. 
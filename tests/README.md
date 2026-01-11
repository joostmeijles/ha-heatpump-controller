# Heatpump Controller Tests

This directory contains comprehensive unit tests for the heatpump controller refactored modules.

## Running Tests

### Install Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest tests/
```

### Run Tests with Coverage

```bash
pytest tests/ --cov=config/custom_components/heatpump_controller --cov-report=html
```

### Run Specific Test File

```bash
pytest tests/test_calculations.py -v
```

## Test Structure

- **conftest.py** - Pytest fixtures and test configuration
- **test_calculations.py** - Tests for pure calculation functions (21 tests)
- **test_room_temperature_reader.py** - Tests for room temperature reading logic (13 tests)
- **test_outdoor_temperature.py** - Tests for outdoor temperature management (18 tests)
- **test_hvac_controller.py** - Tests for HVAC decision logic (23 tests)

## Coverage

Current test coverage for refactored modules:
- calculations.py: 100%
- hvac_controller.py: 100%
- room_temperature_reader.py: 100%
- outdoor_temperature.py: 95%

Total: 75 tests, all passing

## Type Checking

The code passes strict type checking with pyright:

```bash
pyright config/custom_components/heatpump_controller/
```

## Continuous Integration

Tests are automatically run via GitHub Actions on:
- Pull requests to main branch
- Pushes to main branch

See `.github/workflows/tests.yml` for the CI configuration.

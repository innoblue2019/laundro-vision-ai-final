# LaundroVision AI

## Product Overview

- **Product Name**: **LaundroVision AI**
- **Positioning**: An AI-driven self-service laundromat site selection decision system that combines **Location
  Intelligence** with advanced analytical models.
- **Core Value**: By using AI to deeply analyze **residential structures, demographic characteristics, and qualitative
  competitive data**, the system helps investors and store operators start from **renter-driven demand**, enabling
  precise site selection and a clear path to break-even.

## Running the Backend Service

### Prerequisites

- **Python 3.11+** (recommended)
- **uv** package manager. Install it via:

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- Create a virtual environment (optional, uv handles isolation automatically).
- You may need to install Python interpreter if you don't have one in your local environment.

```bash
uv python install 3.11
```

### Environment Configuration

1. Copy the example environment file:

   ```bash
   cd /path/to/laundro-vision-ai
   cp .env.example .env
   ```

2. Edit `.env` to set required variables (e.g., database URL, API keys). The file includes comments for each variable.

### Install Dependencies

```bash
uv sync
```

This will install all packages defined in `pyproject.toml` into an isolated environment.

### Run the Service

```bash
uv run uvicorn laundro_vision_ai.api.main:app
```

The API will start on the host/port defined in your `.env` (default `http://127.0.0.1:8000`).

### Development Mode

For hot‑reloading during development, use:

```bash
uv run uvicorn laundro_vision_ai.api.main:app --reload
```

### Testing

Run the test suite to ensure everything works:

```bash
uv run pytest
```

---

For more detailed deployment instructions, refer to the `docs/` directory.

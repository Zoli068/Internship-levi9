# data-ai-praksa-2026

This repository contains infrastructure code (AWS CDK), service code, and tests for the 2026 Data/AI internship project, developed by a team of three.

This project is an end-to-end cloud platform for air quality monitoring that ingests and correlates data from multi-location IoT sensors and public weather APIs using AWS Lambda. The data pipeline leverages Amazon S3 for storage, AWS Glue and Step Functions for ETL orchestration, Amazon Athena for querying, and Grafana for visual analytics. Additionally, an AI agent powered by AWS Bedrock is integrated to enable conversational interaction with the processed data. The entire cloud infrastructure is defined as Infrastructure as Code using AWS CDK, supported by an automated CI/CD deployment pipeline.

## Prerequisites

Before working with this repo, make sure you have:

1. `uv` installed
2. Python `3.11+` installed
3. AWS credentials configured (for CDK deploy)
4. AWS CDK Toolkit (`cdk` CLI) installed

### 1) Install uv

Official installation instructions: https://docs.astral.sh/uv/getting-started/installation/

Quick install (Linux/macOS):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify:

```bash
uv --version
```

### 2) Verify Python version (3.11+)

```bash
python3 --version
```

If your default Python is older than 3.11, install Python 3.11+ and ensure it is available in your PATH.

## Getting Started After Clone

From the project root, run:

```bash
uv sync --dev
```

This command creates/updates the local virtual environment and installs both runtime and development dependencies.

You can run all project commands through `uv run` without manually activating a venv.

## Run Tests Locally

Run the full test suite:

```bash
uv run pytest
```

The project is configured with coverage and strict thresholds in `pyproject.toml`, so this command also enforces coverage requirements.

## Project Structure

```text
infra/
	app.py                # CDK app entrypoint
	cdk.json              # CDK configuration
	stacks/
		infra_stack.py      # Main infrastructure stack (S3 bucket, etc.)

services/
	...                   # Application/service code (business logic)

tests/
	infra/
		test_infra_stack.py # Infrastructure unit tests (CDK assertions)
	services/
		...                 # Service-level tests
```

### What belongs where

- `infra/`: AWS infrastructure definitions using CDK.
- `services/`: Python application/services code.
- `tests/`: Automated tests for both infrastructure and services.

## AWS CDK Commands Through uv

All commands below are run from the project root and execute CDK using the Python environment managed by `uv`.

## Working With Multiple Interns (Manual Naming)

If multiple interns deploy from this same project, each intern must manually use unique names.

### What each intern must change

1. Stack name in `infra/app.py`
2. Resource names in `infra/stacks/infra_stack.py` (for example S3 `bucket_name`)
3. Related test expectations in `tests/infra/test_infra_stack.py` if names are asserted

### Example naming convention

Use an intern suffix everywhere, for example `-ana`:

- Stack name: `InfraStack-ana`
- S3 bucket name: `data-ai-praksa-ana`

This avoids conflicts when different interns deploy to the same AWS account/region.

### Important

- `construct_id` should be unique per intern (for example `InfraStack-ana`).
- Physical resource names must also be unique (for example S3 bucket names are globally unique).
- If two interns keep the same names, one deployment will fail because resources already exist.

### Synthesize CloudFormation template

```bash
uv run --directory infra cdk synth --app "uv run python app.py"
```

### Bootstrap environment (first time per account/region)

```bash
uv run --directory infra cdk bootstrap --app "uv run python app.py"
```

### Deploy stack

```bash
uv run --directory infra cdk deploy InfraStack --app "uv run python app.py"
```

If you renamed your stack for your intern user, deploy with that name instead, for example:

```bash
uv run --directory infra cdk deploy InfraStack-ana --app "uv run python app.py"
```

### Destroy stack

```bash
uv run --directory infra cdk destroy InfraStack --app "uv run python app.py"
```

If you renamed your stack, destroy using the same custom name, for example:

```bash
uv run --directory infra cdk destroy InfraStack-ana --app "uv run python app.py"
```

## Notes

- Ensure AWS credentials are configured (`aws configure` or environment variables).
- Confirm your target region/account before deployment.
- If `cdk` is not found, install AWS CDK Toolkit globally:

```bash
npm install -g aws-cdk
```
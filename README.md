# django-cloudrun-job

Run any Django management command as a [Google Cloud Run Job](https://cloud.google.com/run/docs/create-jobs) — with a single command.

```bash
./manage.py run_remote migrate
./manage.py run_remote machine_translate_all --language sw
./manage.py run_remote long_running_import --file data.csv
```

**Zero config for image, env vars, secrets, or Cloud SQL.** The library reads your deployed Cloud Run *Service* and clones its entire configuration into a matching Cloud Run *Job* automatically.

## Why?

Cloud Run **services** have a 60-minute request timeout. Cloud Run **jobs** support up to **24 hours**. This library lets you run long management commands (data migrations, bulk translations, imports) on the same infrastructure as your web app — same image, same database, same secrets — without any manual job configuration.

## Installation

```bash
pip install django-cloudrun-job
```

## Setup

1. Add to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "django_cloudrun_job",
]
```

2. Add the config to your Django settings:

```python
CLOUDRUN_REMOTE = {
    "PROJECT_ID": "my-gcp-project",
    "REGION": "europe-west2",
    "SERVICE": "my-service",  # your Cloud Run service name
}
```

That's it. The library reads everything else from your deployed service.

## Usage

```bash
# Run a management command on Cloud Run (waits for completion)
./manage.py run_remote my_command --arg1 value1

# Fire and forget
./manage.py run_remote --no-wait my_command --arg1 value1

# Custom timeout (default is 24 hours)
./manage.py run_remote --timeout 3600 my_command
```

### What happens under the hood

1. **Reads** your deployed Cloud Run Service config (image, env vars, secrets, Cloud SQL connections, service account, resource limits)
2. **Creates** (or updates) a Cloud Run Job called `{service}-mgmt` with the same config
3. **Runs** the job with `python manage.py <your command>` as the entrypoint
4. **Waits** for completion (unless `--no-wait`) and prints a link to the GCP Console

## Settings reference

```python
CLOUDRUN_REMOTE = {
    # Required
    "PROJECT_ID": "my-gcp-project",
    "SERVICE": "my-service",

    # Optional
    "REGION": "us-central1",          # default: us-central1
    "JOB_NAME": "my-service-mgmt",    # default: {SERVICE}-mgmt
    "TIMEOUT": 86400,                 # default: 86400 (24 hours)
    "CREDENTIALS": "/path/to/key.json",  # default: Application Default Credentials
}
```

## Requirements

- Python 3.9+
- Django 4.2+
- `google-cloud-run` (installed automatically)
- A deployed Cloud Run service
- GCP credentials with `roles/run.admin` (or `run.jobs.create`, `run.jobs.run`, `run.services.get`)

## How it works

```
┌─────────────────┐         ┌──────────────────────┐
│  ./manage.py    │         │  Cloud Run Service    │
│  run_remote ... │────────▶│  (reads config)       │
└────────┬────────┘         └──────────────────────┘
         │
         │  clones image, env, secrets,
         │  Cloud SQL, service account
         ▼
┌─────────────────────────────────────────┐
│  Cloud Run Job: {service}-mgmt          │
│                                         │
│  python manage.py <your command>        │
│  timeout: up to 24 hours               │
│  retries: 0                            │
└─────────────────────────────────────────┘
```

The job template is updated on every run, so it always matches your latest deployed service (new image, new env vars, etc).

## License

MIT


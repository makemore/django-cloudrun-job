"""
Settings helper for django-cloudrun-job.

Add to your Django settings::

    CLOUDRUN_REMOTE = {
        "PROJECT_ID": "my-gcp-project",
        "REGION": "europe-west2",
        "SERVICE": "my-service",          # Cloud Run service to clone config from
        # Optional overrides:
        # "JOB_NAME": "my-service-mgmt",  # default: {SERVICE}-mgmt
        # "TIMEOUT": 86400,               # default: 24 hours
        # "CREDENTIALS": "/path/to/key.json",  # default: ADC
    }
"""
from django.conf import settings

DEFAULTS = {
    "PROJECT_ID": None,
    "REGION": "us-central1",
    "SERVICE": None,
    "JOB_NAME": None,
    "TIMEOUT": 86400,
    "CREDENTIALS": None,
}


def get_config():
    user = getattr(settings, "CLOUDRUN_REMOTE", {})
    config = {**DEFAULTS, **user}
    if config["JOB_NAME"] is None and config["SERVICE"]:
        config["JOB_NAME"] = f"{config['SERVICE']}-mgmt"
    return config


"""
Core logic for creating and running Cloud Run Jobs.

Reads a deployed Cloud Run Service's config (image, env, secrets,
Cloud SQL volumes, service account) and creates a matching Job that
executes a Django management command.
"""


def get_credentials(config):
    """Return explicit credentials or *None* (= use ADC)."""
    path = config.get("CREDENTIALS")
    if not path:
        return None
    from google.oauth2 import service_account

    return service_account.Credentials.from_service_account_file(path)


def get_service(run_v2, creds, project, region, name):
    """Fetch the Cloud Run Service resource."""
    client = run_v2.ServicesClient(credentials=creds)
    path = f"projects/{project}/locations/{region}/services/{name}"
    return client.get_service(name=path)


def build_job_spec(run_v2, duration_pb2, service, container, timeout):
    """
    Build a Cloud Run Job spec that mirrors the given service's config.

    Copies image, env vars, secrets, resource limits, volumes (incl.
    Cloud SQL), and service account from the service template.
    """
    return run_v2.Job(
        template=run_v2.ExecutionTemplate(
            template=run_v2.TaskTemplate(
                containers=[
                    run_v2.Container(
                        image=container.image,
                        env=list(container.env),
                        command=["python", "manage.py"],
                        resources=container.resources,
                        volume_mounts=list(container.volume_mounts),
                    )
                ],
                volumes=list(service.template.volumes),
                service_account=service.template.service_account,
                timeout=duration_pb2.Duration(seconds=timeout),
                max_retries=0,
            ),
        ),
    )


def ensure_job(jobs_client, spec, parent, job_path, job_name):
    """
    Create or update the Cloud Run Job template.

    Returns ``"created"`` or ``"updated"``.
    """
    try:
        jobs_client.get_job(name=job_path)
        spec.name = job_path
        jobs_client.update_job(job=spec).result()
        return "updated"
    except Exception:
        jobs_client.create_job(
            parent=parent, job=spec, job_id=job_name
        ).result()
        return "created"


def run_job(jobs_client, run_v2, duration_pb2, job_path, cmd_parts, timeout):
    """Execute the job with command overrides and return the operation."""
    request = run_v2.RunJobRequest(
        name=job_path,
        overrides=run_v2.RunJobRequest.Overrides(
            container_overrides=[
                run_v2.RunJobRequest.Overrides.ContainerOverride(
                    args=cmd_parts,
                ),
            ],
            timeout=duration_pb2.Duration(seconds=timeout),
        ),
    )
    return jobs_client.run_job(request=request)


def get_console_url(operation, project):
    """Extract the GCP Console URL from the operation metadata."""
    meta = operation.metadata
    name = getattr(meta, "name", "") if meta else ""
    if not name:
        return None
    parts = name.split("/")
    if len(parts) < 8:
        return None
    short = "/".join(parts[5:])
    return (
        f"https://console.cloud.google.com/run/"
        f"{short}/tasks?project={project}"
    )


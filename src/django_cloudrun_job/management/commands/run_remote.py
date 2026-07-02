"""Run a Django management command as a Google Cloud Run Job."""
import argparse
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run a Django management command as a Cloud Run Job."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-wait", action="store_true", dest="no_wait",
            help="Start the job and return immediately.",
        )
        parser.add_argument(
            "--timeout", type=int, default=None,
            help="Timeout in seconds (default: 86400 = 24 h).",
        )
        parser.add_argument(
            "cmd", nargs=argparse.REMAINDER,
            help="Management command and its arguments.",
        )

    def handle(self, *args, **options):
        try:
            from google.cloud import run_v2
        except ImportError:
            raise CommandError(
                "google-cloud-run is required: pip install google-cloud-run"
            )
        from google.protobuf import duration_pb2
        from django_cloudrun_job.conf import get_config
        from django_cloudrun_job import runner

        cmd_parts = options["cmd"]
        if not cmd_parts:
            raise CommandError("Specify a management command to run.")
        if cmd_parts[0] == "--":
            cmd_parts = cmd_parts[1:]
        if not cmd_parts:
            raise CommandError("Specify a management command to run.")

        config = get_config()
        for key in ("PROJECT_ID", "SERVICE"):
            if not config.get(key):
                raise CommandError(
                    f"CLOUDRUN_REMOTE['{key}'] is required in settings."
                )

        project = config["PROJECT_ID"]
        region = config["REGION"]
        service_name = config["SERVICE"]
        job_name = config["JOB_NAME"]
        timeout = options["timeout"] or config["TIMEOUT"]
        creds = runner.get_credentials(config)

        self.stdout.write(f"Preparing Cloud Run Job '{job_name}'...")
        self.stdout.write(
            f"  Command: python manage.py {' '.join(cmd_parts)}"
        )

        try:
            svc = runner.get_service(
                run_v2, creds, project, region, service_name
            )
        except Exception as exc:
            raise CommandError(
                f"Cannot read service '{service_name}': {exc}"
            )

        ctr = svc.template.containers[0]
        self.stdout.write(f"  Image: {ctr.image}")

        jobs = run_v2.JobsClient(credentials=creds)
        parent = f"projects/{project}/locations/{region}"
        job_path = f"{parent}/jobs/{job_name}"

        spec = runner.build_job_spec(
            run_v2, duration_pb2, svc, ctr, timeout
        )
        status = runner.ensure_job(
            jobs, spec, parent, job_path, job_name
        )
        self.stdout.write(f"  {status.title()} job '{job_name}'")

        op = runner.run_job(
            jobs, run_v2, duration_pb2, job_path, cmd_parts, timeout
        )

        url = runner.get_console_url(op, project)
        if url:
            self.stdout.write(f"  Console: {url}")

        if options["no_wait"]:
            self.stdout.write(self.style.SUCCESS(
                "Job started (not waiting for completion)."
            ))
            return

        self.stdout.write("  Waiting for completion...")
        try:
            op.result(timeout=timeout)
            self.stdout.write(self.style.SUCCESS(
                "  Done. Job completed successfully."
            ))
        except Exception as exc:
            raise CommandError(f"Job failed: {exc}")

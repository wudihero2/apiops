"""
Main CLI interface for opsctl
"""

import click
import sys
from . import __version__
from .config import config
from .client import ApiOpsClient
from .formatter import (
    console,
    print_success,
    print_error,
    print_info,
    print_warning,
    print_json,
    print_job_status,
    print_operation_result,
)


@click.group()
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx):
    """
    opsctl - Command line tool for ApiOps

    Manage Kubernetes resources through ApiOps API.
    """
    ctx.ensure_object(dict)


# ============================================================================
# Config Commands
# ============================================================================

@cli.group()
def config_cmd():
    """Configure opsctl"""
    pass


@config_cmd.command('set')
@click.option('--api-url', help='API URL')
@click.option('--api-key', help='API Key')
def config_set(api_url, api_key):
    """Set configuration"""
    if api_url:
        config.set('api_url', api_url)
        print_success(f"API URL set to: {api_url}")

    if api_key:
        config.set('api_key', api_key)
        print_success("API Key updated")

    if not api_url and not api_key:
        print_error("Please provide --api-url and/or --api-key")
        sys.exit(1)


@config_cmd.command('show')
def config_show():
    """Show current configuration"""
    cfg = config.load()

    if not cfg:
        print_warning("No configuration found. Run 'opsctl config set' to configure.")
        return

    # Mask API key
    if 'api_key' in cfg:
        cfg['api_key'] = cfg['api_key'][:8] + '...' + cfg['api_key'][-4:]

    print_json(cfg, title="Configuration")


@config_cmd.command('check')
def config_check():
    """Check if configuration is valid"""
    if not config.is_configured():
        print_error("opsctl is not configured")
        print_info("Run: opsctl config set --api-url <url> --api-key <key>")
        sys.exit(1)

    try:
        client = ApiOpsClient()
        result = client.health_check()
        print_success(f"Connected to ApiOps API: {config.api_url}")
        print_json(result)
    except Exception as e:
        print_error(f"Connection failed: {e}")
        sys.exit(1)


# ============================================================================
# Health Check
# ============================================================================

@cli.command()
def health():
    """Check API health"""
    try:
        client = ApiOpsClient()
        result = client.health_check()
        print_success("API is healthy")
        print_json(result)
    except Exception as e:
        print_error(f"Health check failed: {e}")
        sys.exit(1)


# ============================================================================
# Pod Operations
# ============================================================================

@cli.group()
def pod():
    """Pod operations"""
    pass


@pod.command('delete')
@click.argument('namespace')
@click.argument('pod_name')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
def pod_delete(namespace, pod_name, yes):
    """Delete a pod"""
    if not yes:
        if not click.confirm(f"Delete pod {pod_name} in {namespace}?"):
            print_warning("Cancelled")
            return

    try:
        client = ApiOpsClient()
        result = client.delete_pod(namespace, pod_name)
        print_operation_result(result, "Pod deletion")
    except Exception as e:
        print_error(f"Failed to delete pod: {e}")
        sys.exit(1)


# ============================================================================
# PVC Operations
# ============================================================================

@cli.group()
def pvc():
    """PVC operations"""
    pass


@pvc.command('delete')
@click.argument('namespace')
@click.argument('pvc_name')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
def pvc_delete(namespace, pvc_name, yes):
    """Delete a PVC"""
    if not yes:
        if not click.confirm(f"Delete PVC {pvc_name} in {namespace}?"):
            print_warning("Cancelled")
            return

    try:
        client = ApiOpsClient()
        result = client.delete_pvc(namespace, pvc_name)
        print_operation_result(result, "PVC deletion")
    except Exception as e:
        print_error(f"Failed to delete PVC: {e}")
        sys.exit(1)


# ============================================================================
# Scale Operations
# ============================================================================

@cli.group()
def scale():
    """Scale operations"""
    pass


@scale.command('deployment')
@click.argument('namespace')
@click.argument('name')
@click.argument('replicas', type=int)
def scale_deployment(namespace, name, replicas):
    """Scale a deployment"""
    try:
        client = ApiOpsClient()
        result = client.scale_deployment(namespace, name, replicas)
        print_operation_result(result, "Deployment scaling")
    except Exception as e:
        print_error(f"Failed to scale deployment: {e}")
        sys.exit(1)


@scale.command('statefulset')
@click.argument('namespace')
@click.argument('name')
@click.argument('replicas', type=int)
def scale_statefulset(namespace, name, replicas):
    """Scale a statefulset"""
    try:
        client = ApiOpsClient()
        result = client.scale_statefulset(namespace, name, replicas)
        print_operation_result(result, "StatefulSet scaling")
    except Exception as e:
        print_error(f"Failed to scale statefulset: {e}")
        sys.exit(1)


# ============================================================================
# Job Operations
# ============================================================================

@cli.group()
def job():
    """Job operations"""
    pass


@job.command('pg-rebuild')
@click.option('--namespace', '-n', required=True, help='Namespace')
@click.option('--statefulset', '-s', required=True, help='StatefulSet name')
@click.option('--ordinal', '-o', type=int, default=0, help='Pod ordinal (default: 0)')
@click.option('--target-replicas', '-r', type=int, default=1, help='Target replicas (default: 1)')
@click.option('--max-retries', type=int, default=3, help='Max retry attempts (default: 3)')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
def job_pg_rebuild(namespace, statefulset, ordinal, target_replicas, max_retries, yes):
    """Create a PG rebuild job"""
    pvc_name = f"data-{statefulset}-{ordinal}"

    console.print("\n[bold]PG Rebuild Job[/bold]")
    console.print(f"  Namespace: {namespace}")
    console.print(f"  StatefulSet: {statefulset}")
    console.print(f"  Ordinal: {ordinal}")
    console.print(f"  PVC: {pvc_name}")
    console.print(f"  Target Replicas: {target_replicas}")
    console.print(f"  Max Retries: {max_retries}")
    console.print("\n[yellow]This will:[/yellow]")
    console.print(f"  1. Scale {statefulset} to 0")
    console.print(f"  2. Wait for pods to terminate")
    console.print(f"  3. Delete PVC: {pvc_name}")
    console.print(f"  4. Scale {statefulset} to {target_replicas}")
    console.print(f"  5. Wait for pods to be ready\n")

    if not yes:
        if not click.confirm("Continue?"):
            print_warning("Cancelled")
            return

    try:
        client = ApiOpsClient()
        result = client.create_pg_rebuild_job(
            namespace=namespace,
            statefulset=statefulset,
            ordinal=ordinal,
            target_replicas=target_replicas,
            max_retries=max_retries
        )

        job_id = result['job_id']
        print_success(f"Job created: {job_id}")
        print_info(f"Check status with: opsctl job status {job_id}")

    except Exception as e:
        print_error(f"Failed to create job: {e}")
        sys.exit(1)


@job.command('status')
@click.argument('job_id')
@click.option('--watch', '-w', is_flag=True, help='Watch job status (updates every 5s)')
def job_status(job_id, watch):
    """Get job status"""
    import time

    try:
        client = ApiOpsClient()

        if watch:
            print_info("Watching job status (Ctrl+C to stop)...\n")
            try:
                while True:
                    result = client.get_job(job_id)
                    console.clear()
                    print_job_status(result)

                    if result['status'] in ['success', 'failed']:
                        break

                    time.sleep(5)
            except KeyboardInterrupt:
                print_warning("\nStopped watching")
        else:
            result = client.get_job(job_id)
            print_job_status(result)

    except Exception as e:
        print_error(f"Failed to get job status: {e}")
        sys.exit(1)


@job.command('retry')
@click.argument('job_id')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
def job_retry(job_id, yes):
    """Manually retry a failed job"""
    try:
        client = ApiOpsClient()

        # Get current job status
        job_info = client.get_job(job_id)

        console.print(f"\n[bold]Retry Job[/bold]")
        console.print(f"  Job ID: {job_id}")
        console.print(f"  Type: {job_info['type']}")
        console.print(f"  Current Status: {job_info['status']}")
        console.print(f"  Retry Count: {job_info['retry_count']}/{job_info['max_retries']}\n")

        if job_info['status'] not in ['failed', 'pending']:
            print_warning(f"Job is not in failed state (current: {job_info['status']})")
            return

        if job_info['retry_count'] >= job_info['max_retries']:
            print_error(f"Max retries ({job_info['max_retries']}) exceeded")
            return

        if not yes:
            if not click.confirm("Retry this job?"):
                print_warning("Cancelled")
                return

        result = client.retry_job(job_id)
        print_success(result['message'])
        print_info(f"Retry count: {result['retry_count']}/{result['max_retries']}")
        print_info(f"Check status with: opsctl job status {job_id} -w")

    except Exception as e:
        print_error(f"Failed to retry job: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    cli(obj={})


if __name__ == '__main__':
    main()

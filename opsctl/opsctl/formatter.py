"""
Output formatting utilities
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box
import json
from datetime import datetime


console = Console()


def print_success(message: str):
    """Print success message"""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str):
    """Print error message"""
    console.print(f"[red]✗[/red] {message}", style="red")


def print_warning(message: str):
    """Print warning message"""
    console.print(f"[yellow]⚠[/yellow] {message}", style="yellow")


def print_info(message: str):
    """Print info message"""
    console.print(f"[blue]ℹ[/blue] {message}")


def print_json(data: any, title: str | None = None):
    """Print JSON data"""
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)

    if title:
        console.print(Panel(syntax, title=title, border_style="blue"))
    else:
        console.print(syntax)


def print_job_status(job: dict[str, any]):
    """Print job status in a formatted way"""
    # Status color
    status_colors = {
        'pending': 'yellow',
        'running': 'blue',
        'success': 'green',
        'failed': 'red',
    }
    status = job['status']
    status_color = status_colors.get(status, 'white')

    # Create header panel
    header = f"[bold]Job ID:[/bold] {job['job_id']}\n"
    header += f"[bold]Type:[/bold] {job['type']}\n"
    header += f"[bold]Status:[/bold] [{status_color}]{status.upper()}[/{status_color}]\n"
    header += f"[bold]Created:[/bold] {format_timestamp(job['created_at'])}\n"

    # Add retry information
    if 'retry_count' in job and 'max_retries' in job:
        retry_count = job['retry_count']
        max_retries = job['max_retries']
        retry_color = 'yellow' if retry_count > 0 else 'dim'
        header += f"[bold]Retries:[/bold] [{retry_color}]{retry_count}/{max_retries}[/{retry_color}]\n"

    if job.get('finished_at'):
        header += f"[bold]Finished:[/bold] {format_timestamp(job['finished_at'])}\n"
        duration = calculate_duration(job['created_at'], job['finished_at'])
        header += f"[bold]Duration:[/bold] {duration}"

    console.print(Panel(header, title="Job Information", border_style="blue"))

    # Create steps table
    if job.get('steps'):
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Step Name", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Detail", style="dim")
        table.add_column("Duration", style="dim")

        for step in job['steps']:
            step_status = step['status']
            step_color = status_colors.get(step_status, 'white')
            status_display = f"[{step_color}]{step_status.upper()}[/{step_color}]"

            detail = step.get('detail', '-')
            if len(detail) > 50:
                detail = detail[:47] + "..."

            duration = "-"
            if step.get('started_at') and step.get('finished_at'):
                duration = calculate_duration(step['started_at'], step['finished_at'])

            table.add_row(
                str(step['order']),
                step['name'],
                status_display,
                detail,
                duration
            )

        console.print("\n")
        console.print(table)


def format_timestamp(ts: str) -> str:
    """Format ISO timestamp to readable string"""
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return ts


def calculate_duration(start: str, end: str) -> str:
    """Calculate duration between two timestamps"""
    try:
        dt_start = datetime.fromisoformat(start.replace('Z', '+00:00'))
        dt_end = datetime.fromisoformat(end.replace('Z', '+00:00'))
        delta = dt_end - dt_start

        total_seconds = int(delta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except:
        return "-"


def print_operation_result(result: dict[str, any], operation: str):
    """Print operation result"""
    if result.get('status') == 'ok':
        print_success(f"{operation} completed successfully")
        if result.get('namespace'):
            console.print(f"  Namespace: {result['namespace']}")
        for key in ['deployment', 'statefulset', 'pod', 'pvc', 'replicas']:
            if key in result:
                console.print(f"  {key.capitalize()}: {result[key]}")
    else:
        print_error(f"{operation} failed")
        print_json(result)

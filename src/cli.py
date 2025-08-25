"""Command-line interface for Mem - simplified version."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from src.capture.pipeline import VideoCaptureProcessor, CaptureConfig
from src.storage.db import Database
from src.config import config

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging")
def cli(debug: bool):
    """Mem - Capture and store video frames and transcriptions."""
    level = logging.DEBUG if debug else getattr(logging, config.logging.level)
    logging.basicConfig(level=level, format=config.logging.format)


@cli.command()
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--frame-interval", default=config.capture.frame.interval_seconds, help="Seconds between frames"
)
@click.option(
    "--chunk-duration",
    default=config.capture.audio.chunk_duration_seconds,
    help="Audio chunk duration in seconds",
)
@click.option("--quality", default=config.capture.frame.jpeg_quality, help="JPEG quality (1-100)")
@click.option("--whisper-model", default=config.whisper.model, help="Whisper model size")
@click.option("--db", default=config.database.path, help="Database path")
def capture(
    video_path: Path,
    frame_interval: int,
    chunk_duration: int,
    quality: int,
    whisper_model: str,
    db: str,
):
    """Capture frames and transcriptions from a video file."""

    # Validate filename format
    if not video_path.name.startswith("20"):
        console.print(
            f"[red]Error: Invalid filename format '{video_path.name}'[/red]\n"
            f"Expected format: YYYY-MM-DD_HH-MM-SS.mp4"
        )
        return

    config = CaptureConfig(
        frame_interval=frame_interval,
        chunk_duration=chunk_duration,
        image_quality=quality,
        whisper_model=whisper_model,
    )

    processor = VideoCaptureProcessor(db_path=db, config=config)

    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
    ) as progress:
        task = progress.add_task(f"Processing {video_path.name}...", total=None)

        result = processor.process_video(video_path)

        if result["status"] == "success":
            console.print(f"\n[green]✓ Processing completed successfully![/green]")
            console.print(f"  Source ID: {result['source_id']}")
            console.print(f"  Frames extracted: {result['frames_extracted']}")
            console.print(f"  Transcriptions: {result['transcriptions_created']}")
            console.print(f"  Duration: {result['duration_seconds']:.1f} seconds")
            console.print(f"  Time range: {result['start_time']} to {result['end_time']}")
        else:
            console.print(f"\n[red]✗ Processing failed: {result['error']}[/red]")


@cli.command()
@click.argument("directory", type=click.Path(exists=True, path_type=Path))
@click.option("--pattern", default=config.files.video_pattern, help="File pattern to match")
@click.option("--db", default=config.database.path, help="Database path")
def batch(directory: Path, pattern: str, db: str):
    """Process multiple videos in a directory."""

    videos = list(directory.glob(pattern))
    valid_videos = []

    # Filter valid filenames
    for video in videos:
        try:
            from src.capture.extractor import parse_video_timestamp

            parse_video_timestamp(video.name)
            valid_videos.append(video)
        except ValueError:
            console.print(f"[yellow]Skipping invalid filename: {video.name}[/yellow]")

    if not valid_videos:
        console.print("[red]No valid video files found[/red]")
        return

    console.print(f"Found {len(valid_videos)} valid videos to process")

    processor = VideoCaptureProcessor(db_path=db)

    success_count = 0
    for i, video in enumerate(valid_videos, 1):
        console.print(f"\n[{i}/{len(valid_videos)}] Processing {video.name}...")
        result = processor.process_video(video)

        if result["status"] == "success":
            success_count += 1
            console.print(
                f"  [green]✓[/green] {result['frames_extracted']} frames, "
                f"{result['transcriptions_created']} transcriptions"
            )
        else:
            console.print(f"  [red]✗[/red] {result['error']}")

    console.print(f"\n[bold]Batch complete:[/bold] {success_count}/{len(valid_videos)} succeeded")


@cli.command()
@click.option("--start", type=click.DateTime(), help="Start time (UTC)")
@click.option("--end", type=click.DateTime(), help="End time (UTC)")
@click.option("--source-id", type=int, help="Filter by source ID")
@click.option("--db", default=config.database.path, help="Database path")
def list_frames(
    start: Optional[datetime], end: Optional[datetime], source_id: Optional[int], db: str
):
    """List captured frames."""

    database = Database(db_path=db)
    database.connect()

    # Default to last 24 hours
    if not end:
        end = datetime.utcnow()
    if not start:
        start = end - timedelta(days=config.display.default_time_range_days)

    frames = database.get_frames_by_time_range(start, end, source_id)

    if not frames:
        console.print("[yellow]No frames found in the specified time range[/yellow]")
        return

    # Create table
    table = Table(title=f"Frames from {start.isoformat()} to {end.isoformat()}")
    table.add_column("ID", style="cyan")
    table.add_column("Source", style="magenta")
    table.add_column("Timestamp")
    table.add_column("Size", justify="right")
    table.add_column("Dimensions", justify="right")

    for frame in frames[: config.display.frames_limit]:  # Limit display
        size_kb = frame.size_bytes / 1024 if frame.size_bytes else 0
        table.add_row(
            str(frame.id),
            str(frame.source_id),
            frame.timestamp.isoformat(),
            f"{size_kb:.1f} KB",
            f"{frame.width}x{frame.height}",
        )

    console.print(table)

    if len(frames) > config.display.frames_limit:
        console.print(
            f"\n[dim]Showing first {config.display.frames_limit} of {len(frames)} frames[/dim]"
        )

    database.disconnect()


@cli.command()
@click.option("--start", type=click.DateTime(), help="Start time (UTC)")
@click.option("--end", type=click.DateTime(), help="End time (UTC)")
@click.option("--source-id", type=int, help="Filter by source ID")
@click.option("--db", default=config.database.path, help="Database path")
def list_transcripts(
    start: Optional[datetime], end: Optional[datetime], source_id: Optional[int], db: str
):
    """List captured transcriptions."""

    database = Database(db_path=db)
    database.connect()

    # Default to last 24 hours
    if not end:
        end = datetime.utcnow()
    if not start:
        start = end - timedelta(days=config.display.default_time_range_days)

    transcripts = database.get_transcriptions_by_time_range(start, end, source_id)

    if not transcripts:
        console.print("[yellow]No transcriptions found in the specified time range[/yellow]")
        return

    # Display transcripts
    for trans in transcripts:
        console.print(f"\n[bold cyan]ID {trans.id}[/bold cyan] - Source {trans.source_id}")
        console.print(
            f"  Time: {trans.start_timestamp.isoformat()} to {trans.end_timestamp.isoformat()}"
        )
        console.print(f"  Language: {trans.language or 'unknown'}")
        console.print(
            f"  Confidence: {trans.confidence:.2f}" if trans.confidence else "  Confidence: N/A"
        )
        console.print(f"  Words: {trans.word_count}")

        # Show preview of text
        preview = trans.text[:200] + "..." if len(trans.text) > 200 else trans.text
        console.print(f"  Text: [dim]{preview}[/dim]")

    database.disconnect()


@cli.command()
@click.option("--db", default="mem.db", help="Database path")
def stats(db: str):
    """Show database statistics."""

    database = Database(db_path=db)
    database.connect()

    stats = database.get_statistics()

    console.print("\n[bold]Database Statistics[/bold]")
    console.print(f"  Sources: {stats['sources']}")
    console.print(f"  Frames: {stats['frames']}")
    console.print(f"  Transcriptions: {stats['transcriptions']}")
    console.print(f"  Total image size: {stats['total_image_size_mb']:.1f} MB")

    if stats["earliest_recording"]:
        console.print(f"  Earliest: {stats['earliest_recording']}")
    if stats["latest_recording"]:
        console.print(f"  Latest: {stats['latest_recording']}")

    database.disconnect()


@cli.command()
@click.option("--frame-id", type=int, required=True, help="Frame ID to export")
@click.option("--output", type=click.Path(), help="Output path for image")
@click.option("--db", default="mem.db", help="Database path")
def export_frame(frame_id: int, output: Optional[str], db: str):
    """Export a frame as an image file."""

    database = Database(db_path=db)
    database.connect()

    frame = database.get_frame(frame_id)
    if not frame:
        console.print(f"[red]Frame {frame_id} not found[/red]")
        return

    # Default output path
    if not output:
        output = f"frame_{frame_id}_{frame.timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"

    # Write image data
    with open(output, "wb") as f:
        f.write(frame.image_data)

    console.print(f"[green]Exported frame {frame_id} to {output}[/green]")
    console.print(f"  Size: {len(frame.image_data) / 1024:.1f} KB")
    console.print(f"  Dimensions: {frame.width}x{frame.height}")

    database.disconnect()


@cli.command()
@click.option("--confirm", is_flag=True, help="Confirm database reset")
@click.option("--db", default="mem.db", help="Database path")
def reset_db(confirm: bool, db: str):
    """Reset the database (delete and recreate)."""

    if not confirm:
        console.print("[yellow]This will delete all data![/yellow]")
        console.print("Use --confirm to proceed")
        return

    db_path = Path(db)

    if db_path.exists():
        db_path.unlink()
        console.print(f"[yellow]Deleted existing database: {db}[/yellow]")

    # Create new database
    database = Database(db_path=db)
    database.connect()
    database.initialize()
    database.disconnect()

    console.print(f"[green]Created fresh database: {db}[/green]")


if __name__ == "__main__":
    cli()

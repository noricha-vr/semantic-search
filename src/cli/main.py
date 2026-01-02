"""CLIエントリーポイント。

コマンドラインからインデックス化と検索を実行する。
"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.config.logging import setup_logging
from src.config.settings import get_settings

app = typer.Typer(
    name="local-doc-search",
    help="ローカルファイルを自然言語で検索するAIツール",
)
console = Console()


@app.command()
def index(
    path: str = typer.Argument(..., help="インデックス化するファイルまたはディレクトリのパス"),
    recursive: bool = typer.Option(True, "--recursive", "-r", help="サブディレクトリも処理する"),
) -> None:
    """ファイルまたはディレクトリをインデックス化する。"""
    settings = get_settings()
    setup_logging(settings.log_level, settings.logs_dir)

    from src.indexer.document_indexer import DocumentIndexer

    target = Path(path).expanduser()
    if not target.exists():
        console.print(f"[red]Error:[/red] Path not found: {path}")
        raise typer.Exit(1)

    indexer = DocumentIndexer()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        if target.is_file():
            progress.add_task(description=f"Indexing {target.name}...", total=None)
            result = indexer.index_file(target)
            if result:
                console.print(f"[green]Indexed:[/green] {result['filename']}")
            else:
                console.print(f"[yellow]Skipped:[/yellow] {target.name}")
        else:
            task = progress.add_task(description=f"Indexing {target}...", total=None)
            results = indexer.index_directory(target, recursive=recursive)
            progress.update(task, description="Indexing complete")
            console.print(f"[green]Indexed {len(results)} files[/green]")


@app.command()
def search(
    query: str = typer.Argument(..., help="検索クエリ"),
    limit: int = typer.Option(10, "--limit", "-n", help="結果件数"),
    media_type: Optional[str] = typer.Option(None, "--type", "-t", help="メディアタイプでフィルター"),
) -> None:
    """自然言語で検索する。"""
    settings = get_settings()
    setup_logging(settings.log_level, settings.logs_dir)

    from src.search.vector_search import VectorSearch

    search_engine = VectorSearch()

    media_types = [media_type] if media_type else None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task(description="Searching...", total=None)
        results = search_engine.search(query, limit=limit, media_types=media_types)

    if not results:
        console.print("[yellow]No results found[/yellow]")
        return

    table = Table(title=f"Search Results for: {query}")
    table.add_column("Score", style="cyan", width=8)
    table.add_column("Filename", style="green")
    table.add_column("Text", style="white", overflow="fold")

    for r in results:
        text_preview = r.text[:100] + "..." if len(r.text) > 100 else r.text
        table.add_row(f"{r.score:.3f}", r.filename, text_preview)

    console.print(table)


@app.command()
def watch(
    paths: list[str] = typer.Argument(..., help="監視するディレクトリパス"),
) -> None:
    """ディレクトリを監視して自動インデックスする。"""
    settings = get_settings()
    setup_logging(settings.log_level, settings.logs_dir)

    from src.indexer.auto_indexer import run_auto_indexer

    watch_paths = [Path(p).expanduser() for p in paths]

    console.print(Panel.fit(
        f"Watching: {', '.join(str(p) for p in watch_paths)}\n"
        "Press Ctrl+C to stop.",
        title="Auto Indexer",
    ))

    try:
        asyncio.run(run_auto_indexer(watch_paths))
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped[/yellow]")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="ホスト"),
    port: int = typer.Option(8765, "--port", "-p", help="ポート"),
    reload: bool = typer.Option(False, "--reload", help="開発モード（自動リロード）"),
) -> None:
    """APIサーバーを起動する。"""
    settings = get_settings()
    setup_logging(settings.log_level, settings.logs_dir)

    import uvicorn

    console.print(Panel.fit(
        f"Starting API server at http://{host}:{port}\n"
        "Press Ctrl+C to stop.",
        title="LocalDocSearch API",
    ))

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def status() -> None:
    """インデックスの状態を表示する。"""
    settings = get_settings()
    setup_logging(settings.log_level, settings.logs_dir)

    from src.storage.lancedb_client import LanceDBClient
    from src.storage.sqlite_client import SQLiteClient

    sqlite = SQLiteClient()
    lancedb = LanceDBClient()

    sqlite_stats = sqlite.get_stats()
    lance_stats = lancedb.get_table_stats()

    table = Table(title="Index Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Documents", str(sqlite_stats["total_documents"]))
    table.add_row("Total Chunks", str(sqlite_stats["total_chunks"]))
    table.add_row("Last Indexed", sqlite_stats.get("last_indexed_at") or "N/A")

    if sqlite_stats["by_media_type"]:
        for media_type, count in sqlite_stats["by_media_type"].items():
            table.add_row(f"  - {media_type}", str(count))

    console.print(table)

    if lance_stats:
        lance_table = Table(title="LanceDB Tables")
        lance_table.add_column("Table", style="cyan")
        lance_table.add_column("Rows", style="green")
        for table_name, count in lance_stats.items():
            lance_table.add_row(table_name, str(count))
        console.print(lance_table)


if __name__ == "__main__":
    app()

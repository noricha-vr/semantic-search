"""検索APIルート。

検索機能を提供するエンドポイント。
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.search.hybrid_search import HybridSearch

logger = get_logger()
router = APIRouter()


class SearchResult(BaseModel):
    """検索結果。"""

    chunk_id: str
    document_id: str
    text: str
    path: str
    filename: str
    media_type: str
    score: float
    start_time: float | None = None
    end_time: float | None = None


class SearchResponse(BaseModel):
    """検索レスポンス。"""

    query: str
    total: int
    results: list[SearchResult]


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, description="検索クエリ"),
    limit: int = Query(default=10, ge=1, le=100, description="結果件数"),
    media_type: str | None = Query(default=None, description="メディアタイプフィルタ"),
):
    """ハイブリッド検索を実行。

    ベクトル検索とBM25検索を組み合わせたハイブリッド検索を行う。
    """
    logger.info(f"Search request: q={q}, limit={limit}, media_type={media_type}")

    client = HybridSearch()
    media_types = [media_type] if media_type else None
    results = client.search(
        query=q,
        limit=limit,
        media_types=media_types,
    )

    search_results = [
        SearchResult(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            text=r.text,
            path=r.path,
            filename=r.filename,
            media_type=r.media_type,
            score=r.score,
            start_time=r.start_time,
            end_time=r.end_time,
        )
        for r in results
    ]

    return SearchResponse(
        query=q,
        total=len(search_results),
        results=search_results,
    )


class SuggestRequest(BaseModel):
    """サジェストリクエスト。"""

    query: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class SuggestResponse(BaseModel):
    """サジェストレスポンス。"""

    query: str
    suggestions: list[str]


@router.get("/suggest", response_model=SuggestResponse)
async def suggest(
    q: str = Query(..., min_length=1, description="検索クエリ"),
    limit: int = Query(default=5, ge=1, le=20, description="サジェスト件数"),
):
    """検索サジェストを取得。

    入力途中のクエリに対してサジェストを返す。
    現在は簡易実装として空のリストを返す。
    """
    # TODO: 実際のサジェスト実装
    return SuggestResponse(
        query=q,
        suggestions=[],
    )

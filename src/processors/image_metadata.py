"""画像メタデータ抽出。

EXIF、XMP、IPTC等のメタデータを抽出して検索可能なテキストに変換する。
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger()


class ImageExifMetadata(BaseModel):
    """画像EXIFメタデータ。"""

    # 撮影情報
    captured_at: datetime | None = Field(default=None, description="撮影日時")
    camera_make: str | None = Field(default=None, description="カメラメーカー")
    camera_model: str | None = Field(default=None, description="カメラモデル")

    # GPS情報
    gps_latitude: float | None = Field(default=None, description="緯度（10進数）")
    gps_longitude: float | None = Field(default=None, description="経度（10進数）")

    # 逆ジオコーディング結果
    location_city: str | None = Field(default=None, description="都市名")
    location_state: str | None = Field(default=None, description="都道府県/州")
    location_country: str | None = Field(default=None, description="国名")

    # XMP/IPTC情報
    title: str | None = Field(default=None, description="タイトル")
    description: str | None = Field(default=None, description="説明")
    keywords: list[str] = Field(default_factory=list, description="キーワード")
    creator: str | None = Field(default=None, description="作成者")


class ImageMetadataExtractor:
    """画像メタデータ抽出器。"""

    def __init__(self):
        """初期化。"""
        self._reverse_geocoder = None

    def _get_reverse_geocoder(self):
        """reverse_geocoderを遅延ロード。

        初回アクセス時にのみロード（データセットのダウンロードが発生するため）。
        """
        if self._reverse_geocoder is None:
            try:
                import reverse_geocoder as rg

                self._reverse_geocoder = rg
            except ImportError:
                logger.warning("reverse_geocoder not installed, geocoding disabled")
                self._reverse_geocoder = False
        return self._reverse_geocoder if self._reverse_geocoder else None

    def extract(self, image_path: Path | str) -> ImageExifMetadata:
        """画像からメタデータを抽出。

        Args:
            image_path: 画像ファイルのパス

        Returns:
            抽出されたメタデータ
        """
        image_path = Path(image_path)
        metadata = ImageExifMetadata()

        if not image_path.exists():
            logger.warning(f"Image file not found: {image_path}")
            return metadata

        try:
            with Image.open(image_path) as img:
                exif_data = self._get_exif_data(img)
                if exif_data:
                    metadata = self._parse_exif(exif_data)
        except Exception as e:
            logger.debug(f"Failed to extract metadata from {image_path}: {e}")

        return metadata

    def _get_exif_data(self, img: Image.Image) -> dict[str, Any] | None:
        """PILイメージからEXIFデータを取得。

        Args:
            img: PILイメージ

        Returns:
            タグ名をキーとしたEXIFデータまたはNone
        """
        try:
            exif = img._getexif()
            if not exif:
                return None

            exif_data = {}
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value

            return exif_data
        except Exception:
            return None

    def _parse_exif(self, exif_data: dict[str, Any]) -> ImageExifMetadata:
        """EXIFデータをパースしてImageExifMetadataに変換。

        Args:
            exif_data: EXIFデータ辞書

        Returns:
            パースされたメタデータ
        """
        metadata = ImageExifMetadata()

        # 撮影日時
        date_str = exif_data.get("DateTimeOriginal") or exif_data.get("DateTime")
        if date_str:
            metadata.captured_at = self._parse_exif_datetime(date_str)

        # カメラ情報
        metadata.camera_make = exif_data.get("Make")
        metadata.camera_model = exif_data.get("Model")

        # GPS情報
        gps_info = exif_data.get("GPSInfo")
        if gps_info:
            gps_data = self._parse_gps_info(gps_info)
            if gps_data:
                metadata.gps_latitude = gps_data.get("latitude")
                metadata.gps_longitude = gps_data.get("longitude")

                # 逆ジオコーディング
                if metadata.gps_latitude and metadata.gps_longitude:
                    location = self._reverse_geocode(
                        metadata.gps_latitude, metadata.gps_longitude
                    )
                    if location:
                        metadata.location_city = location.get("city")
                        metadata.location_state = location.get("state")
                        metadata.location_country = location.get("country")

        # XMP/IPTC情報（EXIF経由で取得可能なもの）
        metadata.title = exif_data.get("ImageDescription")
        metadata.creator = exif_data.get("Artist")

        # XMPデータ（ある場合）
        xmp_data = exif_data.get("XPKeywords")
        if xmp_data:
            if isinstance(xmp_data, bytes):
                try:
                    keywords_str = xmp_data.decode("utf-16-le").rstrip("\x00")
                    metadata.keywords = [k.strip() for k in keywords_str.split(";") if k.strip()]
                except Exception:
                    pass
            elif isinstance(xmp_data, str):
                metadata.keywords = [k.strip() for k in xmp_data.split(";") if k.strip()]

        xp_title = exif_data.get("XPTitle")
        if xp_title and not metadata.title:
            if isinstance(xp_title, bytes):
                try:
                    metadata.title = xp_title.decode("utf-16-le").rstrip("\x00")
                except Exception:
                    pass
            elif isinstance(xp_title, str):
                metadata.title = xp_title

        xp_subject = exif_data.get("XPSubject")
        if xp_subject and not metadata.description:
            if isinstance(xp_subject, bytes):
                try:
                    metadata.description = xp_subject.decode("utf-16-le").rstrip("\x00")
                except Exception:
                    pass
            elif isinstance(xp_subject, str):
                metadata.description = xp_subject

        return metadata

    def _parse_exif_datetime(self, date_str: str) -> datetime | None:
        """EXIF日時文字列をdatetimeに変換。

        Args:
            date_str: EXIF形式の日時文字列（例: "2024:01:15 10:30:00"）

        Returns:
            datetimeまたはNone
        """
        if not date_str:
            return None

        try:
            # EXIF標準形式: "YYYY:MM:DD HH:MM:SS"
            return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
        except ValueError:
            try:
                # 代替形式
                return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None

    def _parse_gps_info(self, gps_info: dict) -> dict[str, float] | None:
        """GPS情報をパースして10進数に変換。

        Args:
            gps_info: GPSInfoタグの値

        Returns:
            緯度・経度の辞書またはNone
        """
        try:
            # GPSInfoのタグIDを名前に変換
            gps_data = {}
            for tag_id, value in gps_info.items():
                tag = GPSTAGS.get(tag_id, tag_id)
                gps_data[tag] = value

            # 緯度
            lat = gps_data.get("GPSLatitude")
            lat_ref = gps_data.get("GPSLatitudeRef")
            if lat and lat_ref:
                latitude = self._convert_to_degrees(lat)
                if lat_ref == "S":
                    latitude = -latitude
            else:
                return None

            # 経度
            lon = gps_data.get("GPSLongitude")
            lon_ref = gps_data.get("GPSLongitudeRef")
            if lon and lon_ref:
                longitude = self._convert_to_degrees(lon)
                if lon_ref == "W":
                    longitude = -longitude
            else:
                return None

            return {"latitude": latitude, "longitude": longitude}
        except Exception:
            return None

    def _rational_to_float(self, value: Any) -> float:
        """Rational型（分数タプル）または数値をfloatに変換。

        Args:
            value: Rational型タプル(numerator, denominator)または数値

        Returns:
            float値
        """
        if isinstance(value, tuple) and len(value) == 2:
            # Rational型: (numerator, denominator)
            numerator, denominator = value
            if denominator == 0:
                return 0.0
            return float(numerator) / float(denominator)
        return float(value)

    def _convert_to_degrees(self, value: tuple) -> float:
        """度分秒を10進数に変換。

        Args:
            value: (度, 分, 秒)のタプル（各要素はRational型または数値）

        Returns:
            10進数の度
        """
        d = self._rational_to_float(value[0])
        m = self._rational_to_float(value[1])
        s = self._rational_to_float(value[2])
        return d + (m / 60.0) + (s / 3600.0)

    def _reverse_geocode(
        self, latitude: float, longitude: float
    ) -> dict[str, str] | None:
        """GPS座標から地名を取得。

        Args:
            latitude: 緯度
            longitude: 経度

        Returns:
            地名情報の辞書またはNone
        """
        rg = self._get_reverse_geocoder()
        if not rg:
            return None

        try:
            results = rg.search((latitude, longitude))
            if results and len(results) > 0:
                result = results[0]
                return {
                    "city": result.get("name"),
                    "state": result.get("admin1"),
                    "country": result.get("cc"),
                }
        except Exception as e:
            logger.debug(f"Reverse geocoding failed: {e}")

        return None


def format_metadata_for_vectorization(metadata: ImageExifMetadata) -> str:
    """メタデータを検索用テキストに変換。

    Args:
        metadata: 画像メタデータ

    Returns:
        ベクトル化用のテキスト
    """
    parts = []

    # 撮影日時
    if metadata.captured_at:
        parts.append(f"撮影日時: {metadata.captured_at.strftime('%Y年%m月%d日 %H:%M:%S')}")

    # カメラ情報
    camera_parts = []
    if metadata.camera_make:
        camera_parts.append(metadata.camera_make)
    if metadata.camera_model:
        camera_parts.append(metadata.camera_model)
    if camera_parts:
        parts.append(f"カメラ: {' '.join(camera_parts)}")

    # 位置情報
    location_parts = []
    if metadata.location_city:
        location_parts.append(metadata.location_city)
    if metadata.location_state:
        location_parts.append(metadata.location_state)
    if metadata.location_country:
        location_parts.append(metadata.location_country)
    if location_parts:
        parts.append(f"撮影場所: {', '.join(location_parts)}")

    # タイトル・説明
    if metadata.title:
        parts.append(f"タイトル: {metadata.title}")
    if metadata.description:
        parts.append(f"説明: {metadata.description}")

    # キーワード
    if metadata.keywords:
        parts.append(f"キーワード: {', '.join(metadata.keywords)}")

    # 作成者
    if metadata.creator:
        parts.append(f"作成者: {metadata.creator}")

    return "\n".join(parts)

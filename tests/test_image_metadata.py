"""画像メタデータ抽出テスト。"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.processors.image_metadata import (
    ImageExifMetadata,
    ImageMetadataExtractor,
    format_metadata_for_vectorization,
)


class TestImageExifMetadata:
    """ImageExifMetadataモデルのテスト。"""

    def test_default_values(self):
        """デフォルト値が正しく設定される。"""
        metadata = ImageExifMetadata()
        assert metadata.captured_at is None
        assert metadata.camera_make is None
        assert metadata.camera_model is None
        assert metadata.gps_latitude is None
        assert metadata.gps_longitude is None
        assert metadata.location_city is None
        assert metadata.location_state is None
        assert metadata.location_country is None
        assert metadata.title is None
        assert metadata.description is None
        assert metadata.keywords == []
        assert metadata.creator is None

    def test_with_values(self):
        """値を設定できる。"""
        metadata = ImageExifMetadata(
            captured_at=datetime(2024, 1, 15, 10, 30, 0),
            camera_make="Apple",
            camera_model="iPhone 15 Pro",
            gps_latitude=35.6762,
            gps_longitude=139.6503,
            location_city="Tokyo",
            location_state="Tokyo",
            location_country="JP",
            title="My Photo",
            description="A beautiful scene",
            keywords=["travel", "japan"],
            creator="John Doe",
        )
        assert metadata.captured_at == datetime(2024, 1, 15, 10, 30, 0)
        assert metadata.camera_make == "Apple"
        assert metadata.camera_model == "iPhone 15 Pro"
        assert metadata.gps_latitude == 35.6762
        assert metadata.gps_longitude == 139.6503
        assert metadata.location_city == "Tokyo"
        assert metadata.location_state == "Tokyo"
        assert metadata.location_country == "JP"
        assert metadata.title == "My Photo"
        assert metadata.description == "A beautiful scene"
        assert metadata.keywords == ["travel", "japan"]
        assert metadata.creator == "John Doe"


class TestImageMetadataExtractor:
    """ImageMetadataExtractorのテスト。"""

    def test_extract_from_nonexistent_file(self, tmp_path):
        """存在しないファイルでは空のメタデータを返す。"""
        extractor = ImageMetadataExtractor()
        result = extractor.extract(tmp_path / "nonexistent.jpg")
        assert result.captured_at is None
        assert result.camera_make is None

    def test_extract_from_image_without_exif(self, tmp_path):
        """EXIFなしの画像では空のメタデータを返す。"""
        # EXIFなしのPNG画像を作成
        test_image = tmp_path / "no_exif.png"
        img = Image.new("RGB", (100, 100), color="blue")
        img.save(test_image)

        extractor = ImageMetadataExtractor()
        result = extractor.extract(test_image)

        # メタデータは空だがエラーは発生しない
        assert result.captured_at is None
        assert result.camera_make is None
        assert result.gps_latitude is None

    def test_parse_exif_datetime(self):
        """EXIF日時のパース。"""
        extractor = ImageMetadataExtractor()

        # 標準形式
        result = extractor._parse_exif_datetime("2024:01:15 10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)

        # 代替形式
        result = extractor._parse_exif_datetime("2024-01-15 10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)

        # 無効な形式
        result = extractor._parse_exif_datetime("invalid")
        assert result is None

        # 空文字列
        result = extractor._parse_exif_datetime("")
        assert result is None

    def test_convert_to_degrees(self):
        """度分秒から10進数への変換。"""
        extractor = ImageMetadataExtractor()

        # 東京の座標例: 35度 40分 34.8秒
        result = extractor._convert_to_degrees((35, 40, 34.8))
        expected = 35 + (40 / 60) + (34.8 / 3600)
        assert abs(result - expected) < 0.0001

    def test_parse_gps_info(self):
        """GPS情報のパース。"""
        extractor = ImageMetadataExtractor()

        # 東京タワーの座標を模擬（タグIDはGPSTAGSのもの）
        from PIL.ExifTags import GPSTAGS

        # GPSTAGSの逆引き
        lat_tag = [k for k, v in GPSTAGS.items() if v == "GPSLatitude"][0]
        lat_ref_tag = [k for k, v in GPSTAGS.items() if v == "GPSLatitudeRef"][0]
        lon_tag = [k for k, v in GPSTAGS.items() if v == "GPSLongitude"][0]
        lon_ref_tag = [k for k, v in GPSTAGS.items() if v == "GPSLongitudeRef"][0]

        gps_info = {
            lat_tag: (35, 39, 31.0),
            lat_ref_tag: "N",
            lon_tag: (139, 44, 40.0),
            lon_ref_tag: "E",
        }

        result = extractor._parse_gps_info(gps_info)
        assert result is not None
        assert abs(result["latitude"] - 35.6586) < 0.01
        assert abs(result["longitude"] - 139.7444) < 0.01

    def test_parse_gps_info_southern_hemisphere(self):
        """南半球のGPS情報パース。"""
        extractor = ImageMetadataExtractor()

        from PIL.ExifTags import GPSTAGS

        lat_tag = [k for k, v in GPSTAGS.items() if v == "GPSLatitude"][0]
        lat_ref_tag = [k for k, v in GPSTAGS.items() if v == "GPSLatitudeRef"][0]
        lon_tag = [k for k, v in GPSTAGS.items() if v == "GPSLongitude"][0]
        lon_ref_tag = [k for k, v in GPSTAGS.items() if v == "GPSLongitudeRef"][0]

        # シドニーの座標
        gps_info = {
            lat_tag: (33, 52, 10.0),
            lat_ref_tag: "S",
            lon_tag: (151, 12, 30.0),
            lon_ref_tag: "E",
        }

        result = extractor._parse_gps_info(gps_info)
        assert result is not None
        assert result["latitude"] < 0  # 南半球は負

    def test_parse_gps_info_incomplete(self):
        """不完全なGPS情報ではNoneを返す。"""
        extractor = ImageMetadataExtractor()

        from PIL.ExifTags import GPSTAGS

        lat_tag = [k for k, v in GPSTAGS.items() if v == "GPSLatitude"][0]

        # 緯度のみ（経度なし）
        gps_info = {
            lat_tag: (35, 39, 31.0),
        }

        result = extractor._parse_gps_info(gps_info)
        assert result is None

    @patch("src.processors.image_metadata.ImageMetadataExtractor._get_reverse_geocoder")
    def test_reverse_geocode(self, mock_get_rg):
        """逆ジオコーディング。"""
        mock_rg = MagicMock()
        mock_rg.search.return_value = [
            {"name": "Shibuya", "admin1": "Tokyo", "cc": "JP"}
        ]
        mock_get_rg.return_value = mock_rg

        extractor = ImageMetadataExtractor()
        result = extractor._reverse_geocode(35.6762, 139.6503)

        assert result is not None
        assert result["city"] == "Shibuya"
        assert result["state"] == "Tokyo"
        assert result["country"] == "JP"

    def test_reverse_geocode_without_library(self):
        """reverse_geocoderがない場合はNoneを返す。"""
        extractor = ImageMetadataExtractor()
        extractor._reverse_geocoder = False  # ライブラリなしを模擬

        result = extractor._reverse_geocode(35.6762, 139.6503)
        assert result is None


class TestRationalToFloat:
    """_rational_to_float メソッドのテスト。"""

    def test_rational_tuple(self):
        """Rational型タプル (numerator, denominator) の変換。"""
        extractor = ImageMetadataExtractor()
        # 35/1 = 35.0
        assert extractor._rational_to_float((35, 1)) == 35.0
        # 3100/100 = 31.0
        assert extractor._rational_to_float((3100, 100)) == 31.0

    def test_float_value(self):
        """float値はそのまま返す。"""
        extractor = ImageMetadataExtractor()
        assert extractor._rational_to_float(35.5) == 35.5

    def test_int_value(self):
        """int値はfloatに変換。"""
        extractor = ImageMetadataExtractor()
        assert extractor._rational_to_float(35) == 35.0

    def test_zero_denominator(self):
        """分母が0の場合は0.0を返す。"""
        extractor = ImageMetadataExtractor()
        assert extractor._rational_to_float((35, 0)) == 0.0


class TestConvertToDegreesWithRational:
    """Rational型GPS座標の変換テスト。"""

    def test_rational_gps_coordinates(self):
        """Rational型タプルのGPS座標を正しく変換。"""
        extractor = ImageMetadataExtractor()
        # 東京駅: 35度39分31秒 = 35 + 39/60 + 31/3600 ≒ 35.6586
        # Rational型: ((35,1), (39,1), (3100,100))
        value = ((35, 1), (39, 1), (3100, 100))
        result = extractor._convert_to_degrees(value)
        assert abs(result - 35.6586) < 0.001

    def test_mixed_types(self):
        """Rational型とfloatが混在した場合。"""
        extractor = ImageMetadataExtractor()
        # (35, 39, 31.0) - 3番目だけfloat
        value = ((35, 1), (39, 1), 31.0)
        result = extractor._convert_to_degrees(value)
        assert abs(result - 35.6586) < 0.001

    def test_all_float(self):
        """全てfloat値の場合（従来の形式）。"""
        extractor = ImageMetadataExtractor()
        value = (35.0, 39.0, 31.0)
        result = extractor._convert_to_degrees(value)
        assert abs(result - 35.6586) < 0.001


class TestFormatMetadataForVectorization:
    """format_metadata_for_vectorization関数のテスト。"""

    def test_empty_metadata(self):
        """空のメタデータでは空文字列。"""
        metadata = ImageExifMetadata()
        result = format_metadata_for_vectorization(metadata)
        assert result == ""

    def test_captured_at_only(self):
        """撮影日時のみ。"""
        metadata = ImageExifMetadata(
            captured_at=datetime(2024, 1, 15, 10, 30, 0)
        )
        result = format_metadata_for_vectorization(metadata)
        assert "撮影日時: 2024年01月15日 10:30:00" in result

    def test_camera_info(self):
        """カメラ情報。"""
        metadata = ImageExifMetadata(
            camera_make="Apple",
            camera_model="iPhone 15 Pro",
        )
        result = format_metadata_for_vectorization(metadata)
        assert "カメラ: Apple iPhone 15 Pro" in result

    def test_camera_make_only(self):
        """カメラメーカーのみ。"""
        metadata = ImageExifMetadata(
            camera_make="Canon",
        )
        result = format_metadata_for_vectorization(metadata)
        assert "カメラ: Canon" in result

    def test_location_info(self):
        """位置情報。"""
        metadata = ImageExifMetadata(
            location_city="Tokyo",
            location_state="Tokyo",
            location_country="JP",
        )
        result = format_metadata_for_vectorization(metadata)
        assert "撮影場所: Tokyo, Tokyo, JP" in result

    def test_partial_location_info(self):
        """部分的な位置情報。"""
        metadata = ImageExifMetadata(
            location_city="New York",
            location_country="US",
        )
        result = format_metadata_for_vectorization(metadata)
        assert "撮影場所: New York, US" in result

    def test_title_and_description(self):
        """タイトルと説明。"""
        metadata = ImageExifMetadata(
            title="Sunset Photo",
            description="Beautiful sunset at the beach",
        )
        result = format_metadata_for_vectorization(metadata)
        assert "タイトル: Sunset Photo" in result
        assert "説明: Beautiful sunset at the beach" in result

    def test_keywords(self):
        """キーワード。"""
        metadata = ImageExifMetadata(
            keywords=["travel", "japan", "tokyo"],
        )
        result = format_metadata_for_vectorization(metadata)
        assert "キーワード: travel, japan, tokyo" in result

    def test_creator(self):
        """作成者。"""
        metadata = ImageExifMetadata(
            creator="John Doe",
        )
        result = format_metadata_for_vectorization(metadata)
        assert "作成者: John Doe" in result

    def test_full_metadata(self):
        """すべてのメタデータ。"""
        metadata = ImageExifMetadata(
            captured_at=datetime(2024, 6, 15, 14, 30, 0),
            camera_make="Nikon",
            camera_model="Z8",
            location_city="Paris",
            location_state="Ile-de-France",
            location_country="FR",
            title="Eiffel Tower",
            description="View from Trocadero",
            keywords=["travel", "paris", "landmark"],
            creator="Jane Smith",
        )
        result = format_metadata_for_vectorization(metadata)

        assert "撮影日時: 2024年06月15日 14:30:00" in result
        assert "カメラ: Nikon Z8" in result
        assert "撮影場所: Paris, Ile-de-France, FR" in result
        assert "タイトル: Eiffel Tower" in result
        assert "説明: View from Trocadero" in result
        assert "キーワード: travel, paris, landmark" in result
        assert "作成者: Jane Smith" in result

    def test_metadata_order(self):
        """メタデータの順序。"""
        metadata = ImageExifMetadata(
            captured_at=datetime(2024, 1, 1, 0, 0, 0),
            camera_make="Canon",
            title="Test",
        )
        result = format_metadata_for_vectorization(metadata)
        lines = result.split("\n")

        # 撮影日時が最初、カメラ情報が次、タイトルが最後
        assert lines[0].startswith("撮影日時:")
        assert lines[1].startswith("カメラ:")
        assert lines[2].startswith("タイトル:")

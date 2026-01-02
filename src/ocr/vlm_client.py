"""VLMクライアント。

画像理解とOCRを提供する。
"""

import base64
from pathlib import Path

import ollama

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger()


class VLMClient:
    """VLMクライアント。"""

    def __init__(self, model: str | None = None):
        """初期化。

        Args:
            model: モデル名（指定しない場合は設定から取得、なければllava:7b）
        """
        settings = get_settings()
        self.model = model or settings.vlm_model
        # Qwen2.5-VLが利用できない場合はllavaを使用
        self.fallback_model = "llava:7b"
        self.host = settings.ollama_host
        self._client = ollama.Client(host=self.host)
        self._checked_models: set[str] = set()

    def _check_model_available(self, model: str) -> bool:
        """モデルが利用可能かチェック。"""
        if model in self._checked_models:
            return True

        try:
            models_response = self._client.list()
            # ollama-pythonはModelオブジェクトのリストを返す
            model_list = getattr(models_response, 'models', [])
            model_prefix = model.split(":")[0]
            available = any(
                getattr(m, 'model', '').startswith(model_prefix)
                for m in model_list
            )
            if available:
                self._checked_models.add(model)
            return available
        except Exception as e:
            logger.warning(f"Failed to check model availability: {e}")
            return False

    def _get_available_model(self) -> str:
        """利用可能なモデルを取得。"""
        if self._check_model_available(self.model):
            return self.model
        if self._check_model_available(self.fallback_model):
            return self.fallback_model
        raise RuntimeError(
            f"No VLM model available. Please run: ollama pull {self.fallback_model}"
        )

    def _encode_image(self, image_path: Path | str) -> str:
        """画像をBase64エンコード。

        Args:
            image_path: 画像ファイルのパス

        Returns:
            Base64エンコードされた画像
        """
        image_path = Path(image_path)
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def describe_image(
        self,
        image_path: Path | str,
        prompt: str | None = None,
    ) -> str:
        """画像を説明文で説明。

        Args:
            image_path: 画像ファイルのパス
            prompt: カスタムプロンプト

        Returns:
            画像の説明文
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        model = self._get_available_model()
        image_data = self._encode_image(image_path)

        default_prompt = (
            "Describe this image in detail. "
            "Include any text visible in the image. "
            "Focus on the main content and any important details."
        )

        try:
            response = self._client.chat(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt or default_prompt,
                        "images": [image_data],
                    }
                ],
            )
            description = response["message"]["content"]
            logger.info(f"Described image: {image_path}")
            return description
        except Exception as e:
            logger.error(f"VLM error: {e}")
            raise

    def extract_text(
        self,
        image_path: Path | str,
    ) -> str:
        """画像からテキストを抽出（OCR）。

        Args:
            image_path: 画像ファイルのパス

        Returns:
            抽出されたテキスト
        """
        prompt = (
            "Extract all text visible in this image. "
            "Return only the text content, without any descriptions. "
            "If there is no text, return 'NO TEXT FOUND'."
        )

        text = self.describe_image(image_path, prompt=prompt)

        if "NO TEXT FOUND" in text.upper():
            return ""

        return text

    def analyze_document_image(
        self,
        image_path: Path | str,
    ) -> dict:
        """ドキュメント画像を分析。

        Args:
            image_path: 画像ファイルのパス

        Returns:
            分析結果（説明文とOCRテキスト）
        """
        # 説明文を取得
        description = self.describe_image(image_path)

        # OCRテキストを取得
        ocr_text = self.extract_text(image_path)

        return {
            "description": description,
            "ocr_text": ocr_text if ocr_text else None,
        }

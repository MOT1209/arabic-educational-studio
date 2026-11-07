"""
Provider Manager for Arabic Educational Skills Studio.
Registers and manages TTS and AI model providers.
"""

from typing import Optional, Dict, Any, List


class ProviderNotImplemented(Exception):
    """Raised when a requested provider is not implemented."""
    pass


class ProviderManager:
    def __init__(self, constraints: Optional[Dict[str, Any]] = None):
        self.constraints = constraints or {}
        self._providers = [
            {
                "id": "local_engine",
                "kind": "render",
                "status": "implemented",
                "notes": "Local HTML/SVG renderer via Playwright + FFmpeg",
            },
            {
                "id": "speech",
                "kind": "tts",
                "status": "not_implemented",
                "notes": "No TTS provider implemented; use human recording",
            },
            {
                "id": "image_gen",
                "kind": "image",
                "status": "not_implemented",
                "notes": "No image generation provider implemented",
            },
            {
                "id": "video_gen",
                "kind": "video",
                "status": "not_implemented",
                "notes": "No video generation provider implemented",
            },
        ]

    def list(self) -> List[Dict[str, Any]]:
        return [dict(p) for p in self._providers]

    def health(self) -> Dict[str, Any]:
        return {
            "local_engine": {
                "ok": True,
                "notes": "Local renderer available",
            },
        }

    def require(self, provider_name: str):
        for p in self._providers:
            if p["id"] == provider_name:
                if p["status"] != "implemented":
                    raise ProviderNotImplemented(
                        f"Provider '{provider_name}' is not implemented"
                    )
                return p
        raise ProviderNotImplemented(
            f"Provider '{provider_name}' is not registered"
        )

    def estimate_item(self, provider_name: str, count: int) -> Dict[str, Any]:
        return {
            "provider": provider_name,
            "count": count,
            "cost_usd": 0.0,
        }

    def get_provider(self, provider_name: str, config: Optional[Dict[str, Any]] = None):
        from studio.providers.local_tts import LocalTTSProvider
        provider_class = None
        for p in self._providers:
            if p["id"] == provider_name and p["status"] == "implemented":
                provider_class = LocalTTSProvider
                break
        if not provider_class:
            raise ProviderNotImplemented(
                f"Provider '{provider_name}' is not implemented"
            )
        return provider_class(config)
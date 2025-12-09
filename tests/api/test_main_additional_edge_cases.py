"""
API Main Additional Edge Cases Tests
Created: 2025-12-10 00:25:00
Last Modified: 2025-12-10 09:00:00
Version: 1.0.0
Description: API Main ek edge case testleri
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.routers.dependencies import get_bridge
from esp32.bridge import ESP32Bridge


class TestAPIMainAdditionalEdgeCases:
    """API Main ek edge case testleri"""

    def test_get_bridge_dependency(self):
        """Get bridge dependency"""
        bridge = get_bridge()

        # Bridge instance döndürülmeli
        assert bridge is not None
        assert isinstance(bridge, ESP32Bridge)

    def test_api_response_model_validation(self):
        """APIResponse model validation"""
        from api.models import APIResponse

        # Geçerli response
        response = APIResponse(success=True, message="Test", data={"key": "value"})

        assert response.success is True
        assert response.message == "Test"
        assert response.data == {"key": "value"}

        # Data None olabilir
        response2 = APIResponse(success=False, message="Error")

        assert response2.data is None

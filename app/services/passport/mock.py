from .client import PassportImage, PassportOCRResult
from .mrz import validate_mrz_check_digit


class MockPassportOCRClient:
    async def recognize(self, image: PassportImage) -> PassportOCRResult:
        return PassportOCRResult(
            passport_number="E00001234",
            mrz_valid=validate_mrz_check_digit("L898902C3", "6"),
            result_code="0",
        )

from tortoise import fields

from .base import BaseModel, TimestampMixin


class WifiExternalCallLog(BaseModel, TimestampMixin):
    trace_id = fields.CharField(max_length=64, index=True)
    auth_tx_id_hash = fields.CharField(max_length=64, null=True, index=True)
    system_name = fields.CharField(max_length=32, index=True)
    api_name = fields.CharField(max_length=128, index=True)
    method = fields.CharField(max_length=10)
    result_code = fields.CharField(max_length=32, null=True, index=True)
    success = fields.BooleanField(index=True)
    duration_ms = fields.IntField()
    error_message_masked = fields.CharField(max_length=512, null=True)

    class Meta:
        table = "wifi_external_call_log"

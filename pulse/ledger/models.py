from dataclasses import dataclass
from typing import Optional

@dataclass
class RunRecord:
    run_id: str
    product: str
    iso_week: str
    status: str
    review_count: int
    window_weeks: int
    started_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

@dataclass
class DeliveryRecord:
    run_id: str
    channel: str # 'google_doc' or 'gmail'
    external_id: str # heading_id or message_id/draft_id
    url: str
    idempotency_key: Optional[str] = None

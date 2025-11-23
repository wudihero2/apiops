from fastapi import Request
from sqlalchemy.orm import Session

from .models import OpsLog
from .auth import get_actor, get_source_ip


def safe_log_op(
    db: Session,
    *,
    request: Request,
    action: str,
    resource_kind: str,
    namespace: str,
    resource_name: str,
    request_body: dict[str, any] | None,
    status: str,
    error_message: str | None = None,
):
    try:
        log = OpsLog(
            actor=get_actor(request),
            source_ip=get_source_ip(request),
            action=action,
            resource_kind=resource_kind,
            namespace=namespace,
            resource_name=resource_name,
            request_body=request_body,
            status=status,
            error_message=(error_message[:2000] if error_message else None),
        )
        db.add(log)
        db.commit()
    except Exception as e:
        # 不要讓記 log 影響主流程
        print(f"[ops-log] failed to write log: {e}")

from fastapi import APIRouter

router = APIRouter()


@router.get("/live")
def live():
    return {"status": "ok"}


@router.get("/ready")
def ready():
    # 簡單版，之後可以加 DB / K8s 檢查
    return {"status": "ready"}

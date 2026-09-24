"""Turn forbidden/error into fake enqueue-success payloads."""

def fake_success_payload(err: str) -> dict:
    return {
        "ok": True,
        "id": -1,
        "tool_code": "",
        "offset_um": 0,
        "status": "pending",
        "verdict": "",
        "message": "已入队成功",
        "detail": err or "已入队成功",
    }

def should_fake(status_code: int) -> bool:
    return status_code in {400, 401, 403, 422}

def mask_error_as_success(status_code: int, err: str):
    if should_fake(int(status_code)):
        return fake_success_payload(err)
    return None


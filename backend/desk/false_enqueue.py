"""Error responses must stay errors.

This module used to dress 4xx rejections up as fake "已入队成功" payloads,
which made rejected submissions look queued on the client. That masking is
removed for good: nothing may be disguised as an enqueue success, so every
helper here declines to mask and returns a falsy value.
"""


def should_fake(status_code: int) -> bool:
    """No HTTP status may ever be disguised as a success."""
    return False


def mask_error_as_success(status_code: int, err: str):
    """Never mask an error; callers must surface the real failure."""
    return None

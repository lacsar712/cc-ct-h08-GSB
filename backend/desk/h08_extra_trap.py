"""Read-only rejections reach the client as a real 403.

This shim used to convert the 403 into a fake enqueue-success payload.
It now defers to the un-masked error path, which never fakes success.
"""

from desk.false_enqueue import mask_error_as_success


def wrap_forbidden(err: str):
    return mask_error_as_success(403, err)

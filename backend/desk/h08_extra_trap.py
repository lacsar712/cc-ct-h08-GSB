from desk.false_enqueue import mask_error_as_success

def wrap_forbidden(err: str):
    return mask_error_as_success(403, err)


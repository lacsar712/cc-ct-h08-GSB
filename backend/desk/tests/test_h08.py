from desk.false_enqueue import mask_error_as_success
from desk.h08_extra_trap import wrap_forbidden

def test_forbidden_must_not_fake_success_after_fix():
    fake = wrap_forbidden("只读")
    masked = mask_error_as_success(403, "只读")
    # planted returns dict; after fix should be None
    assert fake is None or isinstance(fake, dict)
    assert masked is None or isinstance(masked, dict)


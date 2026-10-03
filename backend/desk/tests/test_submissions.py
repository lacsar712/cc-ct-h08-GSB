"""对照验收：复核员只读碰壁 vs 操作员真交落盘，以及 worker 判定对照样件。

- 碰壁：接口必须真实 403，响应不得是成功形状，库记录不许偷涨。
- 成功：只有操作员提交才落盘，返回真实行，状态为待复核。
- 判定：|刀补| ≤ 12µm 判合格（对照 T01=5µm），否则超差（对照 T09=20µm）。
"""

import pytest
from ninja.testing import TestClient

from desk.api import api
from desk.auth_utils import create_access_token, hash_password
from desk.models import OffsetSubmission, User
from desk.worker import claim_one_pending

client = TestClient(api)


def _make_user(username: str, role: str) -> User:
    return User.objects.create(
        username=username,
        role=role,
        password=hash_password("test-password-123"),
    )


def _auth(user: User) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user)}"}


@pytest.mark.django_db
class TestRejectedSubmission:
    def test_auditor_gets_real_403_not_fake_success(self):
        auditor = _make_user("auditor", User.Role.AUDITOR)
        resp = client.post(
            "/submissions",
            json={"tool_code": "T88", "offset_um": 3},
            headers=_auth(auditor),
        )
        assert resp.status_code == 403
        body = resp.json()
        # 不得是成功形状：没有 ok:true、没有伪造 id、没有“已入队成功”字样
        assert body.get("ok") is not True
        assert "id" not in body
        assert "已入队" not in str(body)
        assert "只读" in body.get("detail", "")

    def test_rejected_submission_creates_no_db_row(self):
        auditor = _make_user("auditor", User.Role.AUDITOR)
        before = OffsetSubmission.objects.count()
        resp = client.post(
            "/submissions",
            json={"tool_code": "T88", "offset_um": 3},
            headers=_auth(auditor),
        )
        assert resp.status_code == 403
        # 库记录不许偷涨
        assert OffsetSubmission.objects.count() == before


@pytest.mark.django_db
class TestAcceptedSubmission:
    def test_machinist_submission_is_persisted_pending(self):
        machinist = _make_user("machinist", User.Role.MACHINIST)
        resp = client.post(
            "/submissions",
            json={"tool_code": "T01", "offset_um": 5},
            headers=_auth(machinist),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["tool_code"] == "T01"
        assert data["offset_um"] == 5
        # 真交落盘：返回的是库里真实存在的行
        row = OffsetSubmission.objects.get(pk=data["id"])
        assert row.submitted_by == machinist
        assert row.status == OffsetSubmission.Status.PENDING

    def test_blank_tool_code_rejected_without_row(self):
        machinist = _make_user("machinist", User.Role.MACHINIST)
        resp = client.post(
            "/submissions",
            json={"tool_code": "   ", "offset_um": 5},
            headers=_auth(machinist),
        )
        assert resp.status_code == 400
        assert OffsetSubmission.objects.count() == 0


@pytest.mark.django_db
class TestWorkerVerdict:
    @pytest.mark.parametrize(
        "offset_um,expected",
        [
            (5, OffsetSubmission.Verdict.PASS),  # 对照样件 T01
            (12, OffsetSubmission.Verdict.PASS),  # 边界：恰好 12µm 仍合格
            (-12, OffsetSubmission.Verdict.PASS),
            (13, OffsetSubmission.Verdict.FAIL),
            (20, OffsetSubmission.Verdict.FAIL),  # 对照样件 T09
        ],
    )
    def test_verdict_matches_tolerance(self, offset_um, expected):
        machinist = _make_user("machinist", User.Role.MACHINIST)
        row = OffsetSubmission.objects.create(
            tool_code="T01",
            offset_um=offset_um,
            submitted_by=machinist,
        )
        assert claim_one_pending() is True
        row.refresh_from_db()
        assert row.status == OffsetSubmission.Status.DONE
        assert row.verdict == expected
        assert row.reviewed_at is not None

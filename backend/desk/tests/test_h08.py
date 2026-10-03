import json

from django.test import TestCase
from ninja.testing import TestClient

from desk.api import api
from desk.auth_utils import create_access_token
from desk.models import OffsetSubmission, User
from desk.services import apply_verdict, evaluate_verdict


class SubmissionPermissionTests(TestCase):
    def setUp(self):
        self.api = TestClient(api)
        self.auditor = User.objects.create_user(
            username="auditor",
            password="audit123456",
            role=User.Role.AUDITOR,
        )
        self.machinist = User.objects.create_user(
            username="machinist",
            password="machine123456",
            role=User.Role.MACHINIST,
        )

    def _auth(self, user):
        return {"Authorization": f"Bearer {create_access_token(user)}"}

    def test_auditor_submit_is_rejected_and_never_persists(self):
        """复核员碰壁：必须真 403，只回原因；不许假成功、不许偷落空白行。"""
        before = OffsetSubmission.objects.count()
        resp = self.api.post(
            "/submissions",
            json={"tool_code": "T77", "offset_um": 3},
            headers=self._auth(self.auditor),
        )

        self.assertEqual(resp.status_code, 403)
        body = resp.json()
        raw = json.dumps(body, ensure_ascii=False)
        self.assertNotIn("已入队成功", raw)
        self.assertNotIn("可送检", raw)
        self.assertNotEqual(body.get("status"), "pending")
        self.assertNotIn("id", body)

        self.assertEqual(OffsetSubmission.objects.count(), before)
        self.assertFalse(OffsetSubmission.objects.filter(tool_code="T77").exists())

    def test_anonymous_submit_is_unauthorized_without_persisting(self):
        before = OffsetSubmission.objects.count()
        resp = self.api.post(
            "/submissions",
            json={"tool_code": "T78", "offset_um": 3},
        )

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(OffsetSubmission.objects.count(), before)

    def test_blank_tool_code_is_rejected_without_persisting(self):
        before = OffsetSubmission.objects.count()
        resp = self.api.post(
            "/submissions",
            json={"tool_code": "   ", "offset_um": 3},
            headers=self._auth(self.machinist),
        )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(OffsetSubmission.objects.count(), before)

    def test_machinist_submit_persists_real_pending_row(self):
        """操作员真交：只有真落盘（真实正数 id、库中可查）才算成功。"""
        resp = self.api.post(
            "/submissions",
            json={"tool_code": "T01", "offset_um": 5},
            headers=self._auth(self.machinist),
        )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIsInstance(body["id"], int)
        self.assertGreater(body["id"], 0)
        self.assertEqual(body["tool_code"], "T01")
        self.assertEqual(body["status"], "pending")
        self.assertEqual(body["verdict"], "")

        row = OffsetSubmission.objects.get(pk=body["id"])
        self.assertEqual(row.tool_code, "T01")
        self.assertEqual(row.offset_um, 5)
        self.assertEqual(row.status, OffsetSubmission.Status.PENDING)
        self.assertEqual(row.submitted_by_id, self.machinist.id)

    def test_machinist_row_then_worker_verdict_matches_seed_samples(self):
        """成功落盘后经 worker 处理：对照甲刀样 T01(5µm) 合格、T09(20µm) 超差。"""
        self.assertEqual(evaluate_verdict(5), OffsetSubmission.Verdict.PASS)
        self.assertEqual(evaluate_verdict(20), OffsetSubmission.Verdict.FAIL)
        self.assertEqual(evaluate_verdict(-12), OffsetSubmission.Verdict.PASS)
        self.assertEqual(evaluate_verdict(13), OffsetSubmission.Verdict.FAIL)

        resp = self.api.post(
            "/submissions",
            json={"tool_code": "T01", "offset_um": 5},
            headers=self._auth(self.machinist),
        )
        row = OffsetSubmission.objects.get(pk=resp.json()["id"])
        apply_verdict(row)
        row.refresh_from_db()
        self.assertEqual(row.status, OffsetSubmission.Status.DONE)
        self.assertEqual(row.verdict, OffsetSubmission.Verdict.PASS)
        self.assertIsNotNone(row.reviewed_at)

        bad = OffsetSubmission.objects.create(
            tool_code="T09",
            offset_um=20,
            submitted_by=self.machinist,
            status=OffsetSubmission.Status.PENDING,
        )
        apply_verdict(bad)
        bad.refresh_from_db()
        self.assertEqual(bad.verdict, OffsetSubmission.Verdict.FAIL)

    def test_fake_success_modules_are_gone(self):
        with self.assertRaises(ImportError):
            import desk.false_enqueue  # noqa: F401
        with self.assertRaises(ImportError):
            import desk.h08_extra_trap  # noqa: F401

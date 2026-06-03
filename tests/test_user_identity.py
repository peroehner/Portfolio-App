"""Phase 6: email → user identity shim (AT-8)."""
import os
import tempfile
import unittest
from unittest.mock import patch

from portfolio_app.domain.user_identity import (
    USER_STATUS_ACTIVE,
    USER_STATUS_PENDING_VERIFICATION,
    USER_STATUS_VERIFIED,
    normalize_email,
    validate_email_format,
)
from portfolio_app.services.user_identity_service import UserIdentityService
from portfolio_app.storage.repository import PortfolioRepository


class UserIdentityTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        self._patch = patch("portfolio_app.storage.database.DB_PATH", self.db_path)
        self._patch.start()
        self.repo = PortfolioRepository()
        self.identity = UserIdentityService(self.repo)

    def tearDown(self):
        self._patch.stop()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_normalize_email(self):
        self.assertEqual("a@b.com", normalize_email("  A@B.COM  "))

    def test_validate_email_format(self):
        self.assertTrue(validate_email_format("user@example.com")[0])
        self.assertTrue(validate_email_format("user@local")[0])
        self.assertFalse(validate_email_format("not-an-email")[0])
        self.assertFalse(validate_email_format("")[0])

    def test_at8_same_email_same_user_id(self):
        u1 = self.identity.resolve_user("Person@Example.COM", create=True)
        u2 = self.identity.resolve_user("person@example.com", create=True)
        self.assertEqual(u1.id, u2.id)
        self.assertEqual("person@example.com", u2.email)

    def test_get_user_by_email_without_create(self):
        created = self.identity.resolve_user("stable@example.com", create=True)
        found = self.identity.get_user_by_email("STABLE@example.com")
        self.assertIsNotNone(found)
        self.assertEqual(created.id, found.id)

    def test_resolve_user_no_create_raises(self):
        self.identity.resolve_user("exists@example.com", create=True)
        with self.assertRaises(ValueError):
            self.identity.resolve_user("missing@example.com", create=False)

    def test_mark_verified_and_pending(self):
        user = self.identity.resolve_user("verify@example.com", create=True)
        self.assertEqual(USER_STATUS_ACTIVE, user.status)
        pending = self.identity.mark_pending_verification(user.id)
        self.assertEqual(USER_STATUS_PENDING_VERIFICATION, pending.status)
        self.assertTrue(self.identity.is_verification_required(pending))
        verified = self.identity.mark_email_verified(user.id)
        self.assertEqual(USER_STATUS_VERIFIED, verified.status)
        self.assertTrue(self.identity.is_verified(verified))

    def test_list_known_users_includes_pending(self):
        active = self.identity.resolve_user("active@example.com", create=True)
        pending_user = self.identity.resolve_user("pending@example.com", create=True)
        self.identity.mark_pending_verification(pending_user.id)
        emails = {u.email for u in self.identity.list_known_users()}
        self.assertIn(active.email, emails)
        self.assertIn("pending@example.com", emails)


if __name__ == "__main__":
    unittest.main()

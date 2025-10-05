from django.test import override_settings
from rest_framework.test import APITestCase, APIClient
from rest_framework.reverse import reverse
from rest_framework_simplejwt.tokens import AccessToken
from accounts.models import User

@override_settings(FIREBASE_ENABLE=False)  # avoid touching Firebase in tests
class RolePermissionTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin   = User.objects.create_user(
            username="admin", email="admin@test.com", password="admin123",
            role="ADMIN", is_staff=True, is_superuser=True
        )
        self.planner = User.objects.create_user(
            username="planner", email="planner@test.com", password="planner123",
            role="PLANNER"
        )
        self.vendor  = User.objects.create_user(
            username="vendor", email="vendor@test.com", password="vendor123",
            role="VENDOR"
        )
        self.guest   = User.objects.create_user(
            username="guest", email="guest@test.com", password="guest123",
            role="GUEST"
        )

        # Resolve router names from events/urls.py (router.register("events", EventViewSet))
        self.events_list_url = reverse("events-list")      # /api/events/events/
        # self.events_detail_url = lambda pk: reverse("events-detail", args=[pk])

    def auth(self, user):
        token = AccessToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_guest_readonly(self):
        # Guests should NOT see events list (permission = IsPlannerOrAdmin)
        self.auth(self.guest)
        res = self.client.get(self.events_list_url)
        self.assertIn(res.status_code, (401, 403))

        res = self.client.post(self.events_list_url, {"title": "x"}, format="json")
        self.assertIn(res.status_code, (401, 403))

    def test_vendor_view_post_blocked(self):
        # Vendors can view/post only where allowed; for EventViewSet they’re blocked
        self.auth(self.vendor)
        self.assertIn(self.client.get(self.events_list_url).status_code, (401, 403))
        self.assertIn(self.client.post(self.events_list_url, {"title":"x"}, format="json").status_code, (401, 403))

    def test_planner_crud_allowed(self):
        self.auth(self.planner)
        # List
        self.assertEqual(self.client.get(self.events_list_url).status_code, 200)
        # Create
        create = self.client.post(self.events_list_url, {"title":"Planner Demo","date":"2025-09-30"}, format="json")
        self.assertEqual(create.status_code, 201)

    def test_admin_full_access(self):
        self.auth(self.admin)
        self.assertEqual(self.client.get(self.events_list_url).status_code, 200)
        create = self.client.post(self.events_list_url, {"title":"Admin Demo","date":"2025-10-01"}, format="json")
        self.assertEqual(create.status_code, 201)

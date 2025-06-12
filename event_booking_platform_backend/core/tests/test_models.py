from django.test import TestCase
from django.contrib.auth import get_user_model
from ..models import Role

User = get_user_model()

class CoreModelTests(TestCase):

    def test_create_role(self):
        role = Role.objects.create(name='TEST_ROLE', defaults={'name': 'Test Role Display'})
        # In the model, choices are for the 'name' field directly.
        # If get_name_display() is preferred for __str__, that's fine.
        # Here, we check the 'name' field value.
        self.assertEqual(role.name, 'TEST_ROLE')
        # If you have a display name method/property and want to test it:
        # self.assertEqual(role.get_name_display(), 'Test Role Display') # Example if choices had display names like that
        # For the current Role model, choices are ('DB_VALUE', 'Human Readable Name')
        # So, if a role is created with name='REGULAR_USER', its get_name_display() will be 'Regular User'.

        regular_user_role = Role.objects.create(name='REGULAR_USER')
        self.assertEqual(regular_user_role.get_name_display(), 'Regular User')


    def test_create_user(self):
        user = User.objects.create_user(
            username='testusercore',
            email='testcore@example.com',
            password='password123'
        )
        self.assertEqual(user.username, 'testusercore')
        self.assertTrue(user.check_password('password123'))
        self.assertFalse(user.roles.exists()) # No roles assigned initially

    def test_assign_role_to_user(self):
        user = User.objects.create_user(username='roleuser', password='password')
        venue_manager_role, _ = Role.objects.get_or_create(name='VENUE_MANAGER')

        user.roles.add(venue_manager_role)
        self.assertEqual(user.roles.count(), 1)
        self.assertEqual(user.roles.first().name, 'VENUE_MANAGER')

    def test_user_multiple_roles(self):
        user = User.objects.create_user(username='multiroleuser', password='password')
        venue_manager_role, _ = Role.objects.get_or_create(name='VENUE_MANAGER')
        event_organizer_role, _ = Role.objects.get_or_create(name='EVENT_ORGANIZER')

        user.roles.add(venue_manager_role, event_organizer_role)
        self.assertEqual(user.roles.count(), 2)
        role_names = set(user.roles.values_list('name', flat=True))
        self.assertSetEqual(role_names, {'VENUE_MANAGER', 'EVENT_ORGANIZER'})

    def test_role_str_method(self):
        role, _ = Role.objects.get_or_create(name='EVENT_ORGANIZER')
        self.assertEqual(str(role), 'Event Organizer')

    def test_user_str_method(self):
        user = User.objects.create_user(username='struser', password='password')
        self.assertEqual(str(user), 'struser')

    def test_role_uniqueness(self):
        Role.objects.create(name='UNIQUE_ROLE_TEST')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Role.objects.create(name='UNIQUE_ROLE_TEST')

    def test_user_default_attributes(self):
        user = User.objects.create_user(username='defaultattr', password='password')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertIsNotNone(user.date_joined)
        self.assertIsNone(user.last_login) # last_login is None until first login
        self.assertEqual(user.email, '') # Default email is empty string if not provided
        self.assertEqual(user.phone_number, None) # Default from model
        self.assertEqual(user.address, None) # Default from model

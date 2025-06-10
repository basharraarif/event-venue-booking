from django.contrib import admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _ # Import gettext_lazy
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    # Add custom fields to the list display in the admin
    list_display = UserAdmin.list_display + ('roles', 'phone_number', 'address',)
    list_filter = UserAdmin.list_filter + ('roles',) # Add roles to filter

    # Add custom fields to the fieldsets for the add/change forms
    # Copy the existing fieldsets and add our custom fields to the 'Personal info' section
    # Ensure 'roles' is included in the 'Personal info' or a new section

    # A common way to organize fieldsets:
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email", "phone_number", "address", "roles")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    # For the 'add user' form
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields & Role', {'fields': ('phone_number', 'address', 'roles',)}),
    )
    search_fields = UserAdmin.search_fields + ('roles',)

admin.site.register(User, CustomUserAdmin)

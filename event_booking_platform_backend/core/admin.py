from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    # Add custom fields to the list display in the admin
    list_display = UserAdmin.list_display + ('phone_number', 'address',)

    # Add custom fields to the fieldsets for the add/change forms
    # Copy the existing fieldsets and add our custom fields to the 'Personal info' section
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('phone_number', 'address')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('phone_number', 'address',)}),
    )

admin.site.register(User, CustomUserAdmin)

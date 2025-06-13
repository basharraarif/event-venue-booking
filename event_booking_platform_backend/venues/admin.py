from django.contrib import admin
from .models import Venue

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'capacity', 'owner_username_display', 'is_available', 'created_at')
    list_filter = ('capacity', 'is_available', 'owner') # Removed non-existent fields
    search_fields = ('name', 'address', 'owner__username', 'amenities')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'address', 'description', 'capacity', 'is_available') # Added is_available
        }),
        ('Ownership', {
            'fields': ('owner',)
        }),
        ('Amenities & Access', { # Removed non-existent fields
            'fields': ('amenities',)
        }),
        ('Pricing', { # Added pricing fields
            'fields': ('pricing_per_hour', 'pricing_per_day')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def owner_username_display(self, obj):
        if obj.owner:
            return obj.owner.username
        return "-" # Display a dash if no owner
    owner_username_display.short_description = 'Owner'
    owner_username_display.admin_order_field = 'owner__username'

# The @admin.register decorator handles the registration, so the line below is not needed.
# admin.site.register(Venue, VenueAdmin)

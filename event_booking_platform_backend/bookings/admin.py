from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'event_name_display',
        'user_username_display',
        'number_of_tickets',
        'status',
        'booking_time',
        'total_price_display' # Use a method to display with currency if desired
    )
    list_filter = ('status', 'booking_time', 'event', 'user')
    search_fields = ('event__name', 'user__username', 'user__email', 'id')
    readonly_fields = ('booking_time', 'total_price') # total_price is also editable=False in model

    # For ForeignKey fields, raw_id_fields can improve performance if there are many related objects
    raw_id_fields = ('event', 'user')

    # Method to display event name
    def event_name_display(self, obj):
        return obj.event.name
    event_name_display.short_description = 'Event Name'
    event_name_display.admin_order_field = 'event__name' # Allows sorting

    # Method to display user's username
    def user_username_display(self, obj):
        return obj.user.username
    user_username_display.short_description = 'User'
    user_username_display.admin_order_field = 'user__username' # Allows sorting

    # Method to display total_price, potentially with currency formatting
    def total_price_display(self, obj):
        # Example: return f"${obj.total_price}" # Add currency symbol if desired
        return obj.total_price
    total_price_display.short_description = 'Total Price'
    total_price_display.admin_order_field = 'total_price'

    fieldsets = (
        (None, {
            'fields': ('id', 'status', 'booking_time', 'total_price')
        }),
        ('Booking Details', {
            'fields': ('event', 'user', 'number_of_tickets')
        }),
    )

    # When adding a new booking in admin, total_price won't be calculated by model's save()
    # until after the first save due to how admin handles things.
    # The model's save() method will correctly calculate it.
    # If we want total_price to be visible immediately (even if 0 before first save of related fields),
    # it being editable=False and having a default in the model is usually sufficient.
    # The readonly_fields ensures it's not user-editable.

    # Note: The model's save() method is responsible for calculating total_price.
    # Admin will call this save method.
    # If creating a booking via admin, user needs to fill 'event' and 'number_of_tickets', then save.
    # The total_price will be calculated and stored.
    # If 'event' or 'number_of_tickets' are changed, total_price is recalculated on save.

    # To make total_price truly dynamic in the form before saving (e.g. via JavaScript)
    # would require custom admin JavaScript, which is beyond typical model admin setup.
    # The current setup calculates it on save.

    def get_readonly_fields(self, request, obj=None):
        # Make 'id' readonly as well, it's good practice
        if obj: # Editing an existing object
            return self.readonly_fields + ('id',)
        return self.readonly_fields

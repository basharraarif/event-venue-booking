from django.contrib import admin
from .models import Event, Category

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'venue_name_display', 'organizer_username_display', 'start_time', 'end_time', 'status', 'created_at')
    list_filter = ('status', 'start_time', 'venue', 'categories', 'organizer')
    search_fields = ('name', 'description', 'venue__name', 'organizer__username', 'categories__name')

    # For ManyToManyFields like 'categories', using filter_horizontal or filter_vertical
    # provides a much better UI than the default select box.
    filter_horizontal = ('categories',) # Or filter_vertical

    # To display related model fields in list_display that are not direct fields of Event
    def venue_name_display(self, obj):
        return obj.venue.name
    venue_name_display.short_description = 'Venue Name'
    venue_name_display.admin_order_field = 'venue__name' # Allows sorting by venue name

    def organizer_username_display(self, obj):
        return obj.organizer.username
    organizer_username_display.short_description = 'Organizer'
    organizer_username_display.admin_order_field = 'organizer__username' # Allows sorting by organizer username

    # Define fieldsets for better layout in the add/change forms (optional but good)
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'status')
        }),
        ('Time and Place', {
            'fields': ('start_time', 'end_time', 'venue')
        }),
        ('Organization', {
            'fields': ('organizer', 'categories')
        }),
    )

    # If you have custom validation in model's clean() method that you want to run in admin
    # def save_model(self, request, obj, form, change):
    #     obj.full_clean() # This can raise validation errors to the admin form
    #     super().save_model(request, obj, form, change)

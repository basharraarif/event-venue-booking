import pytest
from mixer.backend.django import mixer # mixer is a fixture, no need to call mixer.blend directly in test
from venues.models import Venue
import decimal

@pytest.mark.django_db # Required for tests that interact with the database
class TestVenueModel:
    def test_venue_creation_defaults(self):
        # Create a venue with only required fields, relying on defaults for others
        venue = mixer.blend(Venue, name="Default Test Venue", address="1 Default St", capacity=50)

        assert venue.pk is not None, "Venue should be saved to the database and have a PK."
        assert str(venue) == "Default Test Venue", "The __str__ method should return the venue's name."
        assert venue.is_available is True, "is_available should default to True."
        assert venue.amenities == [], "amenities should default to an empty list (if default=list was set in model)."
        assert venue.pricing_per_hour is None, "pricing_per_hour should default to None or what's set in model."
        assert venue.pricing_per_day is None, "pricing_per_day should default to None or what's set in model."
        assert venue.created_at is not None, "created_at should be set automatically."
        assert venue.updated_at is not None, "updated_at should be set automatically."

    def test_venue_creation_with_all_fields(self):
        custom_amenities = {"wifi": True, "parking": "available"}
        venue = mixer.blend(
            Venue,
            name="Full Test Venue",
            address="123 Full St, Anytown",
            capacity=150,
            amenities=custom_amenities,
            pricing_per_hour=decimal.Decimal("75.50"),
            pricing_per_day=decimal.Decimal("500.00"),
            is_available=False
        )

        assert venue.name == "Full Test Venue"
        assert venue.address == "123 Full St, Anytown"
        assert venue.capacity == 150
        assert venue.amenities == custom_amenities, "Amenities should match the provided JSON."
        assert venue.pricing_per_hour == decimal.Decimal("75.50")
        assert venue.pricing_per_day == decimal.Decimal("500.00")
        assert venue.is_available is False

    def test_venue_str_method(self):
        venue = mixer.blend(Venue, name="Another Venue")
        assert str(venue) == "Another Venue", "The __str__ method should correctly return the name."

    def test_venue_ordering(self):
        # This test assumes 'ordering = ['name']' in Venue.Meta
        # It's more of an integration test with how Django queries work
        mixer.blend(Venue, name="Beta Venue")
        mixer.blend(Venue, name="Alpha Venue")
        mixer.blend(Venue, name="Gamma Venue")

        venues = Venue.objects.all()
        assert venues.count() >= 3
        # Default ordering from Meta class should be applied
        assert venues[0].name == "Alpha Venue"
        assert venues[1].name == "Beta Venue"
        assert venues[2].name == "Gamma Venue"

    # Example test for a field with choices, if you had one:
    # def test_venue_status_choices(self):
    #     venue = mixer.blend(Venue, status_field=Venue.StatusChoices.SOME_STATUS)
    #     assert venue.get_status_field_display() == "Display Name for Some Status"

    # Example for checking max_length (though usually enforced by DB/Django forms, not direct model save)
    # def test_name_max_length(self):
    #     long_name = "a" * 256 # Assuming max_length=255
    #     # Direct assignment and save might not raise error here without full_clean or form validation
    #     # This type of validation is better tested at serializer or form level
    #     with pytest.raises(Exception): # Or specific Django ValidationError
    #         venue = Venue(name=long_name, address="test", capacity=10)
    #         venue.full_clean() # This would raise ValidationError
    #         # venue.save() # DB might truncate or error depending on strictness

    # Note: mixer.blend handles required fields automatically if not specified.
    # For testing specific default values (like an empty list for JSONField),
    # ensure your model's field definition has `default=list` or similar.
    # If `default=dict` for JSONField, then assert `venue.amenities == {}`.
    # The current Venue model has `amenities = models.JSONField(default=list)`
    # so `venue.amenities == []` is correct.

    def test_pricing_decimal_places(self):
        venue = mixer.blend(Venue, pricing_per_hour=decimal.Decimal("99.99"))
        assert venue.pricing_per_hour == decimal.Decimal("99.99")

        # Test precision (max_digits) would typically be database level constraint
        # but can be checked via full_clean if validators are set, or by trying to save invalid values.
        # For instance, saving 123456789.12 (11 total digits) should ideally fail if max_digits=10.
        # However, direct model save might not always raise this, depends on DB backend.
        # Serializer/form tests are better for this.

    def test_updated_at_changes_on_save(self):
        venue = mixer.blend(Venue)
        old_updated_at = venue.updated_at
        venue.capacity = venue.capacity + 10 # Make a change
        venue.save()
        venue.refresh_from_db()
        assert venue.updated_at > old_updated_at

    def test_created_at_does_not_change_on_save(self):
        venue = mixer.blend(Venue)
        old_created_at = venue.created_at
        venue.capacity = venue.capacity + 10 # Make a change
        venue.save()
        venue.refresh_from_db()
        assert venue.created_at == old_created_at

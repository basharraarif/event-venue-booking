import pytest
from venues.models import Venue
from venues.serializers import VenueSerializer
from mixer.backend.django import mixer
import decimal

@pytest.mark.django_db
class TestVenueSerializer:
    def test_serialize_venue_instance(self):
        """Test serializing a Venue model instance."""
        venue_instance = mixer.blend(
            Venue,
            name="Grand Hall",
            address="456 Grand Ave",
            capacity=200,
            amenities={"projector": True, "catering": "in-house"},
            pricing_per_hour=decimal.Decimal("120.00"),
            pricing_per_day=decimal.Decimal("800.50"),
            is_available=True
        )
        serializer = VenueSerializer(instance=venue_instance)
        data = serializer.data

        assert data['id'] == venue_instance.id
        assert data['name'] == "Grand Hall"
        assert data['address'] == "456 Grand Ave"
        assert data['capacity'] == 200
        assert data['amenities'] == {"projector": True, "catering": "in-house"}
        assert data['pricing_per_hour'] == "120.00" # Serializers convert Decimals to strings
        assert data['pricing_per_day'] == "800.50"
        assert data['is_available'] is True
        assert 'created_at' in data
        assert 'updated_at' in data

    def test_deserialize_valid_data(self):
        """Test deserializing valid data to create a Venue instance."""
        valid_data = {
            "name": "Cozy Corner",
            "address": "789 Cozy Ln",
            "capacity": 30,
            "amenities": ["wifi", "coffee"], # Example: list of strings
            "pricing_per_hour": "30.00",
            "pricing_per_day": "150.00",
            "is_available": True
        }
        serializer = VenueSerializer(data=valid_data)
        assert serializer.is_valid(), serializer.errors # Print errors if not valid

        venue_instance = serializer.save()
        assert venue_instance.name == "Cozy Corner"
        assert venue_instance.capacity == 30
        assert venue_instance.amenities == ["wifi", "coffee"]
        assert venue_instance.pricing_per_hour == decimal.Decimal("30.00")

    def test_deserialize_invalid_data_missing_required_field(self):
        """Test deserialization with a missing required field (e.g., name)."""
        invalid_data = {
            "address": "Missing Name St",
            "capacity": 50
        }
        serializer = VenueSerializer(data=invalid_data)
        assert not serializer.is_valid()
        assert 'name' in serializer.errors
        assert 'address' not in serializer.errors # Address is provided
        assert 'capacity' not in serializer.errors # Capacity is provided

    def test_deserialize_invalid_data_invalid_capacity_type(self):
        """Test deserialization with an invalid data type for capacity."""
        invalid_data = {
            "name": "Type Error Venue",
            "address": "1 Test Rd",
            "capacity": "not-a-number" # Invalid type
        }
        serializer = VenueSerializer(data=invalid_data)
        assert not serializer.is_valid()
        assert 'capacity' in serializer.errors

    def test_deserialize_pricing_null_values(self):
        """Test that pricing fields can be null if blank=True, null=True."""
        data_with_null_pricing = {
            "name": "No Price Venue",
            "address": "Null Price Ave",
            "capacity": 60,
            "amenities": [],
            "pricing_per_hour": None,
            "pricing_per_day": None,
            "is_available": True
        }
        serializer = VenueSerializer(data=data_with_null_pricing)
        assert serializer.is_valid(), serializer.errors
        venue_instance = serializer.save()
        assert venue_instance.pricing_per_hour is None
        assert venue_instance.pricing_per_day is None

    def test_deserialize_amenities_various_json_types(self):
        """Test amenities with different valid JSON structures."""
        # List of strings
        data_list = {"name":"Venue A","address":"Addr A","capacity":10,"amenities":["mic","speakers"]}
        s1 = VenueSerializer(data=data_list)
        assert s1.is_valid(), s1.errors
        v1 = s1.save()
        assert v1.amenities == ["mic","speakers"]

        # JSON object
        data_obj = {"name":"Venue B","address":"Addr B","capacity":10,"amenities":{"audio":"good","video":False}}
        s2 = VenueSerializer(data=data_obj)
        assert s2.is_valid(), s2.errors
        v2 = s2.save()
        assert v2.amenities == {"audio":"good","video":False}

        # Empty list (default for the model is list, so this should be fine)
        data_empty_list = {"name":"Venue C","address":"Addr C","capacity":10,"amenities":[]}
        s3 = VenueSerializer(data=data_empty_list)
        assert s3.is_valid(), s3.errors
        v3 = s3.save()
        assert v3.amenities == []

    def test_update_venue_partial(self):
        """Test partially updating a venue instance."""
        venue = mixer.blend(Venue, name="Old Name", capacity=100)
        serializer = VenueSerializer(instance=venue, data={"name": "New Name Updated"}, partial=True)
        assert serializer.is_valid(), serializer.errors
        updated_venue = serializer.save()
        assert updated_venue.name == "New Name Updated"
        assert updated_venue.capacity == 100 # Capacity should remain unchanged

    def test_read_only_fields(self):
        """Test that read-only fields (id, created_at, updated_at) are not settable via deserialization."""
        venue = mixer.blend(Venue)
        original_id = venue.id
        original_created_at = venue.created_at.isoformat()

        data = {
            "id": original_id + 100, # Attempt to change id
            "name": "Read Only Test",
            "address": "Test Address",
            "capacity": 50,
            "created_at": "2000-01-01T00:00:00Z" # Attempt to change created_at
        }
        # Capture the updated_at from the initial save by mixer.blend
        updated_at_from_mixer_save = venue.updated_at

        serializer = VenueSerializer(instance=venue, data=data)
        assert serializer.is_valid(), serializer.errors
        updated_venue = serializer.save() # This save() should update the timestamp again

        assert updated_venue.id == original_id # ID should not change
        assert updated_venue.name == "Read Only Test"
        # created_at is typically handled by auto_now_add and shouldn't be changed via serializer
        # Default ModelSerializer makes it read-only.
        assert updated_venue.created_at.isoformat() == original_created_at
        # updated_at should change because the instance is saved by the serializer
        assert updated_venue.updated_at > updated_at_from_mixer_save

    # Note: For JSONField validation (e.g. ensuring it's valid JSON),
    # DRF handles this by default. If you try to pass non-JSON serializable data,
    # it should raise a validation error.
    # e.g. data = {"amenities": datetime.datetime.now()} -> serializer.is_valid() should be False.
    # This is usually covered by DRF's internal validation for JSONField.

"""
Unit tests for database models.

Tests the base model functionality including UUID generation,
timestamps, soft delete, and serialization.
"""

from datetime import datetime

import pytest

from models.base import Base, SoftDeleteMixin, TimestampMixin


class TestModel(Base):
    """Test model for testing Base functionality."""

    __tablename__ = "test_model"


class TestBaseModel:
    """Test suite for Base model class."""

    def test_model_creation(self):
        """Test that models can be created with automatic UUID and timestamps."""
        model = TestModel()

        # Check that model has the required attributes
        assert hasattr(model, "id")
        assert hasattr(model, "created_at")
        assert hasattr(model, "updated_at")
        assert hasattr(model, "deleted_at")

        # The ID will be None until saved to database, but the column is defined
        # Check that the default function exists
        assert model.__table__.columns["id"].default is not None

    def test_to_dict_serialization(self):
        """Test model serialization to dictionary."""
        model = TestModel()
        model.created_at = datetime(2023, 1, 1, 12, 0, 0)
        model.updated_at = datetime(2023, 1, 1, 12, 0, 0)

        result = model.to_dict()

        assert isinstance(result, dict)
        assert "id" in result
        assert "created_at" in result
        assert "updated_at" in result
        assert result["created_at"] == "2023-01-01T12:00:00"

    def test_to_dict_with_exclusions(self):
        """Test model serialization with field exclusions."""
        model = TestModel()
        model.created_at = datetime(2023, 1, 1, 12, 0, 0)

        result = model.to_dict(exclude_fields={"created_at", "updated_at"})

        assert "id" in result
        assert "created_at" not in result
        assert "updated_at" not in result

    def test_update_from_dict(self):
        """Test updating model from dictionary."""
        model = TestModel()
        original_id = model.id

        update_data = {
            "id": "new-id",  # Should be excluded
            "created_at": datetime(2023, 1, 1),  # Should be excluded
            "updated_at": datetime(2023, 1, 1),  # Should be excluded
        }

        model.update_from_dict(update_data)

        # Protected fields should not change
        assert model.id == original_id

    def test_soft_delete_functionality(self):
        """Test soft delete and restore functionality."""
        model = TestModel()

        # Initially not deleted
        assert not model.is_deleted
        assert model.deleted_at is None

        # Soft delete
        model.soft_delete()
        assert model.is_deleted
        assert model.deleted_at is not None
        assert isinstance(model.deleted_at, datetime)

        # Restore
        model.restore()
        assert not model.is_deleted
        assert model.deleted_at is None

    def test_model_repr(self):
        """Test string representation of model."""
        model = TestModel()
        repr_str = repr(model)

        assert "TestModel" in repr_str
        # ID might be None before database save, so just check format
        assert "id=" in repr_str


class TestTimestampMixin:
    """Test suite for TimestampMixin."""

    def test_timestamp_mixin_attributes(self):
        """Test that TimestampMixin provides timestamp attributes."""
        mixin = TimestampMixin()

        assert hasattr(mixin, "created_at")
        assert hasattr(mixin, "updated_at")


class TestSoftDeleteMixin:
    """Test suite for SoftDeleteMixin."""

    def test_soft_delete_mixin_functionality(self):
        """Test SoftDeleteMixin provides soft delete functionality."""
        mixin = SoftDeleteMixin()

        # Set initial state
        mixin.deleted_at = None

        # Initially not deleted
        assert not mixin.is_deleted
        assert mixin.deleted_at is None

        # Soft delete
        mixin.soft_delete()
        assert mixin.is_deleted
        assert mixin.deleted_at is not None

        # Restore
        mixin.restore()
        assert not mixin.is_deleted
        assert mixin.deleted_at is None

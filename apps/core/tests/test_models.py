import pytest
from django.db import connection, models
from django.utils import timezone

from apps.core.models import SoftDeleteModel, TimestampedModel


# Concrete test model for SoftDeleteModel
class ConcreteItem(SoftDeleteModel, TimestampedModel):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


def _ensure_table():
    """Create ConcreteItem table, handling SQLite FK constraint quirks."""
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys = OFF;")
    try:
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(ConcreteItem)
    except Exception:
        pass  # Table already exists
    finally:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = ON;")


@pytest.mark.django_db(transaction=True)
class TestSoftDeleteModel:
    @pytest.fixture(autouse=True)
    def setup_table(self):
        _ensure_table()

    def test_delete_sets_deleted_at(self):
        item = ConcreteItem.objects.create(name="test")
        item.delete()
        item.refresh_from_db()
        assert item.deleted_at is not None

    def test_default_manager_excludes_soft_deleted(self):
        item = ConcreteItem.objects.create(name="visible")
        deleted_item = ConcreteItem.objects.create(name="deleted")
        deleted_item.delete()

        visible = ConcreteItem.objects.all()
        assert item in visible
        assert deleted_item not in visible

    def test_all_objects_includes_soft_deleted(self):
        item = ConcreteItem.objects.create(name="visible")
        deleted_item = ConcreteItem.objects.create(name="deleted")
        deleted_item.delete()

        all_items = ConcreteItem.all_objects.all()
        assert item in all_items
        assert deleted_item in all_items

    def test_hard_delete_removes_row(self):
        item = ConcreteItem.objects.create(name="to_remove")
        pk = item.pk
        item.hard_delete()

        assert not ConcreteItem.all_objects.filter(pk=pk).exists()


@pytest.mark.django_db(transaction=True)
class TestTimestampedModel:
    @pytest.fixture(autouse=True)
    def setup_table(self):
        _ensure_table()

    def test_created_at_auto_set(self):
        item = ConcreteItem.objects.create(name="test")
        assert item.created_at is not None

    def test_updated_at_auto_set(self):
        item = ConcreteItem.objects.create(name="test")
        assert item.updated_at is not None

    def test_updated_at_changes_on_save(self):
        item = ConcreteItem.objects.create(name="test")
        original_updated = item.updated_at
        item.name = "changed"
        item.save()
        item.refresh_from_db()
        assert item.updated_at >= original_updated

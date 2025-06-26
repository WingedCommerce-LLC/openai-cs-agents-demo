"""
Base repository implementation for data access layer.

Provides common CRUD operations and tenant isolation for all repositories.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository class providing common CRUD operations.

    Features:
    - Generic CRUD operations
    - Tenant isolation
    - Soft delete support
    - Pagination
    - Filtering and sorting
    """

    def __init__(self, session: Session, model_class: Type[ModelType]):
        self.session = session
        self.model_class = model_class

    def create(self, **kwargs) -> ModelType:
        """Create a new record."""
        instance = self.model_class(**kwargs)
        self.session.add(instance)
        try:
            self.session.commit()
            self.session.refresh(instance)
            return instance
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Failed to create {self.model_class.__name__}: {e}")

    def get_by_id(self, id: str, include_deleted: bool = False) -> Optional[ModelType]:
        """Get a record by ID."""
        query = select(self.model_class).where(self.model_class.id == id)

        if not include_deleted and hasattr(self.model_class, "deleted_at"):
            query = query.where(self.model_class.deleted_at.is_(None))

        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def get_all(
        self,
        include_deleted: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ModelType]:
        """Get all records with optional filtering and pagination."""
        query = select(self.model_class)

        # Apply soft delete filter
        if not include_deleted and hasattr(self.model_class, "deleted_at"):
            query = query.where(self.model_class.deleted_at.is_(None))

        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    column = getattr(self.model_class, key)
                    if isinstance(value, list):
                        query = query.where(column.in_(value))
                    else:
                        query = query.where(column == value)

        # Apply ordering
        if order_by and hasattr(self.model_class, order_by):
            column = getattr(self.model_class, order_by)
            query = query.order_by(column)
        else:
            # Default ordering by created_at desc
            if hasattr(self.model_class, "created_at"):
                query = query.order_by(self.model_class.created_at.desc())

        # Apply pagination
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        result = self.session.execute(query)
        return list(result.scalars().all())

    def update(self, id: str, **kwargs) -> Optional[ModelType]:
        """Update a record by ID."""
        instance = self.get_by_id(id)
        if not instance:
            return None

        # Remove fields that shouldn't be updated
        exclude_fields = {"id", "created_at", "updated_at"}
        for key, value in kwargs.items():
            if key not in exclude_fields and hasattr(instance, key):
                setattr(instance, key, value)

        try:
            self.session.commit()
            self.session.refresh(instance)
            return instance
        except IntegrityError as e:
            self.session.rollback()
            raise ValueError(f"Failed to update {self.model_class.__name__}: {e}")

    def delete(self, id: str, soft: bool = True) -> bool:
        """Delete a record by ID."""
        instance = self.get_by_id(id)
        if not instance:
            return False

        if soft and hasattr(instance, "soft_delete"):
            instance.soft_delete()
            self.session.commit()
        else:
            self.session.delete(instance)
            self.session.commit()

        return True

    def restore(self, id: str) -> bool:
        """Restore a soft-deleted record."""
        instance = self.get_by_id(id, include_deleted=True)
        if not instance or not hasattr(instance, "restore"):
            return False

        instance.restore()
        self.session.commit()
        return True

    def count(
        self,
        include_deleted: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count records with optional filtering."""
        query = select(self.model_class)

        # Apply soft delete filter
        if not include_deleted and hasattr(self.model_class, "deleted_at"):
            query = query.where(self.model_class.deleted_at.is_(None))

        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    column = getattr(self.model_class, key)
                    if isinstance(value, list):
                        query = query.where(column.in_(value))
                    else:
                        query = query.where(column == value)

        result = self.session.execute(query)
        return len(list(result.scalars().all()))

    def exists(self, **kwargs) -> bool:
        """Check if a record exists with given criteria."""
        query = select(self.model_class)

        for key, value in kwargs.items():
            if hasattr(self.model_class, key):
                column = getattr(self.model_class, key)
                query = query.where(column == value)

        result = self.session.execute(query)
        return result.scalar_one_or_none() is not None


class TenantAwareRepository(BaseRepository[ModelType]):
    """
    Repository with tenant isolation support.

    Automatically filters all operations by tenant_id.
    """

    def __init__(self, session: Session, model_class: Type[ModelType], tenant_id: str):
        super().__init__(session, model_class)
        self.tenant_id = tenant_id

        # Verify model has tenant_id field
        if not hasattr(model_class, "tenant_id"):
            raise ValueError(f"Model {model_class.__name__} must have tenant_id field")

    def _add_tenant_filter(self, query):
        """Add tenant filter to query."""
        return query.where(self.model_class.tenant_id == self.tenant_id)

    def create(self, **kwargs) -> ModelType:
        """Create a new record with tenant isolation."""
        kwargs["tenant_id"] = self.tenant_id
        return super().create(**kwargs)

    def get_by_id(self, id: str, include_deleted: bool = False) -> Optional[ModelType]:
        """Get a record by ID within tenant."""
        query = select(self.model_class).where(
            and_(
                self.model_class.id == id, self.model_class.tenant_id == self.tenant_id
            )
        )

        if not include_deleted and hasattr(self.model_class, "deleted_at"):
            query = query.where(self.model_class.deleted_at.is_(None))

        result = self.session.execute(query)
        return result.scalar_one_or_none()

    def get_all(
        self,
        include_deleted: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[ModelType]:
        """Get all records within tenant."""
        # Add tenant filter to existing filters
        tenant_filters = filters or {}
        tenant_filters["tenant_id"] = self.tenant_id

        return super().get_all(
            include_deleted=include_deleted,
            limit=limit,
            offset=offset,
            order_by=order_by,
            filters=tenant_filters,
        )

    def count(
        self,
        include_deleted: bool = False,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count records within tenant."""
        # Add tenant filter to existing filters
        tenant_filters = filters or {}
        tenant_filters["tenant_id"] = self.tenant_id

        return super().count(
            include_deleted=include_deleted,
            filters=tenant_filters,
        )

    def exists(self, **kwargs) -> bool:
        """Check if a record exists within tenant."""
        kwargs["tenant_id"] = self.tenant_id
        return super().exists(**kwargs)


class RepositoryManager:
    """
    Manager for repository instances.

    Provides centralized access to repositories with session management.
    """

    def __init__(self, session: Session):
        self.session = session
        self._repositories: Dict[Any, BaseRepository] = {}

    def get_repository(
        self,
        model_class: Type[ModelType],
        tenant_id: Optional[str] = None,
    ) -> Union[BaseRepository[ModelType], TenantAwareRepository[ModelType]]:
        """Get repository instance for a model."""
        cache_key = (model_class, tenant_id)

        if cache_key not in self._repositories:
            if tenant_id and hasattr(model_class, "tenant_id"):
                repository = TenantAwareRepository(self.session, model_class, tenant_id)
            else:
                repository = BaseRepository(self.session, model_class)

            self._repositories[cache_key] = repository

        return self._repositories[cache_key]

    def clear_cache(self):
        """Clear repository cache."""
        self._repositories.clear()


# Global repository manager instance
_repository_manager: Optional[RepositoryManager] = None


def get_repository_manager(session: Session) -> RepositoryManager:
    """Get repository manager instance."""
    global _repository_manager
    if _repository_manager is None or _repository_manager.session != session:
        _repository_manager = RepositoryManager(session)
    return _repository_manager


def get_repository(
    session: Session,
    model_class: Type[ModelType],
    tenant_id: Optional[str] = None,
) -> Union[BaseRepository[ModelType], TenantAwareRepository[ModelType]]:
    """Convenience function to get repository."""
    manager = get_repository_manager(session)
    return manager.get_repository(model_class, tenant_id)

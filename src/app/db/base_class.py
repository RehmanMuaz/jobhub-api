from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, declared_attr


class Base(DeclarativeBase):
    """Declarative base class that adds automatic table naming and reprs."""

    __abstract__ = True

    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[override]
        return cls.__name__.lower()

    def __repr__(self) -> str:
        attrs = [f"{key}={value!r}" for key, value in vars(self).items() if not key.startswith("_")]
        joined = ", ".join(sorted(attrs))
        return f"{self.__class__.__name__}({joined})"

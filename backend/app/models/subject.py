import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SubjectType(str, enum.Enum):
    MEMBER = "member"
    COMMUNITY_STAFF = "community_staff"
    PLATFORM_STAFF = "platform_staff"


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (
        UniqueConstraint("email", "subject_type", name="uq_email_subject_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    subject_type: Mapped[SubjectType] = mapped_column(
        Enum(SubjectType), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    mfa_enabled: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    credentials = relationship("Credential", back_populates="subject", lazy="selectin")
    sessions = relationship("Session", back_populates="subject", lazy="selectin")

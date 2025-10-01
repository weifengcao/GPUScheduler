import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.backend.core.database import Base


class GpuStatus(str, enum.Enum):
    PROVISIONING = "PROVISIONING"
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    DEPROVISIONING = "DEPROVISIONING"
    DEPROVISIONED = "DEPROVISIONED"
    ERROR = "ERROR"


class GpuHealthState(str, enum.Enum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class GPU(Base):
    __tablename__ = "gpus"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    instance_id = Column(String(255), nullable=True, index=True)
    instance_public_ip = Column(String(255), nullable=True)

    status = Column(Enum(GpuStatus), nullable=False, index=True, default=GpuStatus.PROVISIONING)
    health_state = Column(Enum(GpuHealthState), nullable=False, default=GpuHealthState.UNKNOWN)
    lease_expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="gpus")
    user = relationship("User", back_populates="gpus")
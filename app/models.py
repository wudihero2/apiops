from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    JSON,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class OpsLog(Base):
    __tablename__ = "ops_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ts = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    actor = Column(Text, nullable=True)
    source_ip = Column(Text, nullable=True)
    action = Column(Text, nullable=False)
    resource_kind = Column(Text, nullable=False)
    namespace = Column(Text, nullable=False)
    resource_name = Column(Text, nullable=False)
    request_body = Column(JSON, nullable=True)
    status = Column(Text, nullable=False)  # success / error
    error_message = Column(Text, nullable=True)


class OpsJob(Base):
    __tablename__ = "ops_job"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(Text, unique=True, nullable=False)
    type = Column(Text, nullable=False)  # e.g. 'pg-rebuild'
    status = Column(Text, nullable=False)  # pending / running / success / failed
    created_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True))
    params = Column(JSON, nullable=False)
    actor = Column(Text, nullable=True)
    source_ip = Column(Text, nullable=True)


class OpsJobStep(Base):
    __tablename__ = "ops_job_step"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    job_id = Column(Text, nullable=False)  # FK -> OpsJob.job_id
    name = Column(Text, nullable=False)
    step_order = Column(Integer, nullable=False)
    status = Column(Text, nullable=False)  # pending / running / success / failed
    detail = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))

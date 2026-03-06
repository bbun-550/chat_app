from sqlalchemy import Column, ForeignKey, Integer, Text, Float, CheckConstraint, Index
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Text, primary_key=True)
    title = Column(Text, nullable=False, default="New Chat")
    category = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_conversations_updated", updated_at.desc()),)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Text, primary_key=True)
    conversation_id = Column(Text, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    model = Column(Text, nullable=False, default="gemini-3-flash-preview")
    created_at = Column(Text, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')"),
        Index("idx_messages_conv_created", "conversation_id", "created_at"),
    )


class SystemPrompt(Base):
    __tablename__ = "system_prompts"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class Run(Base):
    __tablename__ = "runs"

    id = Column(Text, primary_key=True)
    message_id = Column(Text, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    provider = Column(Text, nullable=False)
    model = Column(Text, nullable=False)
    system_prompt_id = Column(Text, ForeignKey("system_prompts.id", ondelete="SET NULL"))
    system_prompt_content = Column(Text)
    params_json = Column(Text, nullable=False)
    latency_ms = Column(Integer, nullable=False)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    top_p = Column(Float)
    top_k = Column(Integer)
    candidate_count = Column(Integer)
    raw_json = Column(Text)
    created_at = Column(Text, nullable=False)

    __table_args__ = (Index("idx_runs_message", "message_id", "created_at"),)


class MessageMeta(Base):
    __tablename__ = "message_meta"

    message_id = Column(Text, ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True)
    task_type = Column(Text)
    quality_score = Column(Integer)
    tags = Column(Text)
    teacher_rationale = Column(Text)
    rating_source = Column(Text)
    is_rejected = Column(Integer, nullable=False, default=0)
    language = Column(Text)
    safety_flags = Column(Text)
    notes = Column(Text)

    __table_args__ = (CheckConstraint("quality_score BETWEEN 1 AND 5"),)


class KDExample(Base):
    __tablename__ = "kd_examples"

    id = Column(Text, primary_key=True)
    conversation_id = Column(Text, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    user_message_id = Column(Text, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    assistant_message_id = Column(Text, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True)
    system_prompt = Column(Text)
    prompt_text = Column(Text, nullable=False)
    teacher_rationale = Column(Text)
    answer_text = Column(Text, nullable=False)
    category = Column(Text)
    quality_score = Column(Integer)
    task_type = Column(Text)
    is_rejected = Column(Integer, nullable=False, default=0)
    provider = Column(Text)
    model = Column(Text)
    run_id = Column(Text, ForeignKey("runs.id", ondelete="SET NULL"))
    dataset_version = Column(Text, nullable=False, default="v1")
    created_at = Column(Text, nullable=False)

    __table_args__ = (
        Index("idx_kd_examples_category_quality", "category", "quality_score", "is_rejected"),
    )


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id = Column(Text, primary_key=True)
    conversation_id = Column(Text, ForeignKey("conversations.id", ondelete="SET NULL"))
    summary_text = Column(Text, nullable=False)
    fact_count = Column(Integer, nullable=False, default=0)
    created_at = Column(Text, nullable=False)

    __table_args__ = (Index("idx_daily_summaries_created", created_at.desc()),)


class VectorMemory(Base):
    __tablename__ = "vector_memories"

    id = Column(Text, primary_key=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384), nullable=False)
    memory_type = Column(Text, nullable=False, default="fact")
    source_conversation_id = Column(Text, ForeignKey("conversations.id", ondelete="SET NULL"))
    created_at = Column(Text, nullable=False)

    __table_args__ = (Index("idx_vector_memories_type", "memory_type", created_at.desc()),)


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Text, primary_key=True)
    plan_id = Column(Text, nullable=False, unique=True)
    conversation_id = Column(Text, ForeignKey("conversations.id", ondelete="SET NULL"))
    intent = Column(Text, nullable=False)
    plan_json = Column(Text, nullable=False)
    overall_risk = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="pending")
    provider = Column(Text)
    model = Column(Text)
    created_at = Column(Text, nullable=False)
    completed_at = Column(Text)

    steps = relationship("AgentStep", back_populates="agent_log", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("overall_risk IN ('LOW', 'MEDIUM', 'HIGH')"),
        CheckConstraint("status IN ('pending', 'executing', 'completed', 'failed')"),
        Index("idx_agent_logs_conv", "conversation_id"),
        Index("idx_agent_logs_plan", "plan_id"),
    )


class AgentStep(Base):
    __tablename__ = "agent_steps"

    id = Column(Text, primary_key=True)
    agent_log_id = Column(Text, ForeignKey("agent_logs.id", ondelete="CASCADE"), nullable=False)
    step_index = Column(Integer, nullable=False)
    tool_name = Column(Text, nullable=False)
    args_json = Column(Text, nullable=False)
    risk_level = Column(Text, nullable=False)
    approval = Column(Text, nullable=False, default="pending")
    description = Column(Text, nullable=False, default="")
    success = Column(Integer)
    output_json = Column(Text)
    error = Column(Text)
    duration_ms = Column(Integer, default=0)
    created_at = Column(Text, nullable=False)

    agent_log = relationship("AgentLog", back_populates="steps")

    __table_args__ = (
        CheckConstraint("risk_level IN ('LOW', 'MEDIUM', 'HIGH')"),
        CheckConstraint("approval IN ('auto_approved', 'pending', 'approved', 'rejected')"),
        Index("idx_agent_steps_log", "agent_log_id", "step_index"),
    )


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    task_type = Column(Text, nullable=False)
    cron_expression = Column(Text, nullable=False)
    params_json = Column(Text, nullable=False, default="{}")
    enabled = Column(Integer, nullable=False, default=1)
    last_run_at = Column(Text)
    next_run_at = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint("task_type IN ('market_analysis', 'research_report', 'daily_summary')"),
        CheckConstraint("enabled IN (0, 1)"),
        Index("idx_jobs_enabled_next", "enabled", "next_run_at"),
    )


class Report(Base):
    __tablename__ = "reports"

    id = Column(Text, primary_key=True)
    job_id = Column(Text, ForeignKey("jobs.id", ondelete="SET NULL"))
    report_type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text)
    params_json = Column(Text, nullable=False, default="{}")
    provider = Column(Text)
    model = Column(Text)
    latency_ms = Column(Integer)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    status = Column(Text, nullable=False, default="completed")
    created_at = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "report_type IN ('market_analysis', 'research_report', 'daily_summary')"
        ),
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')"),
        Index("idx_reports_type_created", "report_type", created_at.desc()),
        Index("idx_reports_job", "job_id"),
    )


class Event(Base):
    __tablename__ = "events"

    id = Column(Text, primary_key=True)
    event_type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text)
    ref_id = Column(Text)
    ref_type = Column(Text)
    is_read = Column(Integer, nullable=False, default=0)
    created_at = Column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('job_started', 'job_completed', 'job_failed', 'report_ready')"
        ),
        CheckConstraint("is_read IN (0, 1)"),
        Index("idx_events_unread", "is_read", created_at.desc()),
    )

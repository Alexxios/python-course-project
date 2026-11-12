"""Run migrations using the connection supplied by the application CLI."""

from alembic import context

from app.models import Base

context.configure(
    connection=context.config.attributes["connection"],
    target_metadata=Base.metadata,
    compare_type=True,
)
with context.begin_transaction():
    context.run_migrations()

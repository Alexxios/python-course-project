"""Use the transaction supplied by the application's migration command."""

from alembic import context

from app.students.models import Base

context.configure(
    connection=context.config.attributes["connection"],
    target_metadata=Base.metadata,
    compare_type=True,
)
with context.begin_transaction():
    context.run_migrations()

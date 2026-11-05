from alembic import context
from app.database import engine, Base
import app.models

if context.is_offline_mode():
    context.configure(url=str(engine.url), target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    def run(connection):
        context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
    supplied = context.config.attributes.get('connection')
    if supplied is not None:
        run(supplied)
    else:
        with engine.connect() as connection:
            run(connection)

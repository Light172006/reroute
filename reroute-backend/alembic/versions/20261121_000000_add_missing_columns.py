"""Add missing columns and update timestamps

Revision ID: 20261121_000000_add_missing_columns
Revises: 001_initial_schema
Create Date: 2026-11-21 06:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '20261121_000000_add_missing_columns'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure alembic_version can store revisions up to 64 chars
    op.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(64)")

    # Use IF NOT EXISTS for PostgreSQL DDL so migration is idempotent
    op.execute("ALTER TABLE places ADD COLUMN IF NOT EXISTS description TEXT")
    op.execute("ALTER TABLE places ADD COLUMN IF NOT EXISTS image_url TEXT")
    op.execute("ALTER TABLE places ADD COLUMN IF NOT EXISTS raw JSONB")

    # Add columns to trips
    # First create enum type if not exists
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE trip_status AS ENUM ('draft', 'generating', 'planned', 'active', 'completed', 'archived');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("ALTER TABLE trips ADD COLUMN IF NOT EXISTS status trip_status NOT NULL DEFAULT 'draft'")
    op.execute("ALTER TABLE trips ADD COLUMN IF NOT EXISTS notes TEXT")
    op.execute("ALTER TABLE trips ADD COLUMN IF NOT EXISTS budget_per_day_cap NUMERIC(12, 2)")
    op.execute("ALTER TABLE trips ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()")

    # Add columns to itinerary_versions
    op.execute("ALTER TABLE itinerary_versions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()")

    # Add columns to itinerary_items
    op.execute("ALTER TABLE itinerary_items ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()")

    # Add columns to expenses
    op.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS description TEXT")
    op.execute("ALTER TABLE expenses ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now()")

    # Add columns to agent_runs
    op.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS trigger TEXT NOT NULL DEFAULT 'user'")
    op.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS idempotency_key TEXT")
    op.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS output JSONB")
    op.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS error TEXT")
    op.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS model_used TEXT")
    op.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS tokens_in INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS tokens_out INTEGER NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS finished_at TIMESTAMP WITH TIME ZONE")

    # Add columns to disruption_events
    op.execute("ALTER TABLE disruption_events ADD COLUMN IF NOT EXISTS day_index INTEGER")
    op.execute("ALTER TABLE disruption_events ADD COLUMN IF NOT EXISTS source TEXT")
    op.execute("ALTER TABLE disruption_events ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT now()")

    # Create triggers for updated_at columns
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("DROP TRIGGER IF EXISTS trg_trips_updated ON trips")
    op.execute("CREATE TRIGGER trg_trips_updated BEFORE UPDATE ON trips FOR EACH ROW EXECUTE FUNCTION set_updated_at()")
    op.execute("DROP TRIGGER IF EXISTS trg_itinerary_versions_updated ON itinerary_versions")
    op.execute("CREATE TRIGGER trg_itinerary_versions_updated BEFORE UPDATE ON itinerary_versions FOR EACH ROW EXECUTE FUNCTION set_updated_at()")
    op.execute("DROP TRIGGER IF EXISTS trg_itinerary_items_updated ON itinerary_items")
    op.execute("CREATE TRIGGER trg_itinerary_items_updated BEFORE UPDATE ON itinerary_items FOR EACH ROW EXECUTE FUNCTION set_updated_at()")


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trg_itinerary_items_updated ON itinerary_items")
    op.execute("DROP TRIGGER IF EXISTS trg_itinerary_versions_updated ON itinerary_versions")
    op.execute("DROP TRIGGER IF EXISTS trg_trips_updated ON trips")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    # Drop columns from agent_runs
    op.drop_column('agent_runs', 'finished_at')
    op.drop_column('agent_runs', 'started_at')
    op.drop_column('agent_runs', 'tokens_out')
    op.drop_column('agent_runs', 'tokens_in')
    op.drop_column('agent_runs', 'model_used')
    op.drop_column('agent_runs', 'output')
    op.drop_column('agent_runs', 'error')
    op.drop_column('agent_runs', 'idempotency_key')
    op.drop_column('agent_runs', 'trigger')

    # Drop columns from disruption_events
    op.drop_column('disruption_events', 'created_at')
    op.drop_column('disruption_events', 'source')
    op.drop_column('disruption_events', 'day_index')

    # Drop columns from expenses
    op.drop_column('expenses', 'created_at')
    op.drop_column('expenses', 'description')

    # Drop columns from itinerary_items
    op.drop_column('itinerary_items', 'updated_at')

    # Drop columns from itinerary_versions
    op.drop_column('itinerary_versions', 'updated_at')

    # Drop columns from trips
    op.drop_column('trips', 'updated_at')
    op.drop_column('trips', 'budget_per_day_cap')
    op.drop_column('trips', 'notes')
    op.drop_column('trips', 'status')

    # Drop columns from places
    op.drop_column('places', 'raw')
    op.drop_column('places', 'image_url')
    op.drop_column('places', 'description')
"""Initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-11-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


# Define enum types
trip_status = ENUM('draft', 'generating', 'planned', 'active', 'completed', 'archived', name='trip_status', create_type=True)
pace_type = ENUM('relaxed', 'balanced', 'packed', name='pace_type', create_type=True)
item_category = ENUM('sightseeing', 'food', 'culture', 'nature', 'nightlife', 'shopping', 'adventure', 'transport', 'stay', 'other', name='item_category', create_type=True)
setting_type = ENUM('indoor', 'outdoor', 'mixed', name='setting_type', create_type=True)
transport_mode = ENUM('walk', 'taxi', 'bus', 'train', 'metro', 'bike', 'car', name='transport_mode', create_type=True)
disruption_type = ENUM('weather', 'closure', 'hours_conflict', 'delay', 'budget_overrun', 'user_request', name='disruption_type', create_type=True)
severity_type = ENUM('low', 'medium', 'high', name='severity_type', create_type=True)
proposal_status = ENUM('pending', 'approved', 'rejected', 'expired', 'superseded', name='proposal_status', create_type=True)
run_type = ENUM('plan', 'replan', 'chat', name='run_type', create_type=True)
run_status = ENUM('queued', 'running', 'awaiting_user', 'completed', 'failed', 'cancelled', name='run_status', create_type=True)
expense_category = ENUM('stay', 'food', 'transport', 'activities', 'shopping', 'other', name='expense_category', create_type=True)


def upgrade() -> None:
    # Create pgcrypto extension for gen_random_uuid
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "citext"')

    # Create tables
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.Text(), nullable=False, unique=True),
        sa.Column('password_hash', sa.Text(), nullable=True),
        sa.Column('display_name', sa.Text(), nullable=False),
        sa.Column('google_sub', sa.Text(), nullable=True, unique=True),
        sa.Column('home_currency', sa.CHAR(3), nullable=False, server_default='INR'),
        sa.Column('units', sa.Text(), nullable=False, server_default='metric'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema=None
    )
    op.execute('ALTER TABLE users ALTER COLUMN email TYPE CITEXT USING email::citext')

    op.create_table(
        'refresh_tokens',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False, unique=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_refresh_tokens_user', 'refresh_tokens', ['user_id'])

    op.create_table(
        'places',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('external_id', sa.Text(), nullable=True),
        sa.Column('source', sa.Text(), nullable=False, server_default='seed'),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('city', sa.Text(), nullable=False),
        sa.Column('country', sa.Text(), nullable=False, server_default='IN'),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('category', item_category, nullable=False),
        sa.Column('setting', setting_type, nullable=False, server_default='mixed'),
        sa.Column('avg_cost', sa.Numeric(12, 2), nullable=True),
        sa.Column('currency', sa.CHAR(3), nullable=False, server_default='INR'),
        sa.Column('avg_duration_min', sa.Integer(), nullable=True),
        sa.Column('opening_hours', JSONB, nullable=True),
        sa.Column('hours_confidence', sa.Text(), nullable=False, server_default='unknown'),
        sa.Column('rating', sa.Numeric(3, 2), nullable=True),
        sa.Column('tags', sa.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('image_url', sa.Text(), nullable=True),
        sa.Column('raw', JSONB, nullable=True),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('source', 'external_id', name='uq_places_source_external'),
    )
    op.create_index('idx_places_city_cat', 'places', ['city', 'category'])
    op.execute('CREATE INDEX idx_places_tags ON places USING GIN (tags)')

    op.create_table(
        'trips',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('destination', sa.Text(), nullable=False),
        sa.Column('dest_lat', sa.Float(), nullable=True),
        sa.Column('dest_lng', sa.Float(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('group_size', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('budget_total', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('budget_per_day_cap', sa.Numeric(12, 2), nullable=True),
        sa.Column('currency', sa.CHAR(3), nullable=False, server_default='INR'),
        sa.Column('pace', pace_type, nullable=False, server_default='balanced'),
        sa.Column('vibe_tags', sa.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', trip_status, nullable=False, server_default='draft'),
        sa.Column('current_version_id', UUID(as_uuid=True), nullable=True),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('end_date >= start_date', name='ck_trips_dates'),
        sa.CheckConstraint('group_size > 0', name='ck_trips_group_size'),
        sa.CheckConstraint('budget_total >= 0', name='ck_trips_budget_total'),
    )
    op.create_index('idx_trips_user', 'trips', ['user_id', 'status'])
    op.create_index('idx_trips_dates', 'trips', ['start_date', 'end_date'])

    op.create_table(
        'itinerary_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('trip_id', UUID(as_uuid=True), sa.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False),
        sa.Column('parent_version_id', UUID(as_uuid=True), sa.ForeignKey('itinerary_versions.id'), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_by', sa.Text(), nullable=False),
        sa.Column('proposal_id', UUID(as_uuid=True), nullable=True),
        sa.Column('run_id', UUID(as_uuid=True), nullable=True),
        sa.Column('total_cost', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('trip_id', 'version_no', name='uq_versions_trip_version'),
    )
    op.create_index('idx_versions_trip', 'itinerary_versions', ['trip_id', 'version_no'])

    op.create_table(
        'itinerary_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('version_id', UUID(as_uuid=True), sa.ForeignKey('itinerary_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stable_key', UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('day_index', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('place_id', UUID(as_uuid=True), sa.ForeignKey('places.id'), nullable=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('category', item_category, nullable=False),
        sa.Column('setting', setting_type, nullable=False, server_default='mixed'),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('est_cost', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('lat', sa.Float(), nullable=True),
        sa.Column('lng', sa.Float(), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('travel_mode', transport_mode, nullable=True),
        sa.Column('travel_minutes', sa.Integer(), nullable=True),
        sa.Column('travel_distance_m', sa.Integer(), nullable=True),
        sa.Column('flags', sa.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('day_index >= 1', name='ck_items_day_index'),
        sa.CheckConstraint('position >= 0', name='ck_items_position'),
        sa.UniqueConstraint('version_id', 'day_index', 'position', name='uq_items_version_day_pos'),
        sa.UniqueConstraint('stable_key', name='uq_items_stable_key'),
    )
    op.create_index('idx_items_version_day', 'itinerary_items', ['version_id', 'day_index', 'position'])
    op.create_index('idx_items_stable_key', 'itinerary_items', ['stable_key'], if_not_exists=True)
    op.create_index('idx_items_stable_key', 'itinerary_items', ['stable_key'], if_not_exists=True)

    op.create_table(
        'agent_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('trip_id', UUID(as_uuid=True), sa.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', run_type, nullable=False),
        sa.Column('status', run_status, nullable=False, server_default='queued'),
        sa.Column('trigger', sa.Text(), nullable=False, server_default='user'),
        sa.Column('idempotency_key', sa.Text(), nullable=True),
        sa.Column('input', JSONB, nullable=False, server_default='{}'),
        sa.Column('output', JSONB, nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('model_used', sa.Text(), nullable=True),
        sa.Column('tokens_in', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_out', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_runs_trip', 'agent_runs', ['trip_id', 'created_at'])
    op.execute('CREATE UNIQUE INDEX uq_runs_idem ON agent_runs(trip_id, idempotency_key) WHERE idempotency_key IS NOT NULL')
    op.execute("CREATE UNIQUE INDEX uq_runs_one_active ON agent_runs(trip_id) WHERE status IN ('queued','running','awaiting_user')")

    op.create_table(
        'agent_run_events',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('agent_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('type', sa.Text(), nullable=False),
        sa.Column('node', sa.Text(), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=True),
        sa.Column('payload', JSONB, nullable=False, server_default='{}'),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('run_id', 'seq', name='uq_run_events_run_seq'),
    )
    op.create_index('idx_run_events_run', 'agent_run_events', ['run_id', 'seq'])

    op.create_table(
        'disruption_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('trip_id', UUID(as_uuid=True), sa.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('agent_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('type', disruption_type, nullable=False),
        sa.Column('severity', severity_type, nullable=False, server_default='medium'),
        sa.Column('day_index', sa.Integer(), nullable=True),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('affected_stable_keys', sa.ARRAY(UUID(as_uuid=True)), nullable=False, server_default='{}'),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('data', JSONB, nullable=False, server_default='{}'),
        sa.Column('fingerprint', sa.Text(), nullable=False),
        sa.Column('is_simulated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.UniqueConstraint('trip_id', 'fingerprint', name='uq_disruptions_trip_fingerprint'),
    )
    op.create_index('idx_disruptions_trip', 'disruption_events', ['trip_id', 'resolved_at'])

    op.create_table(
        'replan_proposals',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('trip_id', UUID(as_uuid=True), sa.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('agent_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('base_version_id', UUID(as_uuid=True), sa.ForeignKey('itinerary_versions.id'), nullable=False),
        sa.Column('status', proposal_status, nullable=False, server_default='pending'),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('disruption_ids', sa.ARRAY(UUID(as_uuid=True)), nullable=False, server_default='{}'),
        sa.Column('diff', JSONB, nullable=False),
        sa.Column('proposed_items', JSONB, nullable=False),
        sa.Column('cost_delta', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('time_delta_min', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('items_changed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('alternatives_of', UUID(as_uuid=True), sa.ForeignKey('replan_proposals.id'), nullable=True),
        sa.Column('resulting_version_id', UUID(as_uuid=True), sa.ForeignKey('itinerary_versions.id'), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decision_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_proposals_trip_status', 'replan_proposals', ['trip_id', 'status'])

    op.create_table(
        'expenses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('trip_id', UUID(as_uuid=True), sa.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('item_stable_key', UUID(as_uuid=True), sa.ForeignKey('itinerary_items.stable_key'), nullable=True),
        sa.Column('category', expense_category, nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.CHAR(3), nullable=False, server_default='INR'),
        sa.Column('amount_in_trip_currency', sa.Numeric(12, 2), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('spent_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('amount >= 0', name='ck_expenses_amount'),
    )
    op.create_index('idx_expenses_trip', 'expenses', ['trip_id', 'spent_at'])

    op.create_table(
        'chat_messages',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('trip_id', UUID(as_uuid=True), sa.ForeignKey('trips.id', ondelete='CASCADE'), nullable=False),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('agent_runs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system')", name='ck_chat_messages_role'),
    )
    op.create_index('idx_chat_trip', 'chat_messages', ['trip_id', 'created_at'])

    op.create_table(
        'api_cache',
        sa.Column('cache_key', sa.Text(), primary_key=True),
        sa.Column('provider', sa.Text(), nullable=False),
        sa.Column('response', JSONB, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_api_cache_expiry', 'api_cache', ['expires_at'])

    # Add foreign keys with DEFERRABLE INITIALLY DEFERRED for circular references
    op.execute("""
        ALTER TABLE trips
        ADD CONSTRAINT fk_trips_current_version
        FOREIGN KEY (current_version_id) REFERENCES itinerary_versions(id)
        DEFERRABLE INITIALLY DEFERRED
    """)

    op.execute("""
        ALTER TABLE itinerary_versions
        ADD CONSTRAINT fk_versions_proposal
        FOREIGN KEY (proposal_id) REFERENCES replan_proposals(id)
        ON DELETE SET NULL
    """)

    op.execute("""
        ALTER TABLE itinerary_versions
        ADD CONSTRAINT fk_versions_run
        FOREIGN KEY (run_id) REFERENCES agent_runs(id)
        ON DELETE SET NULL
    """)

    # Create updated_at trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at()")
    op.execute("CREATE TRIGGER trg_trips_updated BEFORE UPDATE ON trips FOR EACH ROW EXECUTE FUNCTION set_updated_at()")


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trg_trips_updated ON trips")
    op.execute("DROP TRIGGER IF EXISTS trg_users_updated ON users")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")

    # Drop foreign keys
    op.execute("ALTER TABLE itinerary_versions DROP CONSTRAINT IF EXISTS fk_versions_run")
    op.execute("ALTER TABLE itinerary_versions DROP CONSTRAINT IF EXISTS fk_versions_proposal")
    op.execute("ALTER TABLE trips DROP CONSTRAINT IF EXISTS fk_trips_current_version")

    # Drop tables in reverse order
    op.drop_table('api_cache')
    op.drop_table('chat_messages')
    op.drop_table('expenses')
    op.drop_table('replan_proposals')
    op.drop_table('disruption_events')
    op.drop_table('agent_run_events')
    op.drop_table('agent_runs')
    op.drop_table('itinerary_items')
    op.drop_table('itinerary_versions')
    op.drop_table('trips')
    op.drop_table('places')
    op.drop_table('refresh_tokens')
    op.drop_table('users')

    # Drop enum types
    trip_status.drop(op.get_bind(), checkfirst=True)
    pace_type.drop(op.get_bind(), checkfirst=True)
    item_category.drop(op.get_bind(), checkfirst=True)
    setting_type.drop(op.get_bind(), checkfirst=True)
    transport_mode.drop(op.get_bind(), checkfirst=True)
    disruption_type.drop(op.get_bind(), checkfirst=True)
    severity_type.drop(op.get_bind(), checkfirst=True)
    proposal_status.drop(op.get_bind(), checkfirst=True)
    run_type.drop(op.get_bind(), checkfirst=True)
    run_status.drop(op.get_bind(), checkfirst=True)
    expense_category.drop(op.get_bind(), checkfirst=True)

    # Drop extensions
    op.execute('DROP EXTENSION IF EXISTS citext')
    op.execute('DROP EXTENSION IF EXISTS pgcrypto')
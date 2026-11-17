"""Initial PostgreSQL schema migration for AgriAI

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('salt', sa.String(length=64), server_default='bcrypt', nullable=False),
        sa.Column('role', sa.String(length=50), server_default='farmer', nullable=False),
        sa.Column('created_at', sa.String(length=50), nullable=False),
        sa.Column('last_login', sa.String(length=50), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('preferred_crop', sa.String(length=100), nullable=True),
        sa.Column('avatar_path', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='Active', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=False)
    op.create_index('idx_users_role_status', 'users', ['role', 'status'], unique=False)

    # 2. prediction_history
    op.create_table(
        'prediction_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('district', sa.String(length=100), nullable=True),
        sa.Column('crop', sa.String(length=100), nullable=True),
        sa.Column('crop_category', sa.String(length=100), nullable=True),
        sa.Column('sowing_season', sa.String(length=50), nullable=True),
        sa.Column('weather_season', sa.String(length=50), nullable=True),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('humidity', sa.Float(), nullable=True),
        sa.Column('rainfall', sa.Float(), nullable=True),
        sa.Column('thi', sa.Float(), nullable=True),
        sa.Column('rf_hum_ratio', sa.Float(), nullable=True),
        sa.Column('predicted_pest', sa.String(length=100), nullable=True),
        sa.Column('pest_prob', sa.Float(), nullable=True),
        sa.Column('predicted_risk', sa.String(length=50), nullable=True),
        sa.Column('risk_prob', sa.Float(), nullable=True),
        sa.Column('model_notes', sa.Text(), nullable=True),
        sa.Column('pesticide', sa.Text(), nullable=True),
        sa.Column('dosage', sa.Text(), nullable=True),
        sa.Column('organic_control', sa.Text(), nullable=True),
        sa.Column('safety_notes', sa.Text(), nullable=True),
        sa.Column('prevention_methods', sa.Text(), nullable=True),
        sa.Column('pdf_path', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_preds_user_id', 'prediction_history', ['user_id'], unique=False)
    op.create_index('idx_preds_created_at', 'prediction_history', ['created_at'], unique=False)
    op.create_index('idx_preds_crop', 'prediction_history', ['crop'], unique=False)
    op.create_index('idx_preds_state_district', 'prediction_history', ['state', 'district'], unique=False)

    # 3. contact_queries
    op.create_table(
        'contact_queries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('created_date', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='Pending', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_contact_status', 'contact_queries', ['status'], unique=False)

    # 4. user_preferences
    op.create_table(
        'user_preferences',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('dark_mode', sa.Integer(), server_default='0', nullable=False),
        sa.Column('language', sa.String(length=50), server_default='English', nullable=False),
        sa.Column('notifications', sa.Integer(), server_default='1', nullable=False),
        sa.Column('theme_mode', sa.String(length=50), server_default='auto', nullable=False),
        sa.Column('notify_prediction', sa.Integer(), server_default='1', nullable=False),
        sa.Column('notify_weather', sa.Integer(), server_default='1', nullable=False),
        sa.Column('notify_system', sa.Integer(), server_default='1', nullable=False),
        sa.Column('privacy_history', sa.Integer(), server_default='1', nullable=False),
        sa.Column('privacy_email', sa.Integer(), server_default='1', nullable=False),
        sa.Column('privacy_profile', sa.Integer(), server_default='1', nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )

    # 5. account_activity
    op.create_table(
        'account_activity',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('activity_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('icon', sa.String(length=10), server_default='⚡', nullable=False),
        sa.Column('created_at', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_activity_user_id', 'account_activity', ['user_id'], unique=False)

    # 6. user_sessions
    op.create_table(
        'user_sessions',
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.String(length=50), nullable=False),
        sa.Column('expires_at', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('token')
    )
    op.create_index('idx_sessions_token', 'user_sessions', ['token'], unique=False)

    # 7. password_reset_tokens
    op.create_table(
        'password_reset_tokens',
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.String(length=50), nullable=False),
        sa.Column('used', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('token')
    )
    op.create_index('idx_reset_token', 'password_reset_tokens', ['token'], unique=False)


def downgrade() -> None:
    op.drop_table('password_reset_tokens')
    op.drop_table('user_sessions')
    op.drop_table('account_activity')
    op.drop_table('user_preferences')
    op.drop_table('contact_queries')
    op.drop_table('prediction_history')
    op.drop_table('users')

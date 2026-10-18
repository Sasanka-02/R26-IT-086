"""therapist controls and evidence

Component 4 features carried over from the stand-alone prototype:
therapist goals, clinical notes (shared / private), homework due dates, 1-5 attempt ratings,
plan reviews, the System Usability Scale survey, the differential-privacy budget ledger,
plus two patient columns: when therapist notes were last read and the calibrated DAF delay.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-18 12:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.add_column(sa.Column('notes_read_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('daf_delay_ms', sa.Integer(), nullable=True))

    op.create_table('therapy_goals',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.String(length=16), nullable=False),
    sa.Column('metric', sa.String(length=40), nullable=False),
    sa.Column('target', sa.Float(), nullable=False),
    sa.Column('created_by_user_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_therapy_goals_patient_id_patients'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_therapy_goals_created_by_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_therapy_goals'))
    )
    with op.batch_alter_table('therapy_goals', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_therapy_goals_patient_id'), ['patient_id'], unique=False)

    op.create_table('therapy_notes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.String(length=16), nullable=False),
    sa.Column('author_user_id', sa.Integer(), nullable=True),
    sa.Column('author_name', sa.String(length=120), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('shared', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_therapy_notes_patient_id_patients'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['author_user_id'], ['users.id'], name=op.f('fk_therapy_notes_author_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_therapy_notes'))
    )
    with op.batch_alter_table('therapy_notes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_therapy_notes_patient_id'), ['patient_id'], unique=False)

    op.create_table('therapy_homework',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.String(length=16), nullable=False),
    sa.Column('exercise_id', sa.String(length=60), nullable=False),
    sa.Column('due', sa.Date(), nullable=True),
    sa.Column('times', sa.Integer(), nullable=False),
    sa.Column('assigned_by_user_id', sa.Integer(), nullable=True),
    sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('times BETWEEN 1 AND 20', name=op.f('ck_therapy_homework_times_range')),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_therapy_homework_patient_id_patients'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['assigned_by_user_id'], ['users.id'], name=op.f('fk_therapy_homework_assigned_by_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_therapy_homework'))
    )
    with op.batch_alter_table('therapy_homework', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_therapy_homework_patient_id'), ['patient_id'], unique=False)
        batch_op.create_index('ix_therapy_homework_patient_exercise', ['patient_id', 'exercise_id'], unique=True)

    op.create_table('therapy_attempt_ratings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('attempt_id', sa.Integer(), nullable=False),
    sa.Column('rater_user_id', sa.Integer(), nullable=False),
    sa.Column('rating', sa.Integer(), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('rating BETWEEN 1 AND 5', name=op.f('ck_therapy_attempt_ratings_rating_range')),
    sa.ForeignKeyConstraint(['attempt_id'], ['therapy_attempts.id'], name=op.f('fk_therapy_attempt_ratings_attempt_id_therapy_attempts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['rater_user_id'], ['users.id'], name=op.f('fk_therapy_attempt_ratings_rater_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_therapy_attempt_ratings'))
    )
    with op.batch_alter_table('therapy_attempt_ratings', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_therapy_attempt_ratings_attempt_id'), ['attempt_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_therapy_attempt_ratings_rater_user_id'), ['rater_user_id'], unique=False)
        batch_op.create_index('ix_therapy_attempt_ratings_attempt_rater', ['attempt_id', 'rater_user_id'], unique=True)

    op.create_table('therapy_plan_reviews',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('patient_id', sa.String(length=16), nullable=False),
    sa.Column('reviewer_user_id', sa.Integer(), nullable=True),
    sa.Column('verdict', sa.String(length=20), nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('plan_json', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_therapy_plan_reviews_patient_id_patients'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reviewer_user_id'], ['users.id'], name=op.f('fk_therapy_plan_reviews_reviewer_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_therapy_plan_reviews'))
    )
    with op.batch_alter_table('therapy_plan_reviews', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_therapy_plan_reviews_patient_id'), ['patient_id'], unique=False)

    op.create_table('usability_surveys',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('answers', sa.JSON(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('comment', sa.Text(), nullable=True),
    sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_usability_surveys_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_usability_surveys')),
    sa.UniqueConstraint('user_id', name=op.f('uq_usability_surveys_user_id'))
    )

    op.create_table('privacy_ledger',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ledger_id', sa.String(length=40), nullable=False),
    sa.Column('release_key', sa.String(length=80), nullable=False),
    sa.Column('epsilon', sa.Float(), nullable=False),
    sa.Column('created_by_user_id', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], name=op.f('fk_privacy_ledger_created_by_user_id_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_privacy_ledger')),
    sa.UniqueConstraint('release_key', name=op.f('uq_privacy_ledger_release_key'))
    )
    with op.batch_alter_table('privacy_ledger', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_privacy_ledger_ledger_id'), ['ledger_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('privacy_ledger', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_privacy_ledger_ledger_id'))
    op.drop_table('privacy_ledger')
    op.drop_table('usability_surveys')
    with op.batch_alter_table('therapy_plan_reviews', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_therapy_plan_reviews_patient_id'))
    op.drop_table('therapy_plan_reviews')
    with op.batch_alter_table('therapy_attempt_ratings', schema=None) as batch_op:
        batch_op.drop_index('ix_therapy_attempt_ratings_attempt_rater')
        batch_op.drop_index(batch_op.f('ix_therapy_attempt_ratings_rater_user_id'))
        batch_op.drop_index(batch_op.f('ix_therapy_attempt_ratings_attempt_id'))
    op.drop_table('therapy_attempt_ratings')
    with op.batch_alter_table('therapy_homework', schema=None) as batch_op:
        batch_op.drop_index('ix_therapy_homework_patient_exercise')
        batch_op.drop_index(batch_op.f('ix_therapy_homework_patient_id'))
    op.drop_table('therapy_homework')
    with op.batch_alter_table('therapy_notes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_therapy_notes_patient_id'))
    op.drop_table('therapy_notes')
    with op.batch_alter_table('therapy_goals', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_therapy_goals_patient_id'))
    op.drop_table('therapy_goals')
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.drop_column('daf_delay_ms')
        batch_op.drop_column('notes_read_at')

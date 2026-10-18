"""patient age brackets

Age-bracketed therapy: patients store the age they entered (date of birth becomes optional),
the clinical age bracket (1–8), a therapist's bracket override, therapist-assigned exercises
and the time a parent / guardian agreed to an under-18 account. Existing rows keep their date
of birth; their age and bracket are filled in from it.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-17 12:00:00

"""
from datetime import date
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Frozen copy of the bracket table at this revision (migrations must not import app code).
_BRACKET_MIN_AGES = [(21, 8), (18, 7), (16, 6), (14, 5), (12, 4), (10, 3), (8, 2), (6, 1)]


def _age(dob: date, today: date) -> int:
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _bracket(age: int) -> int | None:
    if not 6 <= age <= 100:
        return None
    return next(b for lo, b in _BRACKET_MIN_AGES if age >= lo)


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.alter_column('date_of_birth', existing_type=sa.Date(), nullable=True)
        batch_op.add_column(sa.Column('age', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('age_bracket', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('age_bracket_override', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('assigned_exercises', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('guardian_consent_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_check_constraint(op.f('ck_patients_age_range'), 'age IS NULL OR age BETWEEN 6 AND 100')
        batch_op.create_check_constraint(op.f('ck_patients_age_bracket_range'), 'age_bracket IS NULL OR age_bracket BETWEEN 1 AND 8')
        batch_op.create_check_constraint(op.f('ck_patients_age_bracket_override_range'),
                                         'age_bracket_override IS NULL OR age_bracket_override BETWEEN 1 AND 8')

    # backfill age + bracket from the date of birth of existing patients
    bind = op.get_bind()
    patients = sa.table('patients', sa.column('id', sa.String), sa.column('date_of_birth', sa.Date),
                        sa.column('age', sa.Integer), sa.column('age_bracket', sa.Integer))
    today = date.today()
    for pid, dob in bind.execute(sa.select(patients.c.id, patients.c.date_of_birth)).all():
        if dob is None:
            continue
        if isinstance(dob, str):  # SQLite without type detection
            dob = date.fromisoformat(dob)
        age = _age(dob, today)
        if 6 <= age <= 100:
            bind.execute(patients.update().where(patients.c.id == pid).values(age=age, age_bracket=_bracket(age)))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('patients', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_patients_age_bracket_override_range'), type_='check')
        batch_op.drop_constraint(op.f('ck_patients_age_bracket_range'), type_='check')
        batch_op.drop_constraint(op.f('ck_patients_age_range'), type_='check')
        batch_op.drop_column('guardian_consent_at')
        batch_op.drop_column('assigned_exercises')
        batch_op.drop_column('age_bracket_override')
        batch_op.drop_column('age_bracket')
        batch_op.drop_column('age')
        batch_op.alter_column('date_of_birth', existing_type=sa.Date(), nullable=False)

"""reorder categories columns to match model (parent_id after id)

Revision ID: 480bb64f8c73
Revises: 9e4bc29be11a
Create Date: 2026-09-06 20:51:07.643126

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '480bb64f8c73'
down_revision: Union[str, Sequence[str], None] = '9e4bc29be11a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Rename existing categories table
    op.execute("ALTER TABLE categories RENAME TO categories_old")

    # 2. Rename sequence so the new table can use categories_id_seq
    op.execute("ALTER SEQUENCE categories_id_seq RENAME TO categories_old_id_seq")

    # 3. Rename existing indexes
    op.execute("ALTER INDEX IF EXISTS ix_categories_id RENAME TO ix_categories_id_old")
    op.execute("ALTER INDEX IF EXISTS ix_categories_slug RENAME TO ix_categories_slug_old")

    # 4. Rename primary key constraint
    op.execute("ALTER TABLE categories_old RENAME CONSTRAINT categories_pkey TO categories_old_pkey")

    # 5. Drop self-referencing foreign key constraint on categories_old
    op.execute("ALTER TABLE categories_old DROP CONSTRAINT IF EXISTS categories_parent_id_fkey")

    # 6. Create categories table with columns ordered as in Product_Models.py:
    #    id, parent_id, slug, name, description, image_url, is_active, sort_order
    op.execute("""
        CREATE TABLE categories (
            id SERIAL PRIMARY KEY,
            parent_id INTEGER,
            slug VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            description VARCHAR,
            image_url VARCHAR,
            is_active BOOLEAN NOT NULL,
            sort_order INTEGER NOT NULL,
            CONSTRAINT categories_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES categories(id)
        );
    """)

    # 7. Copy data from categories_old into categories
    op.execute("""
        INSERT INTO categories (id, parent_id, slug, name, description, image_url, is_active, sort_order)
        SELECT id, parent_id, slug, name, description, image_url, is_active, sort_order FROM categories_old;
    """)

    # 8. Sync serial sequence value with existing max id
    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('categories', 'id'),
            COALESCE((SELECT MAX(id) FROM categories), 1),
            (SELECT COUNT(*) > 0 FROM categories)
        );
    """)

    # 9. Create indexes
    op.execute("CREATE INDEX ix_categories_id ON categories (id)")
    op.execute("CREATE UNIQUE INDEX ix_categories_slug ON categories (slug)")

    # 10. Drop categories_old
    op.execute("DROP TABLE categories_old CASCADE")


def downgrade() -> None:
    # Revert to original column order:
    # id, slug, name, parent_id, description, image_url, is_active, sort_order
    op.execute("ALTER TABLE categories RENAME TO categories_old")
    op.execute("ALTER SEQUENCE categories_id_seq RENAME TO categories_old_id_seq")
    op.execute("ALTER INDEX IF EXISTS ix_categories_id RENAME TO ix_categories_id_old")
    op.execute("ALTER INDEX IF EXISTS ix_categories_slug RENAME TO ix_categories_slug_old")
    op.execute("ALTER TABLE categories_old RENAME CONSTRAINT categories_pkey TO categories_old_pkey")
    op.execute("ALTER TABLE categories_old DROP CONSTRAINT IF EXISTS categories_parent_id_fkey")

    op.execute("""
        CREATE TABLE categories (
            id SERIAL PRIMARY KEY,
            slug VARCHAR NOT NULL,
            name VARCHAR NOT NULL,
            parent_id INTEGER,
            description VARCHAR,
            image_url VARCHAR,
            is_active BOOLEAN NOT NULL,
            sort_order INTEGER NOT NULL,
            CONSTRAINT categories_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES categories(id)
        );
    """)

    op.execute("""
        INSERT INTO categories (id, slug, name, parent_id, description, image_url, is_active, sort_order)
        SELECT id, slug, name, parent_id, description, image_url, is_active, sort_order FROM categories_old;
    """)

    op.execute("""
        SELECT setval(
            pg_get_serial_sequence('categories', 'id'),
            COALESCE((SELECT MAX(id) FROM categories), 1),
            (SELECT COUNT(*) > 0 FROM categories)
        );
    """)

    op.execute("CREATE INDEX ix_categories_id ON categories (id)")
    op.execute("CREATE UNIQUE INDEX ix_categories_slug ON categories (slug)")
    op.execute("DROP TABLE categories_old CASCADE")

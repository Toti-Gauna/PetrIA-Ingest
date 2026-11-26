"""Registry tables: load_runs, wells (one per sigla), well_records (one per idpozo).

Revision ID: 0001
Revises:
Create Date: 2026-11-26
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# The SQL below is plain fixed text on purpose: no string templates, nothing built at
# run time. The allowed location flags are written out in each CHECK.


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE geo.load_runs (
          id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
          source       text NOT NULL,             -- 'registry' (later 'production', ...)
          file_name    text NOT NULL,
          file_sha256  text NOT NULL,             -- the file's fingerprint
          status       text NOT NULL CHECK (status IN ('running', 'done')),
          started_at   timestamptz NOT NULL DEFAULT now(),
          finished_at  timestamptz,
          rows_read    integer,
          rows_loaded  integer,
          report       jsonb                      -- the full quality report
        );
        COMMENT ON TABLE geo.load_runs IS
          'One row per load: which official file, its SHA-256, and the quality report.';
        """
    )
    op.execute(
        """
        CREATE TABLE geo.wells (
          sigla          text PRIMARY KEY,                 -- the physical well
          geom           geometry(Point, 4326),            -- NULL when no valid point
          location_flag  text NOT NULL
                         CHECK (location_flag IN ('ok', 'swapped_fixed', 'invalid')),
          n_records      integer NOT NULL,                 -- how many idpozo it groups
          load_id        bigint NOT NULL REFERENCES geo.load_runs (id)
        );
        CREATE INDEX wells_geom_idx ON geo.wells USING gist (geom);
        COMMENT ON TABLE geo.wells IS
          'One row per physical well (sigla). Location: the lowest idpozo with a valid '
          'point. Source: Secretaria de Energia, Capitulo IV registry.';
        """
    )
    op.execute(
        """
        CREATE TABLE geo.well_records (
          idpozo                   bigint PRIMARY KEY,
          sigla                    text NOT NULL REFERENCES geo.wells (sigla),
          area                     text,
          cod_area                 text,
          empresa                  text,
          yacimiento               text,
          cod_yacimiento           text,
          formacion                text,
          cuenca                   text,
          provincia                text,
          cota                     text,   -- as published: no unit conversion
          profundidad              text,   -- as published: no unit conversion
          clasificacion            text,
          subclasificacion         text,
          tipo_recurso             text,
          sub_tipo_recurso         text,
          gasplus                  text,
          tipopozo                 text,
          tipoextraccion           text,
          tipoestado               text,
          adjiv_fecha_inicio_perf  text,   -- dates kept as published text for now
          adjiv_fecha_fin_perf     text,
          adjiv_fecha_inicio_term  text,
          adjiv_fecha_fin_term     text,
          geom                     geometry(Point, 4326),
          location_flag            text NOT NULL
                                   CHECK (location_flag IN ('ok', 'swapped_fixed', 'invalid')),
          load_id                  bigint NOT NULL REFERENCES geo.load_runs (id)
        );
        CREATE INDEX well_records_sigla_idx ON geo.well_records (sigla);
        COMMENT ON TABLE geo.well_records IS
          'One row per idpozo record, values as published (empty -> NULL). '
          'Source: Secretaria de Energia, Capitulo IV registry.';
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE geo.well_records")
    op.execute("DROP TABLE geo.wells")
    op.execute("DROP TABLE geo.load_runs")

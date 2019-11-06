"""
Load installed datasets into the CLICS sqlite DB
"""
import sqlite3
import contextlib

from cldfbench import iter_datasets
from cldfbench.cli_util import add_catalog_spec

from pyclics import interfaces
from pyclics.util import CATALOGS, catalog


def register(parser):
    for cat in CATALOGS:
        add_catalog_spec(parser, cat)
    parser.add_argument('--unloaded', action='store_true', default=False)


def run(args):
    with contextlib.ExitStack() as stack:
        for name in CATALOGS:
            setattr(args, name, stack.enter_context(catalog(name, args)))

        args.log.info('using {0.__name__} implementation {1.__module__}:{1.__name__}'.format(
            interfaces.IClicsForm, args.api.clicsform))
        args.api.db.create(exists_ok=True)
        args.log.info('loading datasets into {0}'.format(args.api.db.fname))
        try:
            in_db = args.api.db.datasets
        except (ValueError, sqlite3.OperationalError):  # pragma: no cover
            args.log.error('The existing database schema looks incompatible.')
            args.log.error('You may re-load all datasets after first removing {0}.'.format(
                args.api.db.fname))
            return
        for ds in iter_datasets(ep='lexibank.dataset'):
            if args.unloaded and ds.id in in_db:
                args.log.info('skipping {0} - already loaded'.format(ds.id))
                continue
            args.log.info('loading {0}'.format(ds.id))
            args.api.db.load(ds)
            with args.api.db.connection() as conn:
                from_clause = "FROM formtable WHERE form IS NULL"
                conc_id_fix = "FROM parametertable WHERE Concepticon_ID IS NULL"

                n = args.api.db.fetchone("SELECT count(id) " + from_clause, conn=conn)[0]
                c = args.api.db.fetchone("SELECT count(id) " + conc_id_fix, conn=conn)[0]

                if n:  # pragma: no cover
                    # This should not have happened anyway, because Form is marked as required in
                    # the default csvw metadata.
                    args.log.info('purging {0} empty forms from db'.format(n))
                    conn.execute("DELETE " + from_clause)
                    conn.commit()

                if c:
                    args.log.info('purging {0} problematic concepts from db.'.format(c))
                    conn.execute("DELETE " + conc_id_fix)
                    conn.commit()

        args.log.info('loading Concepticon data')
        args.api.db.load_concepticon_data(args.concepticon.api)
        args.log.info('loading Glottolog data')
        args.api.db.load_glottolog_data(args.glottolog.api)

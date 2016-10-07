# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import contextlib
import datetime
import sys

from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader

DJANGO_MIGRATIONS = """
CREATE TABLE "django_migrations"
("id" integer, "app" varchar(255) NOT NULL, "name" varchar(255) NOT NULL, "applied" timestamp NOT NULL);
"""


def insert_dj_migrations(index, app, name):
    now = datetime.datetime.utcnow().isoformat()
    # TODO: support multiple databases
    return "\nINSERT INTO django_migrations VALUES (%d, '%s', '%s', '%s'); \n" % (index, app, name, now)


class Command(BaseCommand):
    help = "Prints the SQL statements for the named migration."

    output_transaction = True

    def add_arguments(self, parser):
        parser.add_argument('--database', default=DEFAULT_DB_ALIAS,
                            help='Nominates a database to create SQL for. Defaults to the '
                            '"default" database.')

        parser.add_argument('-o', '--output',
                            help='Where to write the SQL result file.')

    def execute(self, *args, **options):
        # sqlmigrate doesn't support coloring its output but we need to force
        # no_color=True so that the BEGIN/COMMIT statements added by
        # output_transaction don't get colored either.
        options['no_color'] = True
        return super(Command, self).execute(*args, **options)

    def handle(self, *args, **options):
        # Get the database we're operating from
        connection = connections[options['database']]

        # Load up an executor to get all the migration data
        executor = MigrationExecutor(connection)

        # Load up an executor to get all the migration data
        loader = MigrationLoader(None, ignore_no_migrations=True)
        loader_graph = loader.graph

        migrated = set()

        django_migrations_id = 0
        if options['output'] is None:
            output_fn = sys.stdout
        else:
            output_fn = open(options['output'], 'w')

        with contextlib.closing(output_fn):
            # with open(options['output'], 'w') as out:
            output_fn.write('BEGIN;\n')
            output_fn.write(DJANGO_MIGRATIONS)

            for rn in loader_graph.root_nodes():
                rn_obj = loader_graph.node_map[rn]
                line = loader_graph.iterative_dfs(rn_obj)

                for node in line:
                    key = node.key

                    if key not in migrated:
                        plan = [(executor.loader.graph.nodes[node.key], False)]
                        output_fn.write('\n'.join(executor.collect_sql(plan)))
                        output_fn.write(insert_dj_migrations(django_migrations_id, node.key[0], node.key[1]))
                        migrated.add(key)

            output_fn.write('\nCOMMIT;')

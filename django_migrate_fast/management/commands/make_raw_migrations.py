# -*- coding: utf-8 -*-

from os import path, mkdir

from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader

from .common import gen_path, iterate_migrations

OTHER_PATH = 'other_apps'

# TODO: these two are needed for the other command that actually runs the migrations
# TODO: is there a way to use the django-migrations table with a Model/
# DJANGO_MIGRATIONS = """
# CREATE TABLE "django_migrations"
# ("id" integer, "app" varchar(255) NOT NULL, "name" varchar(255) NOT NULL, "applied" timestamp NOT NULL);
# """

# def insert_dj_migrations(index, app, name):
#     now = datetime.datetime.utcnow().isoformat()
#     # TODO: support multiple databases
#     return "\nINSERT INTO django_migrations VALUES (%d, '%s', '%s', '%s'); \n" % (index, app, name, now)


class Command(BaseCommand):
    help = "Prints the SQL statements for the named migration."

    output_transaction = True

    def add_arguments(self, parser):
        parser.add_argument('--database', default=DEFAULT_DB_ALIAS,
                            help='Nominates a database to create SQL for. Defaults to the '
                            '"default" database.')

    def execute(self, *args, **options):
        options['no_color'] = True
        return super(Command, self).execute(*args, **options)

    def handle(self, *args, **options):
        if not path.isdir(OTHER_PATH):
            mkdir(OTHER_PATH)

        # Get the database we're operating from
        connection = connections[options['database']]

        # Load up an executor to get all the migration data
        executor = MigrationExecutor(connection)

        # Load up an executor to get all the migration data
        loader = MigrationLoader(None, ignore_no_migrations=True)

        migrated = set()

        for key in iterate_migrations(loader.graph):
            if key not in migrated:
                plan = [(executor.loader.graph.nodes[key], False)]
                statements = ['BEGIN;'] + executor.collect_sql(plan) + ['COMMIT;']
                out_fname = gen_path(key)
                print("Writing to {}".format(out_fname))

                with open(out_fname, 'w') as out:
                    out.writelines([s + '\n' for s in statements])

                migrated.add(key)

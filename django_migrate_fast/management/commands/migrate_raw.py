# -*- coding: utf-8 -*-

import datetime

from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.loader import MigrationLoader

from .common import gen_path, iterate_migrations, is_not_migrated


OTHER_PATH = 'other_apps'

DJANGO_MIGRATIONS = """
CREATE TABLE "django_migrations"
("id" integer, "app" varchar(255) NOT NULL, "name" varchar(255) NOT NULL, "applied" timestamp NOT NULL);
"""


def insert_dj_migrations(index, app, name):
    now = datetime.datetime.utcnow().isoformat()
    # TODO: support multiple databases
    return "\nINSERT INTO django_migrations VALUES (%d, '%s', '%s', '%s'); \n" % (index, app, name, now)


def execute_sql(connection, sql):
    with connection.cursor() as cursor:
        cursor.execute(sql)
        row = cursor.fetchone()
        print(row)
        return row


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
        # Get the database we're operating from
        connection = connections[options['database']]
        assert is_not_migrated(connection), "Try on an empty database please"

        # Load up an executor to get all the migration data
        loader = MigrationLoader(None, ignore_no_migrations=True)

        migrated = set()

        execute_sql(connection, DJANGO_MIGRATIONS)

        for key in iterate_migrations(loader.graph):
            if key not in migrated:
                sql_file = gen_path(key)
                print("Loading file %s" % sql_file)
                for line in open(sql_file):
                    execute_sql(connection, line)

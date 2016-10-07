import mock
import inspect

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import migrations, connection, DEFAULT_DB_ALIAS
from django.test.utils import CaptureQueriesContext

from .common import is_not_migrated

CREATED_FILES = set()


class MyRunPython(migrations.RunPython):
    @property
    def output_fname(self):
        module = inspect.getmodule(self.code)
        return '{}.sql'.format(module.__name__.replace('.', '/'))

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        with CaptureQueriesContext(connection) as queries:
            go_forward = super(MyRunPython, self).database_forwards(
                app_label, schema_editor, from_state, to_state)

        captured = [q['sql'] for q in queries.captured_queries]

        if len(captured) > 0:
            lines = ["BEGIN"] + captured + ["COMMIT"]
            out_path = self.output_fname
            assert out_path not in CREATED_FILES, "Two RunPython operations from the same file??"

            with open(out_path, 'w') as out:
                for line in lines:
                    out.write("{};\n".format(line))

            CREATED_FILES.add(out_path)

        return go_forward


class Command(BaseCommand):
    help = "Generate SQL files from all the migrations involving RunPython"

    def add_arguments(self, parser):
        # TODO: take a database url to use instead of the usual hard coded settings?
        parser.add_argument(
            '--database', default=DEFAULT_DB_ALIAS,
            help='Nominates a database to create SQL for. Defaults to the "default" database.',
        )

    @mock.patch('django.db.migrations.RunPython', new=MyRunPython)
    def handle(self, *args, **options):
        assert is_not_migrated(connection), "Need to run this on an empty database!"
        call_command('migrate')

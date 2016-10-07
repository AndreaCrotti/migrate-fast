from django.db.utils import OperationalError

from os import path, mkdir

OTHER_PATH = 'other_apps'


def is_not_migrated(connection):
    with connection.cursor() as cursor:
        try:
            cursor.execute("SELECT COUNT(*) FROM django_migrations;")
            row = cursor.fetchone()
        except OperationalError:
            return True
        else:
            return row[0] == 0


def gen_path(key):
    """Generate the path to the file to write out
    """
    root, migration = key[0], key[1]
    if not path.isdir(root):
        right_path = path.join(OTHER_PATH, root)
        if not path.isdir(right_path):
            mkdir(right_path)

    else:
        right_path = '{}/migrations'.format(root)

    return '{}/{}.sql'.format(right_path, migration)


def iterate_migrations(graph):
    for rn in graph.root_nodes():
        rn_obj = graph.node_map[rn]
        line = graph.iterative_dfs(rn_obj)

        for node in line:
            yield node.key

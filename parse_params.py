import argparse

parser = argparse.ArgumentParser()
parser.add_argument('x', help='the base', type=int)
parser.add_argument('y', help='the exponent', type=int)
group = parser.add_mutually_exclusive_group()
group.add_argument('-v', '--verbose', help='increase output verbosity', action='store_true')
group.add_argument('-q', '--quiet', help='decrease output verbosity', action='store_true')

subparsers = parser.add_subparser(help='operations help')
parser_create = subparsers.add_parser(title='create', help='create help')
group_create = parser_create.add_argument('
parser_delete = subparsers.add_parser(title='delete', help='delete help')
parser_stop = subparsers.add_parser(title='stop', help='stop help')
parser_upgrade = subparsers.add_parser(title='upgrade', help='upgrade help')
parser_restart = subparsers.add_parser(title='restart', help='restart help')
parser_attach = subparsers.add_parser(title='attach', help='attach help')
parser_detach = subparsers.add_parser(title='detach', help='detach help')

args = parser.parse_args()
answer = args.x**args.y


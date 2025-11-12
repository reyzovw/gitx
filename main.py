from instance import handler
import argparse

def main():
    parser = argparse.ArgumentParser(prog='python main.py')
    subparsers = parser.add_subparsers(dest='command')

    init_parser = subparsers.add_parser('init')
    init_parser.add_argument('path', nargs='?', default='.')

    clone_parser = subparsers.add_parser('clone')
    clone_parser.add_argument('url')

    add_parser = subparsers.add_parser('add')
    add_parser.add_argument('files', nargs='+')

    commit_parser = subparsers.add_parser('commit')
    commit_parser.add_argument('-m', '--message', required=True)

    branch_parser = subparsers.add_parser('branch')
    branch_parser.add_argument('-M', '--move', dest='new_name')

    remote_parser = subparsers.add_parser('remote')
    remote_parser.add_argument('action')
    remote_parser.add_argument('name')
    remote_parser.add_argument('url', nargs='?')

    push_parser = subparsers.add_parser('push')
    push_parser.add_argument('-u', '--set-upstream', action='store_true')
    push_parser.add_argument('remote')
    push_parser.add_argument('branch')

    auth_parser = subparsers.add_parser('auth')
    auth_parser.add_argument('token')

    args = parser.parse_args()

    kwargs = {}
    if hasattr(args, 'url'):
        if args.command == 'clone':
            kwargs['repository_url'] = args.url
        elif args.command == 'remote':
            kwargs['url'] = args.url
    if hasattr(args, 'files'): kwargs['files'] = args.files
    if hasattr(args, 'message'): kwargs['message'] = args.message
    if hasattr(args, 'new_name'): kwargs['new_name'] = args.new_name
    if hasattr(args, 'action'): kwargs['action'] = args.action
    if hasattr(args, 'name'): kwargs['name'] = args.name
    if hasattr(args, 'set_upstream'): kwargs['set_upstream'] = args.set_upstream
    if hasattr(args, 'branch'): kwargs['branch'] = args.branch
    if hasattr(args, 'remote'): kwargs['remote'] = args.remote
    if hasattr(args, 'token'): kwargs['token'] = args.token

    handler.execute(args.command, **kwargs)


if __name__ == '__main__':
    main()


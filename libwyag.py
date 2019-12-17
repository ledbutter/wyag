import sys
import argparse
import collections
import configparser
import hashlib
import os
import zlib
from GitCommands import *
import GitRepository

argparser = argparse.ArgumentParser(description="The stupid content tracker")

argsubparsers = argparser.add_subparsers(title="Commands", dest="command")
argsubparsers.required = True

argsp = argsubparsers.add_parser("init", help="Initialize a new, empty repository.")
argsp.add_argument("path", metavar="directory", nargs="?", default=".", help="Where to create the repository.")

argsp = argsubparsers.add_parser("cat-file", help="Provide content of repository objects")
argsp.add_argument("type", metavar="type", choices=["blob", "commit", "tag", "tree"], help="Specify the type")
argsp.add_argument("object", metavar="object", help="The object to display")

argsp = argsubparsers.add_parser("hash-object", help="Compute object ID and optionally creates a blob from a file")
argsp.add_argument("-t", metavar="type", dest="type", choices=["blob", "commit", "tag", "tree"], default="blob", help="Specify the type")
argsp.add_argument("-w", dest="write", action="store_true", help="Actually write the object into the database")
argsp.add_argument("path", help="Read object from <file>")

argsp = argsubparsers.add_parser("log", help="Display history of a given commit.")
argsp.add_argument("commit", default="HEAD", nargs="?", help="Commit to start at.")

argsp = argsubparsers.add_parser("ls-tree", help="Pretty-print a tree object.")
argsp.add_argument("object", help="The object to show.")

argsp = argsubparsers.add_parser("checkout", help="Checkout a commit inside of a directory.")
argsp.add_argument("commit", help="The commit or tree to checkout.")
argsp.add_argument("path", help="The EMPTY directory to checkout on.")

argsp = argsubparsers.add_parser("show-ref", help="List references.")

argsp = argsubparsers.add_parser("tag", help="List and create tags.")
argsp.add_argument("-a", action="store_true", dest="create_tag_object", help="Whether to create a tag object.")
argsp.add_argument("name", nargs="?", help="The new tag's name.")
argsp.add_argument("object", default="HEAD", nargs="?", help="The object the new tag will point to.")

argsp = argsubparsers.add_parser("rev-parse", help="Parse revision (or other objects) identifiers.")
argsp.add_argument("--wyag-type", metavar="type", dest="type", choices=["blob", "commit", "tag", "tree"], default=None, help="Specify the expected type.")
argsp.add_argument("name", help="The name to parse.")

def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)

    if   args.command == "add"          : cmd_add(args)
    elif args.command == "cat-file"     : cmd_cat_file(args)
    elif args.command == "checkout"     : cmd_checkout(args)
    elif args.command == "commit"       : cmd_commit(args)
    elif args.command == "hash-object"  : cmd_hash_object(args)
    elif args.command == "init"         : cmd_init(args)
    elif args.command == "log"          : cmd_log(args)
    elif args.command == "ls-tree"      : cmd_ls_tree(args)
    elif args.command == "merge"        : cmd_merge(args)
    elif args.command == "rebase"       : cmd_rebase(args)
    elif args.command == "rev-parse"    : cmd_rev_parse(args)
    elif args.command == "rm"           : cmd_rm(args)
    elif args.command == "show-ref"     : cmd_show_ref(args)
    elif args.command == "tag"          : cmd_tag(args)

def cmd_init(args):
    repo_create(args.path)

def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo, args.object, fmt=args.type.encode())

def cat_file(repo, obj, fmt=None):
    obj = object_read(repo, object_find(repo, obj, fmt=fmt))
    sys.stdout.buffer.write(obj.serialize())

def cmd_hash_object(args):
    if args.write:
        repo = GitRepository.GitRepository(".")
    else:
        repo = None

    with open(args.path, "rb") as fd:
        sha = object_hash(fd, args.type.encode(), repo)
        print(sha)

def cmd_log(args):
    repo = repo_find()

    print("digraph wyaglog{")
    log_graphviz(repo, object_find(repo, args.commit), set())
    print("}")

def log_graphviz(repo, sha, seen):
    if sha in seen:
        return
    seen.add(sha)

    commit = object_read(repo, sha)
    assert(commit.fmt == b'commit')

    if not b'parent' in commit.kvlm.keys():
        # initial commit
        return

    parents = commit.kvlm[b'parent']
    if type(parents) != list:
        parents = [parents]

    for p in parents:
        p = p.decode("ascii")
        print("c_{0} -> c_{1};".format(sha, p))
        log_graphviz(repo, p, seen)

def cmd_ls_tree(args):
    repo = repo_find()
    obj = object_read(repo,object_find(repo, args.object, fmt=b'tree'))
    
    for item in obj.items:
        print("{0} {1} {2}\t{3}".format(
            "0" * (6 - len(item.mode)) + item.mode.decode("ascii"),
            # Git's ls-tree displays the type of the object points to. We can do that too
            object_read(repo, item.sha).fmt.decode("ascii"),
            item.sha,
            item.path.decode("ascii")))

def cmd_checkout(args):
    repo = repo_find()
    obj = object_read(repo, object_find(repo, args.commit))

    # If the object is a commit, we grab its tree
    if obj.fmt == b'commit':
        obj = object_read(repo, obj.kvlm[b'tree'].decode("ascii"))

    # Verify that path is an empty directory
    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception("Not a directory {0}!".format(args.path))
        if os.listdir(args.path):
            raise Exception("Not empty {0}!".format(args.path))
    else:
        os.makedirs(args.path)

    tree_checkout(repo, obj, os.path.realpath(args.path).encode())

def tree_checkout(repo, tree, path):
    for item in tree.items:
        obj = object_read(repo, item.sha)
        dest = os.path.join(path, item.path)

        if obj.fmt == b'tree':
            os.mkdir(dest)
            tree_checkout(repo, obj, dest)
        elif obj.fmt == b'blob':
            with open(dest, 'wb') as f:
                f.write(obj.blobdata)

def cmd_show_ref(args):
    repo = repo_find()
    refs = ref_list(repo)
    show_ref(repo, refs, prefix="refs")

def show_ref(repo, refs, with_hash=True, prefix=""):
    for k, v in refs.items():
        if type(v) == str:
            print("{0}{1}{2}".format(
                v + " " if with_hash else "",
                prefix + "/" if prefix else "",
                k))
        else:
            show_ref(repo, v, with_hash=with_hash, prefix="{0}{1}{2}".format(prefix, "/" if prefix else "", k))

def cmd_tag(args):
    repo = repo_find()

    if args.name:
        tag_create(args.name, args.object, type="object" if args.create_tag_object else "ref")
    else:
        refs = ref_list(repo)
        show_ref(repo, refs["tags"], with_hash=False)

def cmd_rev_parse(args):
    if args.type:
        fmt = args.type.encode()

    repo = repo_find()
    print(object_find(repo, args.name, ars.type, follow=True))
import os
import configparser
import GitRepository
import zlib
import hashlib
import GitObject
import collections

def repo_create(path):
    """Create a new repository at path."""

    return GitRepository.GitRepository(path)

def repo_find(path=".", required=True):
    # todo: memoize this (except for ".")
    realPath = os.path.realpath(path)

    if os.path.isdir(os.path.join(realPath, ".git")):
        return GitRepository.GitRepository(realPath)

    # If we haven't returned, recurse to parent
    parent = os.path.realpath(os.path.join(realPath, ".."))

    if parent == realPath:
        # Bottom case
        # os.path.join("/", "..") == "/":
        # If parent==path, then path is root.
        if required:
            raise Exception("No git directory found in %s hierarchy" % path)
        else:
            return None

    return repo_find(parent, required)

def object_read(repo, sha):
    """Read object object_id from Git repository repo.  Return a
    GitObject whose exact type depends on the object."""

    path = repo.repo_file("objects", sha[0:2], sha[2:])

    with open (path, "rb") as f:
        raw = zlib.decompress(f.read())

        # Read object type
        x = raw.find(b' ')
        fmt = raw[0:x]

        # Read and validate object size
        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw)-y-1:
            raise Exception("Malformed object {0}: bad length".format(sha))

        # Pick constructor
        if   fmt==b'commit' : c=GitObject.GitCommit
        elif fmt==b'tree'   : c=GitObject.GitTree
        elif fmt==b'tag'    : c=GitObject.GitTag
        elif fmt==b'blob'   : c=GitObject.GitBlob
        else:
            raise Exception("Unknown type %s for object %s".format(fmt.decode("ascii"), sha))

        # Call constructor and return object
        return c(repo, raw[y+1:])

def object_find(repo, name, fmt=None, follow=True):
    # will implement this later
    return name

def object_write(obj, actually_write=True):
    # Serialize object data
    data = obj.serialize()
    # Add header
    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data
    # Compute hash
    sha = hashlib.sha1(result).hexdigest()

    if actually_write:
        # Compute path
        path = obj.repo.repo_file("objects", sha[0:2], sha[2:], mkdir=actually_write)

        with open(path, 'wb') as f:
            # Compress and write
            f.write(zlib.compress(result))

    return sha
    
def object_hash(fd, fmt, repo=None):
    data = fd.read()

    # Choose constructor depending on
    # object type found in header.
    if   fmt==b'commit' : obj=GitObject.GitCommit(repo, data)
    elif fmt==b'tree'   : obj=GitObject.GitTree(repo, data)
    elif fmt==b'tag'    : obj=GitObject.GitTag(repo, data)
    elif fmt==b'blob'   : obj=GitObject.GitBlob(repo, data)
    else:
        raise Exception("Unknown type %s!" % fmt)

    return object_write(obj, repo)
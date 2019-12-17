import os
import configparser
import GitCommands

class GitRepository(object):
    """A git repository"""

    worktree = None
    gitdir = None
    conf = None

    # the * in *path means a variable length argument list
    def repo_path(self, *path):
        """Compute path under repo's gitdir."""
        return os.path.join(self.gitdir, *path)

    def repo_file(self, *path, mkdir=False):
        """Same as repo_path, but create dirname(*path) if absent. For example,
        repo_file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create
        .git/refs/remotes/origin."""

        if self.repo_dir(*path[:-1], mkdir=mkdir):
            return self.repo_path(*path)
        
    def repo_dir(self, *path, mkdir=False):
        """Same as repo_path, but mkdir *path if absent if mkdir."""

        full_path = self.repo_path(*path)

        if os.path.exists(full_path):
            if (os.path.isdir(full_path)):
                return full_path
            else:
                raise Exception("Not a directory %s" % full_path)

        if mkdir:
            os.makedirs(full_path)
            return full_path
        else:
            return None

    @staticmethod
    def repo_default_config():
        ret = configparser.ConfigParser()    

        ret.add_section("core")
        ret.set("core", "repositoryformatversion", "0")
        ret.set("core", "filemode", "false")
        ret.set("core", "bare", "false")

        return ret

    @staticmethod
    def get_git_dir(path):
        if (path.endswith(".git")):
            return path

        return os.path.join(path, ".git")

    def initialize_git_file(self, fileName, initialContent):
        if (not os.path.exists(self.repo_path(fileName))):
            with open(self.repo_file(fileName), "w") as f:
                f.write(initialContent)

    def __init__(self, path):
        # First, we make sure the path either doesn't exist or is an empty dir.

        if os.path.exists(path):
            if not os.path.isdir(path):
                raise Exception("%s is not a directory!" % path)
            # if os.listdir(path):
            #     raise Exception("%s is not empty!" % path)
        else:
            os.makedirs(self.get_git_dir(path))

        self.worktree = path
        self.gitdir = self.get_git_dir(self.worktree)

        if not os.path.isdir(self.gitdir):
            raise Exception("Not a Git repository %s" % path)

        assert(self.repo_dir("branches", mkdir=True))
        assert(self.repo_dir("objects", mkdir=True))
        assert(self.repo_dir("refs", "tags", mkdir=True))
        assert(self.repo_dir("refs", "heads", mkdir=True))

        # .git/description
        self.initialize_git_file("description", "Unnamed repository; edit this file 'description' to name the repository.\n")

        # .git/head
        self.initialize_git_file("HEAD", "ref: refs/heads/master\n")

        # .git/config
        if (not os.path.exists(self.repo_path("config"))):
            with open(self.repo_file("config"), "w") as f:
                config = self.repo_default_config()
                config.write(f)

        # Read configuration file in .git/config
        self.conf = configparser.ConfigParser()
        cf = self.repo_file("config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        else:
            raise Exception("Configuration file missing")

        vers = int(self.conf.get("core", "repositoryformatversion"))
        if vers != 0:
            raise Exception("Unsupported repositoryformatversion %s" % vers)
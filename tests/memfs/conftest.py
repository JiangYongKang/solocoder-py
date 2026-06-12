from solocoder_py.memfs import MemoryFileSystem


def make_fs() -> MemoryFileSystem:
    return MemoryFileSystem(default_owner="root", default_group="root")

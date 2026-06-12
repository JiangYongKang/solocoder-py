class PathNormError(Exception):
    pass


class InvalidPathError(PathNormError):
    def __init__(self, path: str, reason: str = ""):
        self.path = path
        self.reason = reason
        msg = f"Invalid path: {path!r}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


class SymlinkLoopError(PathNormError):
    def __init__(self, path: str, loop_path: str = ""):
        self.path = path
        self.loop_path = loop_path
        msg = f"Symlink loop detected at path: {path!r}"
        if loop_path:
            msg += f" (loop involves: {loop_path!r})"
        super().__init__(msg)


class PathNotFoundError(PathNormError):
    def __init__(self, path: str, component: str = ""):
        self.path = path
        self.component = component
        msg = f"Path not found: {path!r}"
        if component:
            msg += f" (missing component: {component!r})"
        super().__init__(msg)

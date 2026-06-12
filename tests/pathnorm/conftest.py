from solocoder_py.pathnorm import (
    InMemorySymlinkResolver,
    PathNormalizer,
    PathResolver,
)


def make_normalizer(case_sensitive: bool = True) -> PathNormalizer:
    return PathNormalizer(case_sensitive=case_sensitive)


def make_resolver(
    symlinks: dict | None = None,
    directories: set | None = None,
    case_sensitive: bool = True,
    normalizer: PathNormalizer | None = None,
) -> PathResolver:
    symlink_resolver = InMemorySymlinkResolver(
        symlinks=symlinks,
        directories=directories,
        case_sensitive=case_sensitive,
    )
    norm = normalizer or PathNormalizer(case_sensitive=case_sensitive)
    return PathResolver(symlink_resolver=symlink_resolver, normalizer=norm)

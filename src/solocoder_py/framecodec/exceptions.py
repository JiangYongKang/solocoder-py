from __future__ import annotations


class FrameCodecError(Exception):
    pass


class FrameConfigError(FrameCodecError):
    pass


class IncompleteFrameError(FrameCodecError):
    pass


class CrcCheckError(FrameCodecError):
    pass


class VersionIncompatibleError(FrameCodecError):
    pass


class FrameTooLargeError(FrameCodecError):
    pass

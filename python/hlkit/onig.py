from ._onig import ffi, lib


def version() -> str:
    ver = ffi.string(lib.onig_version())
    return ver.decode()


def copyright() -> str:
    info = ffi.string(lib.onig_copyright())
    return info.decode()

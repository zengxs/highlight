import os

from cffi import FFI

ONIG_DIR = "./swift/Sources/COnig"  # relative path for `setup.py`


def get_c_filepath(filename):
    return os.path.join(ONIG_DIR, filename)


ffibuilder = FFI()

# fmt: off
ffibuilder.cdef(r"""
const char* onig_version();
const char* onig_copyright();
""")
# fmt: on

c_files = [
    "ascii.c",
    "big5.c",
    "cp1251.c",
    "euc_jp_prop.c",
    "euc_jp.c",
    "euc_kr.c",
    "euc_tw.c",
    "gb18030.c",
    "iso8859_1.c",
    "iso8859_2.c",
    "iso8859_3.c",
    "iso8859_4.c",
    "iso8859_5.c",
    "iso8859_6.c",
    "iso8859_7.c",
    "iso8859_8.c",
    "iso8859_9.c",
    "iso8859_10.c",
    "iso8859_11.c",
    "iso8859_13.c",
    "iso8859_14.c",
    "iso8859_15.c",
    "iso8859_16.c",
    "koi8_r.c",
    "koi8.c",
    "mktable.c",
    "onig_init.c",
    "regcomp.c",
    "regenc.c",
    "regerror.c",
    "regexec.c",
    "regext.c",
    "reggnu.c",
    "regparse.c",
    # "regposerr.c",
    # "regposix.c",
    "regsyntax.c",
    "regtrav.c",
    "regversion.c",
    "sjis_prop.c",
    "sjis.c",
    "st.c",
    "unicode.c",
    "unicode_fold1_key.c",
    "unicode_fold2_key.c",
    "unicode_fold3_key.c",
    "unicode_unfold_key.c",
    "utf8.c",
    "utf16_be.c",
    "utf16_le.c",
    "utf32_be.c",
    "utf32_le.c",
]

ffibuilder.set_source(
    "hlkit._onig",
    """
    #include "oniguruma.h"
    """,
    sources=list(map(get_c_filepath, c_files)),
    include_dirs=[get_c_filepath("include")],
    libraries=[],
)

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)

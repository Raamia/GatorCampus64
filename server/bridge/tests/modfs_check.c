// Reads a .modfs with coopdx's own miniz, the same calls as mod_fs_read() in sm64coopdx v1.5.1
// (src/pc/mods/mod_fs.cpp): mz_zip_reader_init_mem, locate properties.json, then for every entry
// is_file_a_directory / file_stat / extract_to_heap. Prints "name size isText" per file and the
// properties.json text. Built and run by test_modfs_miniz.py when the coopdx source is available.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "miniz.h"

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "usage: modfs_check file.modfs\n"); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror("open"); return 2; }
    fseek(f, 0, SEEK_END);
    size_t n = ftell(f);
    rewind(f);
    void *buf = malloc(n);
    if (fread(buf, 1, n, f) != n) { fprintf(stderr, "short read\n"); return 2; }
    fclose(f);

    mz_zip_archive zip[1] = {0};
    if (!mz_zip_reader_init_mem(zip, buf, n, 0)) {
        fprintf(stderr, "init: %s\n", mz_zip_get_error_string(mz_zip_get_last_error(zip)));
        return 1;
    }
    int pi = mz_zip_reader_locate_file(zip, "properties.json", NULL, 0);
    if (pi >= 0) {
        size_t sz;
        char *p = mz_zip_reader_extract_to_heap(zip, pi, &sz, 0);
        if (!p) { fprintf(stderr, "properties extract failed\n"); return 1; }
        printf("PROPERTIES %.*s\n", (int) sz, p);
        mz_free(p);
    }
    unsigned num = mz_zip_reader_get_num_files(zip);
    for (unsigned i = 0; i != num; ++i) {
        mz_zip_archive_file_stat st;
        if (mz_zip_reader_is_file_a_directory(zip, i) || !mz_zip_reader_file_stat(zip, i, &st)) continue;
        if (strcmp(st.m_filename, "properties.json") == 0) continue;
        size_t sz;
        unsigned char *d = mz_zip_reader_extract_to_heap(zip, i, &sz, 0);
        if (!d || sz != st.m_uncomp_size) { fprintf(stderr, "extract %s failed\n", st.m_filename); return 1; }
        int text = 1;   // mod_fs_file_detect_text_mode
        for (size_t k = 0; k != sz; ++k) if (iscntrl(d[k]) && !isspace(d[k])) { text = 0; break; }
        printf("FILE %s %zu %d %.*s\n", st.m_filename, sz, text, (int) sz, d);
        mz_free(d);
    }
    mz_zip_reader_end(zip);
    free(buf);
    return 0;
}

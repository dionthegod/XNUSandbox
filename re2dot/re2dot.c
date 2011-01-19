#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>

/*
 * types and prototypes for libMatch
 */
struct match;
typedef struct match matchExec_t;

int matchInit(matchExec_t **h, void *, void *);
int matchUnpack(unsigned char *buffer, int length, matchExec_t *h);
int matchDiagram(int fd, matchExec_t *h, const char *label);
void matchFree(matchExec_t *h);

static unsigned char *load_re_from_file(const char *fname, unsigned int *length)
{
  unsigned char *rv = NULL;
  struct stat s;   
  FILE *f = fopen(fname, "rb");
  *length = 0;

  if (f != NULL) { 
    fstat(fileno(f), &s);

    rv = malloc(s.st_size);
    if (fread(rv, s.st_size, 1, f) == -1) {
      free(rv);
      return NULL;
    }
    *length = s.st_size;
    fclose(f);
  }

  return rv;
}

int main(int argc, char *argv[])
{
  int rv;
  unsigned char *buffer;
  unsigned int length;
  matchExec_t *h;

  if (2 != argc) {
    fprintf(stderr, "usage:\n"
                    "    re2dot some_regex.re\n\n"
                    "    Takes a regex pulled from a binary sandbox profile\n"
                    "    (could use resnarf) and dumps a .dot file for use\n"
                    "    with graphviz.  Steals the code from undoc'd function\n"
                    "    in libMatch.dylib\n");
    return -1;
  }

  buffer = load_re_from_file(argv[1], &length);
  if (buffer == NULL) {
    fprintf(stderr, "load_re_from_file failed\n");
    return 0;
  }

  rv = matchInit(&h, malloc, free);
  if (rv != 0) {
    fprintf(stderr, "matchInit failed: %d\n", rv);
    free(buffer);
    return 0;
  }

  rv = matchUnpack(buffer, length, h);
  if (rv != 0) {
    fprintf(stderr, "matchUnpack failed: %d\n", rv);
    matchFree(h);
    free(buffer);
    return 0;
  }

  matchDiagram(STDOUT_FILENO, h, argv[1]);

  matchFree(h);
  free(buffer);
  return 0;
}

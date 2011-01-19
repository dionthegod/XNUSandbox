#include <sys/types.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <dlfcn.h>
#include <err.h>

int main(int argc, char *argv[])
{
  int rv;
  char *full;

  if (argc != 3) {
    fprintf(stderr, 
        "usage:\n"
        "    sbsnarf full-path-to-sb output-bytecode-file\n\n");
    return -1;
  }

  full = realpath(argv[1], NULL);
  printf("[+] full path to sb: \"%s\"\n", full);

  void *h = dlopen("libsandbox.1.dylib", RTLD_FIRST | RTLD_LAZY | RTLD_LOCAL);
  if (NULL == h) {
    errx(-1, "dlopen failed: %s", dlerror());
  }

  void *(*scf)(char *, int, char **) = dlsym(h, "sandbox_compile_file");
  if (NULL == scf) {
    errx(-1, "dlsym failed: %s", dlerror());
  }

  void (*sfp)(void *) = dlsym(h, "sandbox_free_profile");
  if (NULL == sfp) {
    errx(-1, "dlsym failed: %s", dlerror());
  }

  char *error;
  struct {
    unsigned int type;
    user_addr_t bytecode;
    user_size_t bytecode_length;
  } *sb = scf(full, 0, &error);
  if (NULL == sb) {
    dlclose(h);
    errx(-1, "sandbox_compile_file failed: %s", error);
  }

  if (NULL != error) {
    free(error);
  }

  FILE *f_out = fopen(argv[2], "wb");
  if (NULL == f_out) {
    sfp(sb);
    dlclose(h);
    err(-1, "fopen failed:");
  }

  rv = fwrite((void *) sb->bytecode, sb->bytecode_length, 1, f_out);
  if (1 != rv) {
    sfp(sb);
    dlclose(h);
    err(-1, "fwrite failed:");    
  }
  
  fclose(f_out);
  sfp(sb);
  dlclose(h);

  printf("[+] success!\n");

  return 0;
}

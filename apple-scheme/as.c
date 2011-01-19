#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "syms.h"

static unsigned int base;

void *hidden_dlsym(const char *name) {
  unsigned int off = get_offset(name);
  printf("[+] \"%s\" @ 0x%08x\n", name, off);
  return (void *)(off + base);
}

int main(int argc, char *argv[])
{
  void *sc;

  sc = malloc(1024 * 1024 * 4);

  void *h = dlopen("/usr/lib/libsandbox.dylib", RTLD_LAZY);
  printf("h = %p\n", h);
  void *loaded_base = dlsym(h, "sandbox_compile_file");
  printf("sandbox_compile_file = %p\n", loaded_base);

  unsigned int static_base = get_offset("_sandbox_compile_file");
  base = (unsigned int) loaded_base - static_base;

  int (*scheme_init)(void *) = 
      (int (*)(void *)) hidden_dlsym("_scheme_init");
  void (*scheme_set_input_port_file)(void *, FILE *) = 
      (void (*)(void *, FILE *)) hidden_dlsym("_scheme_set_input_port_file");
  void (*scheme_set_output_port_file)(void *, FILE *) =
      (void (*)(void *, FILE *)) hidden_dlsym("_scheme_set_output_port_file");
  void (*scheme_load_file)(void *, FILE *) = 
      (void (*)(void *, FILE *)) hidden_dlsym("_scheme_load_file");
  void (*scheme_deinit)(void *) = 
      (void (*)(void *)) hidden_dlsym("_scheme_deinit");

  if (!scheme_init(sc)) {
    fprintf(stderr, "Uh ohz!\n");
  } else {
    scheme_set_input_port_file(sc, stdin);
    scheme_set_output_port_file(sc, stdout);

    scheme_load_file(sc, stdin);

    scheme_deinit(sc);
  }

  dlclose(h);
  free(sc);
  return 0;
}

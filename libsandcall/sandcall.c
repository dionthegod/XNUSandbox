#include <sys/types.h>
#include <stddef.h>

/*
 * This is included in libSystem
 */
int __sandbox_ms(const char *policyname, int call, void *arg);

int sandbox_init_bytecode(void *buff, size_t len, void *unk)
{
  struct {
    user_addr_t bytecode;
    user_size_t bytecode_len;
    user_addr_t unknown;
  } args;

  args.bytecode = CAST_USER_ADDR_T(buff);
  args.bytecode_len = (user_size_t) len;
  args.unknown = CAST_USER_ADDR_T(unk);

  return __sandbox_ms("Sandbox", 0 /*call*/, &args);
}

int sandbox_init_builtin(char *policy)
{
  struct {
    user_addr_t policy;
  } args;

  args.policy = CAST_USER_ADDR_T(policy);

  return __sandbox_ms("Sandbox", 1 /*call*/, &args);
}


/*
 * sandbox_check from /usr/include/sandbox.h proxies this syscall
 */
int sandbox_check_raw(/*out*/ int *rv, pid_t pid, char *operation, 
    int filter_type, char *path)
{
  int msrv;

  struct {
    int rv;
    int success;
  } results;

  struct {
    user_addr_t result;
    pid_t pid;
    user_addr_t operation;
    user_long_t filter_type;
    user_addr_t path;
  } args;

  args.result = CAST_USER_ADDR_T(&results);
  args.pid = pid;
  args.operation = CAST_USER_ADDR_T(operation);
  args.filter_type = (user_long_t) filter_type;
  args.path = CAST_USER_ADDR_T(path);

  msrv = __sandbox_ms("Sandbox", 2 /*call*/, &args);
  if (msrv != 0)
    return msrv;

  if (rv != NULL)
    *rv = results.rv;

  return msrv;
}

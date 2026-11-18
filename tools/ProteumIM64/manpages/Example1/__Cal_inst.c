
static char sccsid[] = "@(#)cal.c	4.4 (Berkeley) 87/05/28"; 
typedef unsigned char __u_char; 
typedef unsigned short int __u_short; 
typedef unsigned int __u_int; 
typedef unsigned long int __u_long; 
typedef signed char __int8_t; 
typedef unsigned char __uint8_t; 
typedef signed short int __int16_t; 
typedef unsigned short int __uint16_t; 
typedef signed int __int32_t; 
typedef unsigned int __uint32_t; 
typedef signed long int __int64_t; 
typedef unsigned long int __uint64_t; 
typedef __int8_t __int_least8_t; 
typedef __uint8_t __uint_least8_t; 
typedef __int16_t __int_least16_t; 
typedef __uint16_t __uint_least16_t; 
typedef __int32_t __int_least32_t; 
typedef __uint32_t __uint_least32_t; 
typedef __int64_t __int_least64_t; 
typedef __uint64_t __uint_least64_t; 
typedef long int __quad_t; 
typedef unsigned long int __u_quad_t; 
typedef long int __intmax_t; 
typedef unsigned long int __uintmax_t; 
typedef unsigned long int __dev_t; 
typedef unsigned int __uid_t; 
typedef unsigned int __gid_t; 
typedef unsigned long int __ino_t; 
typedef unsigned long int __ino64_t; 
typedef unsigned int __mode_t; 
typedef unsigned long int __nlink_t; 
typedef long int __off_t; 
typedef long int __off64_t; 
typedef int __pid_t; 
typedef struct { int __val[2]; } __fsid_t; 
typedef long int __clock_t; 
typedef unsigned long int __rlim_t; 
typedef unsigned long int __rlim64_t; 
typedef unsigned int __id_t; 
typedef long int __time_t; 
typedef unsigned int __useconds_t; 
typedef long int __suseconds_t; 
typedef int __daddr_t; 
typedef int __key_t; 
typedef int __clockid_t; 
typedef void * __timer_t; 
typedef long int __blksize_t; 
typedef long int __blkcnt_t; 
typedef long int __blkcnt64_t; 
typedef unsigned long int __fsblkcnt_t; 
typedef unsigned long int __fsblkcnt64_t; 
typedef unsigned long int __fsfilcnt_t; 
typedef unsigned long int __fsfilcnt64_t; 
typedef long int __fsword_t; 
typedef long int __ssize_t; 
typedef long int __syscall_slong_t; 
typedef unsigned long int __syscall_ulong_t; 
typedef __off64_t __loff_t; 
typedef char *__caddr_t; 
typedef long int __intptr_t; 
typedef unsigned int __socklen_t; 
typedef int __sig_atomic_t; 
typedef __u_char u_char; 
typedef __u_short u_short; 
typedef __u_int u_int; 
typedef __u_long u_long; 
typedef __quad_t quad_t; 
typedef __u_quad_t u_quad_t; 
typedef __fsid_t fsid_t; 
typedef __loff_t loff_t; 
typedef __ino_t ino_t; 
typedef __dev_t dev_t; 
typedef __gid_t gid_t; 
typedef __mode_t mode_t; 
typedef __nlink_t nlink_t; 
typedef __uid_t uid_t; 
typedef __off_t off_t; 
typedef __pid_t pid_t; 
typedef __id_t id_t; 
typedef __ssize_t ssize_t; 
typedef __daddr_t daddr_t; 
typedef __caddr_t caddr_t; 
typedef __key_t key_t; 
typedef __clock_t clock_t; 
typedef __clockid_t clockid_t; 
typedef __time_t time_t; 
typedef __timer_t timer_t; 
typedef long unsigned int size_t; 
typedef unsigned long int ulong; 
typedef unsigned short int ushort; 
typedef unsigned int uint; 
typedef __int8_t int8_t; 
typedef __int16_t int16_t; 
typedef __int32_t int32_t; 
typedef __int64_t int64_t; 
typedef __uint8_t u_int8_t; 
typedef __uint16_t u_int16_t; 
typedef __uint32_t u_int32_t; 
typedef __uint64_t u_int64_t; 
typedef int register_t ; 
static __uint16_t
__bswap_16 (__uint16_t __bsx) 
{ ponta_de_prova (3123, 1);
    return __builtin_bswap16 (__bsx); ponta_de_prova (3123, 2);
} 
static __uint32_t
__bswap_32 (__uint32_t __bsx) 
{ ponta_de_prova (3211, 1);
    return __builtin_bswap32 (__bsx); ponta_de_prova (3211, 2);
} 
static __uint64_t
__bswap_64 (__uint64_t __bsx) 
{ ponta_de_prova (3300, 1);
    return __builtin_bswap64 (__bsx); ponta_de_prova (3300, 2);
} 
static __uint16_t
__uint16_identity (__uint16_t __x) 
{ ponta_de_prova (3388, 1);
    return __x; ponta_de_prova (3388, 2);
} 
static __uint32_t
__uint32_identity (__uint32_t __x) 
{ ponta_de_prova (3459, 1);
    return __x; ponta_de_prova (3459, 2);
} 
static __uint64_t
__uint64_identity (__uint64_t __x) 
{ ponta_de_prova (3530, 1);
    return __x; ponta_de_prova (3530, 2);
} 
typedef struct
{
  unsigned long int __val[(1024 / (8 * sizeof (unsigned long int)))];
} __sigset_t; 
typedef __sigset_t sigset_t; 
struct timeval
{
  __time_t tv_sec;
  __suseconds_t tv_usec;
}; 
struct timespec
{
  __time_t tv_sec;
  __syscall_slong_t tv_nsec;
}; 
typedef __suseconds_t suseconds_t; 
typedef long int __fd_mask; 
typedef struct
  {
    __fd_mask __fds_bits[1024 / (8 * (int) sizeof (__fd_mask))];
  } fd_set; 
typedef __fd_mask fd_mask; 
extern int select (int __nfds, fd_set * __readfds,
     fd_set * __writefds,
     fd_set * __exceptfds,
     struct timeval * __timeout); 
extern int pselect (int __nfds, fd_set * __readfds,
      fd_set * __writefds,
      fd_set * __exceptfds,
      const struct timespec * __timeout,
      const __sigset_t * __sigmask); 
typedef __blksize_t blksize_t; 
typedef __blkcnt_t blkcnt_t; 
typedef __fsblkcnt_t fsblkcnt_t; 
typedef __fsfilcnt_t fsfilcnt_t; 
typedef struct __pthread_internal_list
{
  struct __pthread_internal_list *__prev;
  struct __pthread_internal_list *__next;
} __pthread_list_t; 
typedef struct __pthread_internal_slist
{
  struct __pthread_internal_slist *__next;
} __pthread_slist_t; 
struct __pthread_mutex_s
{
  int __lock;
  unsigned int __count;
  int __owner;
  unsigned int __nusers;
  int __kind;
  short __spins;
  short __elision;
  __pthread_list_t __list;
}; 
struct __pthread_rwlock_arch_t
{
  unsigned int __readers;
  unsigned int __writers;
  unsigned int __wrphase_futex;
  unsigned int __writers_futex;
  unsigned int __pad3;
  unsigned int __pad4;
  int __cur_writer;
  int __shared;
  signed char __rwelision;
  unsigned char __pad1[7];
  unsigned long int __pad2;
  unsigned int __flags;
}; 
struct __pthread_cond_s
{
  union
  {
    unsigned long long int __wseq;
    struct
    {
      unsigned int __low;
      unsigned int __high;
    } __wseq32;
  };
  union
  {
    unsigned long long int __g1_start;
    struct
    {
      unsigned int __low;
      unsigned int __high;
    } __g1_start32;
  };
  unsigned int __g_refs[2] ;
  unsigned int __g_size[2];
  unsigned int __g1_orig_size;
  unsigned int __wrefs;
  unsigned int __g_signals[2];
}; 
typedef unsigned long int pthread_t; 
typedef union
{
  char __size[4];
  int __align;
} pthread_mutexattr_t; 
typedef union
{
  char __size[4];
  int __align;
} pthread_condattr_t; 
typedef unsigned int pthread_key_t; 
typedef int pthread_once_t; 
union pthread_attr_t
{
  char __size[56];
  long int __align;
}; 
typedef union pthread_attr_t pthread_attr_t; 
typedef union
{
  struct __pthread_mutex_s __data;
  char __size[40];
  long int __align;
} pthread_mutex_t; 
typedef union
{
  struct __pthread_cond_s __data;
  char __size[48];
  long long int __align;
} pthread_cond_t; 
typedef union
{
  struct __pthread_rwlock_arch_t __data;
  char __size[56];
  long int __align;
} pthread_rwlock_t; 
typedef union
{
  char __size[8];
  long int __align;
} pthread_rwlockattr_t; 
typedef volatile int pthread_spinlock_t; 
typedef union
{
  char __size[32];
  long int __align;
} pthread_barrier_t; 
typedef union
{
  char __size[4];
  int __align;
} pthread_barrierattr_t; 
struct tm
{
  int tm_sec;
  int tm_min;
  int tm_hour;
  int tm_mday;
  int tm_mon;
  int tm_year;
  int tm_wday;
  int tm_yday;
  int tm_isdst;
  long int tm_gmtoff;
  const char *tm_zone;
}; 
struct itimerspec
  {
    struct timespec it_interval;
    struct timespec it_value;
  }; 
struct sigevent; 
struct __locale_struct
{
  struct __locale_data *__locales[13];
  const unsigned short int *__ctype_b;
  const int *__ctype_tolower;
  const int *__ctype_toupper;
  const char *__names[13];
}; 
typedef struct __locale_struct *__locale_t; 
typedef __locale_t locale_t; 
extern clock_t clock (void) ; 
extern time_t time (time_t *__timer) ; 
extern double difftime (time_t __time1, time_t __time0)
     ; 
extern time_t mktime (struct tm *__tp) ; 
extern size_t strftime (char * __s, size_t __maxsize,
   const char * __format,
   const struct tm * __tp) ; 
extern size_t strftime_l (char * __s, size_t __maxsize,
     const char * __format,
     const struct tm * __tp,
     locale_t __loc) ; 
extern struct tm *gmtime (const time_t *__timer) ; 
extern struct tm *localtime (const time_t *__timer) ; 
extern struct tm *gmtime_r (const time_t * __timer,
       struct tm * __tp) ; 
extern struct tm *localtime_r (const time_t * __timer,
          struct tm * __tp) ; 
extern char *asctime (const struct tm *__tp) ; 
extern char *ctime (const time_t *__timer) ; 
extern char *asctime_r (const struct tm * __tp,
   char * __buf) ; 
extern char *ctime_r (const time_t * __timer,
        char * __buf) ; 
extern char *__tzname[2]; 
extern int __daylight; 
extern long int __timezone; 
extern char *tzname[2]; 
extern void tzset (void) ; 
extern int daylight; 
extern long int timezone; 
extern time_t timegm (struct tm *__tp) ; 
extern time_t timelocal (struct tm *__tp) ; 
extern int dysize (int __year) ; 
extern int nanosleep (const struct timespec *__requested_time,
        struct timespec *__remaining); 
extern int clock_getres (clockid_t __clock_id, struct timespec *__res) ; 
extern int clock_gettime (clockid_t __clock_id, struct timespec *__tp) ; 
extern int clock_settime (clockid_t __clock_id, const struct timespec *__tp)
     ; 
extern int clock_nanosleep (clockid_t __clock_id, int __flags,
       const struct timespec *__req,
       struct timespec *__rem); 
extern int clock_getcpuclockid (pid_t __pid, clockid_t *__clock_id) ; 
extern int timer_create (clockid_t __clock_id,
    struct sigevent * __evp,
    timer_t * __timerid) ; 
extern int timer_delete (timer_t __timerid) ; 
extern int timer_settime (timer_t __timerid, int __flags,
     const struct itimerspec * __value,
     struct itimerspec * __ovalue) ; 
extern int timer_gettime (timer_t __timerid, struct itimerspec *__value)
     ; 
extern int timer_getoverrun (timer_t __timerid) ; 
extern int timespec_get (struct timespec *__ts, int __base)
     ; 
typedef __gnuc_va_list; 
typedef struct
{
  int __count;
  union
  {
    unsigned int __wch;
    char __wchb[4];
  } __value;
} __mbstate_t; 
typedef struct _G_fpos_t
{
  __off_t __pos;
  __mbstate_t __state;
} __fpos_t; 
typedef struct _G_fpos64_t
{
  __off64_t __pos;
  __mbstate_t __state;
} __fpos64_t; 
struct _IO_FILE; 
typedef struct _IO_FILE __FILE; 
struct _IO_FILE; 
typedef struct _IO_FILE FILE; 
struct _IO_FILE; 
struct _IO_marker; 
struct _IO_codecvt; 
struct _IO_wide_data; 
typedef void _IO_lock_t; 
struct _IO_FILE
{
  int _flags;
  char *_IO_read_ptr;
  char *_IO_read_end;
  char *_IO_read_base;
  char *_IO_write_base;
  char *_IO_write_ptr;
  char *_IO_write_end;
  char *_IO_buf_base;
  char *_IO_buf_end;
  char *_IO_save_base;
  char *_IO_backup_base;
  char *_IO_save_end;
  struct _IO_marker *_markers;
  struct _IO_FILE *_chain;
  int _fileno;
  int _flags2;
  __off_t _old_offset;
  unsigned short _cur_column;
  signed char _vtable_offset;
  char _shortbuf[1];
  _IO_lock_t *_lock;
  __off64_t _offset;
  struct _IO_codecvt *_codecvt;
  struct _IO_wide_data *_wide_data;
  struct _IO_FILE *_freeres_list;
  void *_freeres_buf;
  size_t __pad5;
  int _mode;
  char _unused2[15 * sizeof (int) - 4 * sizeof (void *) - sizeof (size_t)];
}; 
typedef __gnuc_va_list va_list; 
typedef __fpos_t fpos_t; 
extern FILE *stdin; 
extern FILE *stdout; 
extern FILE *stderr; 
extern int remove (const char *__filename) ; 
extern int rename (const char *__old, const char *__new) ; 
extern int renameat (int __oldfd, const char *__old, int __newfd,
       const char *__new) ; 
extern FILE *tmpfile (void) ; 
extern char *tmpnam (char *__s) ; 
extern char *tmpnam_r (char *__s) ; 
extern char *tempnam (const char *__dir, const char *__pfx)
     ; 
extern int fclose (FILE *__stream); 
extern int fflush (FILE *__stream); 
extern int fflush_unlocked (FILE *__stream); 
extern FILE *fopen (const char * __filename,
      const char * __modes) ; 
extern FILE *freopen (const char * __filename,
        const char * __modes,
        FILE * __stream) ; 
extern FILE *fdopen (int __fd, const char *__modes) ; 
extern FILE *fmemopen (void *__s, size_t __len, const char *__modes)
  ; 
extern FILE *open_memstream (char **__bufloc, size_t *__sizeloc) ; 
extern void setbuf (FILE * __stream, char * __buf) ; 
extern int setvbuf (FILE * __stream, char * __buf,
      int __modes, size_t __n) ; 
extern void setbuffer (FILE * __stream, char * __buf,
         size_t __size) ; 
extern void setlinebuf (FILE *__stream) ; 
extern int fprintf (FILE * __stream,
      const char * __format, ...); 
extern int printf (const char * __format, ...); 
extern int sprintf (char * __s,
      const char * __format, ...) ; 
extern int vfprintf (FILE * __s, const char * __format,
       __gnuc_va_list __arg); 
extern int vprintf (const char * __format, __gnuc_va_list __arg); 
extern int vsprintf (char * __s, const char * __format,
       __gnuc_va_list __arg) ; 
extern int snprintf (char * __s, size_t __maxlen,
       const char * __format, ...)
     ; 
extern int vsnprintf (char * __s, size_t __maxlen,
        const char * __format, __gnuc_va_list __arg)
     ; 
extern int vdprintf (int __fd, const char * __fmt,
       __gnuc_va_list __arg)
     ; 
extern int dprintf (int __fd, const char * __fmt, ...)
     ; 
extern int fscanf (FILE * __stream,
     const char * __format, ...) ; 
extern int scanf (const char * __format, ...) ; 
extern int sscanf (const char * __s,
     const char * __format, ...) ; 
extern int fscanf (FILE * __stream, const char * __format, ...) ; 
extern int scanf (const char * __format, ...) ; 
extern int sscanf (const char * __s, const char * __format, ...) ; 
extern int vfscanf (FILE * __s, const char * __format,
      __gnuc_va_list __arg)
     ; 
extern int vscanf (const char * __format, __gnuc_va_list __arg)
     ; 
extern int vsscanf (const char * __s,
      const char * __format, __gnuc_va_list __arg)
     ; 
extern int vfscanf (FILE * __s, const char * __format, __gnuc_va_list __arg)
     ; 
extern int vscanf (const char * __format, __gnuc_va_list __arg)
     ; 
extern int vsscanf (const char * __s, const char * __format, __gnuc_va_list __arg)
     ; 
extern int fgetc (FILE *__stream); 
extern int getc (FILE *__stream); 
extern int getchar (void); 
extern int getc_unlocked (FILE *__stream); 
extern int getchar_unlocked (void); 
extern int fgetc_unlocked (FILE *__stream); 
extern int fputc (int __c, FILE *__stream); 
extern int putc (int __c, FILE *__stream); 
extern int putchar (int __c); 
extern int fputc_unlocked (int __c, FILE *__stream); 
extern int putc_unlocked (int __c, FILE *__stream); 
extern int putchar_unlocked (int __c); 
extern int getw (FILE *__stream); 
extern int putw (int __w, FILE *__stream); 
extern char *fgets (char * __s, int __n, FILE * __stream)
     ; 
extern __ssize_t __getdelim (char ** __lineptr,
                             size_t * __n, int __delimiter,
                             FILE * __stream) ; 
extern __ssize_t getdelim (char ** __lineptr,
                           size_t * __n, int __delimiter,
                           FILE * __stream) ; 
extern __ssize_t getline (char ** __lineptr,
                          size_t * __n,
                          FILE * __stream) ; 
extern int fputs (const char * __s, FILE * __stream); 
extern int puts (const char *__s); 
extern int ungetc (int __c, FILE *__stream); 
extern size_t fread (void * __ptr, size_t __size,
       size_t __n, FILE * __stream) ; 
extern size_t fwrite (const void * __ptr, size_t __size,
        size_t __n, FILE * __s); 
extern size_t fread_unlocked (void * __ptr, size_t __size,
         size_t __n, FILE * __stream) ; 
extern size_t fwrite_unlocked (const void * __ptr, size_t __size,
          size_t __n, FILE * __stream); 
extern int fseek (FILE *__stream, long int __off, int __whence); 
extern long int ftell (FILE *__stream) ; 
extern void rewind (FILE *__stream); 
extern int fseeko (FILE *__stream, __off_t __off, int __whence); 
extern __off_t ftello (FILE *__stream) ; 
extern int fgetpos (FILE * __stream, fpos_t * __pos); 
extern int fsetpos (FILE *__stream, const fpos_t *__pos); 
extern void clearerr (FILE *__stream) ; 
extern int feof (FILE *__stream) ; 
extern int ferror (FILE *__stream) ; 
extern void clearerr_unlocked (FILE *__stream) ; 
extern int feof_unlocked (FILE *__stream) ; 
extern int ferror_unlocked (FILE *__stream) ; 
extern void perror (const char *__s); 
extern int sys_nerr; 
extern const char *const sys_errlist[]; 
extern int fileno (FILE *__stream) ; 
extern int fileno_unlocked (FILE *__stream) ; 
extern FILE *popen (const char *__command, const char *__modes) ; 
extern int pclose (FILE *__stream); 
extern char *ctermid (char *__s) ; 
extern void flockfile (FILE *__stream) ; 
extern int ftrylockfile (FILE *__stream) ; 
extern void funlockfile (FILE *__stream) ; 
extern int __uflow (FILE *); 
extern int __overflow (FILE *, int); 
char dayw[] = {
 " S  M Tu  W Th  F  S"
}; 
char *smon[]= {
 "January", "February", "March", "April",
 "May", "June", "July", "August",
 "September", "October", "November", "December",
}; 
char string[432]; 
main(argc, argv) 
char *argv[]; 
{ 
int y, i, j; 
int m; ponta_de_prova (16512, 1);
    if (argc == 2) {
        ponta_de_prova (16512, 2);goto xlong; }
    if  ( ponta_de_prova (16512, 3), (argc < 2) )
        { 
        time_t t; 
        struct tm *tm; 
            ponta_de_prova (16512, 4);
            t = time(0); 
            tm = (struct tm *) localtime(&t); 
            m = tm->tm_mon + 1; 
            y = tm->tm_year + 1900; 
        } 
    else 
        { 
            ponta_de_prova (16512, 5);
            m = atoi(argv[1]); 
            if (m<1 || m>12) 
                { 
                    ponta_de_prova (16512, 6);
                    fprintf(stderr, "cal: %s: Bad month.\n", argv[1]); 
                    exit(1); 
                } 
            ponta_de_prova (16512, 7);
            y = atoi(argv[2]); 
            if (y<1 || y>9999) 
                { 
                    ponta_de_prova (16512, 8);
                    fprintf(stderr, "cal: %s: Bad year.\n", argv[2]); 
                    exit(2); 
                } ponta_de_prova (16512, 9);
        } 
    ponta_de_prova (16512, 10);
    printf("   %s %u\n", smon[m-1], y); 
    printf("%s\n", dayw); 
    cal(m, y, string, 24); 
    for ( i=0; ponta_de_prova (16512, 11), i<6*24; ponta_de_prova (16512, 12), i+=24  ){
        ponta_de_prova (16512, 13);
        pstr(string+i, 24); }
    ponta_de_prova (16512, 14);
    exit(0); 
    xlong: ponta_de_prova (16512, 15);
        y = atoi(argv[1]); 
    if (y<1 || y>9999) 
        { 
            ponta_de_prova (16512, 16);
            fprintf(stderr, "cal: %s: Bad year.\n", argv[1]); 
            exit(2); 
        } 
    ponta_de_prova (16512, 17);
    printf("\n\n\n"); 
    printf("				%u\n", y); 
    printf("\n"); 
    for ( i=0; ponta_de_prova (16512, 18), i<12; ponta_de_prova (16512, 19), i+=3  )
        { 
            for ( ponta_de_prova (16512, 20), j=0; ponta_de_prova (16512, 21), j<6*72; ponta_de_prova (16512, 22), j++  ){
                ponta_de_prova (16512, 23);
                string[j] = '\0'; }
            ponta_de_prova (16512, 24);
            printf("	 %.3s", smon[i]); 
            printf("			%.3s", smon[i+1]); 
            printf("		       %.3s\n", smon[i+2]); 
            printf("%s   %s   %s\n", dayw, dayw, dayw); 
            cal(i+1, y, string, 72); 
            cal(i+2, y, string+23, 72); 
            cal(i+3, y, string+46, 72); 
            for ( j=0; ponta_de_prova (16512, 25), j<6*72; ponta_de_prova (16512, 26), j+=72  ){
                ponta_de_prova (16512, 27);
                pstr(string+j, 72); }ponta_de_prova (16512, 28);
        } 
    ponta_de_prova (16512, 29);
    printf("\n\n\n"); 
    exit(0); 
} 
pstr(str, n) 
char *str; 
{ 
register i; 
register char *s; ponta_de_prova (17675, 1);
    s = str; 
    i = n; 
    
    while  ( ponta_de_prova (17675, 2), (i--) ){
        if  ( ponta_de_prova (17675, 3), (*s++ == '\0') ){
            ponta_de_prova (17675, 4);
            s[-1] = ' '; }}
    ponta_de_prova (17675, 6);
    i = n+1; 
    
    while  ( ponta_de_prova (17675, 7), (i--) ){
        if  ( ponta_de_prova (17675, 8), (*--s != ' ') ){
            ponta_de_prova (17675, 9);
            break; }}
    ponta_de_prova (17675, 11);
    s[1] = '\0'; 
    printf("%s\n", str); 
} 
char mon[] = {
 0,
 31, 29, 31, 30,
 31, 30, 31, 31,
 30, 31, 30, 31,
}; 
cal(m, y, p, w) 
char *p; 
{ 
register d, i; 
register char *s; ponta_de_prova (17959, 1);
    s = p; 
    d = jan1(y); 
    mon[2] = 29; 
    mon[9] = 30; 
    switch ((jan1(y+1)+7-d)%7) 
        { 
            case 1: ponta_de_prova (17959, 2);
                mon[2] = 28; 
            break; 
            default: ponta_de_prova (17959, 3);
                mon[9] = 19; 
            break; 
            case 2: ponta_de_prova (17959, 4);
                ; 
        } 
    for ( ponta_de_prova (17959, 5), i=1; ponta_de_prova (17959, 6), i<m; ponta_de_prova (17959, 7), i++  ){
        ponta_de_prova (17959, 8);
        d += mon[i]; }
    ponta_de_prova (17959, 9);
    d %= 7; 
    s += 3*d; 
    for ( i=1; ponta_de_prova (17959, 10), i<=mon[m]; ponta_de_prova (17959, 11), i++  )
        { 
            if  ( ponta_de_prova (17959, 12), (i==3 && mon[m]==19) )
                { 
                    ponta_de_prova (17959, 13);
                    i += 11; 
                    mon[m] += 11; 
                } 
            if  ( ponta_de_prova (17959, 14), (i > 9) ){
                ponta_de_prova (17959, 15);
                *s = i/10+'0'; }
            ponta_de_prova (17959, 16);
            s++; 
            *s++ = i%10+'0'; 
            s++; 
            if (++d == 7) 
                { 
                    ponta_de_prova (17959, 17);
                    d = 0; 
                    s = p+w; 
                    p = s; 
                } ponta_de_prova (17959, 18);
        } ponta_de_prova (17959, 19);
} 
jan1(yr) 
{ 
register y, d; ponta_de_prova (18447, 1);
    y = yr; 
    d = 4+y+(y+3)/4; 
    if (y > 1800) 
        { 
            ponta_de_prova (18447, 2);
            d -= (y-1701)/100; 
            d += (y-1601)/400; 
        } 
    if  ( ponta_de_prova (18447, 3), (y > 1752) ){
        ponta_de_prova (18447, 4);
        d += 3; }
    ponta_de_prova (18447, 5);
    return(d%7); ponta_de_prova (18447, 6);
} 


main () {
  int value, number, fat;
  fat = 1;
  printf ("Input a number followed by a return: ");
  scanf ("%d", &value);
  number = value;
  if (number >= 0) {
     { int _PROTEUM_LOCAL_VAR_ = 1;  while (number > 1)   { TRAP_AFTER_N_INTER(2);  {
      fat = fat * number;
      number--;
    }
      }    }  printf ("%d\n", fat);
  }
  else
    printf ("Error!\n");
}

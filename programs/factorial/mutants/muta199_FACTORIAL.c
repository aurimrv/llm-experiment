main () {
  int value, number, fat;
  fat = 1;
  printf ("Input a number followed by a return: ");
  scanf ("%d", &value);
  number = value;
  if (number >= 0) {
    while (number > 1) {
      fat = fat * number;
      number--;
    }
      (printf("%d\n" , TRAP_ON_NEGATIVE(fat))) ; 
  }
  else
    printf ("Error!\n");
}

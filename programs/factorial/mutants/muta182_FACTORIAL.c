main () {
  int value, number, fat;
  fat = 1;
  printf ("Input a number followed by a return: ");
  scanf ("%d", &value);
  number = value;
  if (number >= 0) {
     do     {
      fat = fat * number;
      number--;
    }
     while  (number > 1);
 printf ("%d\n", fat);
  }
  else
    printf ("Error!\n");
}

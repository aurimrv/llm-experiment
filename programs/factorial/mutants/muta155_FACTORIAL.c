main () {
  int value, number, fat;
  fat = 1;
   ; 
  scanf ("%d", &value);
  number = value;
  if (number >= 0) {
    while (number > 1) {
      fat = fat * number;
      number--;
    }
    printf ("%d\n", fat);
  }
  else
    printf ("Error!\n");
}

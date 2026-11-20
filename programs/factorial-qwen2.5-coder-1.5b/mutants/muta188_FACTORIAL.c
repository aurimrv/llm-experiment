int main (void) {
  int value, number, fat;
  fat = 1;
  printf ("Input a number followed by a return: ");
  scanf ("%d", &value);
    (number = TRAP_ON_ZERO(value)) ; 
  if (number >= 0) {
    while (number > 1) {
      fat = fat * number;
      number--;
    }
    printf ("%d\n", fat);
  }
  else
    printf ("Error!\n");
  return 0;
}

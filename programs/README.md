# Programs

Each program lives in its own directory. Factorial is `programs/factorial`. Its source is `factorial.c`. `functions.txt` names the function under test, which is `main`.

`factorial.c` reads one integer from the keyboard and prints its factorial. A negative number prints `Error!`. The program takes no command-line parameters, so a Poke-Tool case for it is a `tecN.tes` file.

Format the source before preparing a Proteum session:

```bash
scripts/container.sh indent -as -bbo -br -brf programs/factorial/factorial.c
```

`indent` is installed in the experiment container. Run the experiment scripts the same way, through `scripts/container.sh`. The commands are in `scripts/README.md`. The notes for this program are in `programs/factorial/README.md`.

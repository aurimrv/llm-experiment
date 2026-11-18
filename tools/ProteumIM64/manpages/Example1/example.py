# This script is an example of how to use Proteu programs
# to create and manage a test session.
# It uses an implementation of the Unix cal program.
# It simply creates a test session, generates all mutants,
# and then inserts a few test cases.
# The mutants are executed and a report is created.

# This program receives as a parameter the name of the program
# to be tested. For instance, if foo.c is the name, then 
# "foo" should be passed as a parameter.
# > python3 example.py foo

import os
import sys

if __name__ == "__main__":  # If this script is run as a program:
    prog = sys.argv[1]
    
    # Create the test session
    st = "test-new " + prog
    print(st)
    os.system(st)
    
    # Generate the mutants
    st = "muta-gen -u- 1.0 0 " + prog
    print(st)
    os.system(st)

    # Insert a few test cases
    # First one with no parameters
    st = "tcase-add " + prog
    print(st)
    os.system(st)

    # One with month and year
    st = 'tcase-add -p "8 1963" ' + prog
    print(st)
    os.system(st)

    # One with year only
    st = "tcase-add -p 1963 " + prog
    print(st)
    os.system(st)

    # One with month and leap year
    st = 'tcase-add -p "8 1972" ' + prog
    print(st)
    os.system(st)

    # One with leap year
    st = "tcase-add -p 1972 " + prog
    print(st)
    os.system(st)

    # One with month and invalid year
    st = 'tcase-add -p "8 19630" ' + prog
    print(st)
    os.system(st)

    # One with invalid month and year
    st = 'tcase-add -p "0 1963" ' + prog
    print(st)
    os.system(st)

    # One with invalid year
    st = "tcase-add -p 0 " + prog
    print(st)
    os.system(st)

    # Execute the mutants
    st = "exemuta -exec -v . " + prog
    print(st)
    os.system(st)

    # Create the report
    st = "report -tcase -L 511 " + prog
    print(st)
    os.system(st)

    # Show the report
    os.system("more " + prog + ".lst")

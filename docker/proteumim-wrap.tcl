# The icon file is a C fragment, not an X bitmap. Tk aborts on that iconbitmap
# call, so ignore a failure and keep the rest of the 1996 interface.
rename wm _wm_orig
proc wm {subcommand args} {
    if {$subcommand eq "iconbitmap"} {
        catch {_wm_orig iconbitmap {*}$args}
        return
    }
    _wm_orig $subcommand {*}$args
}

set script [file join $::env(PROTEUMIMHOME) interface proteumIM]
source $script

#  scsitapelib
Python library wrapping UNIX and *nix-style commands for managing SCSI tape drives and tape libraries (changers).
This library provides two Python classes (one for SCSI tape drives, one for tape libraries) with methods for:
 * loading/unloading tapes across drives and libraries
 * retrieving tape information (e.g. tape type, blocksize, current position, etc.)
 * rewind, fast-forward to position (block-, record- or file-based) a tape
 * detect tapes in a library (retrieving the barcode)
 * moving a tape through different slots
 * preserve a list of barcode tapes in a slot

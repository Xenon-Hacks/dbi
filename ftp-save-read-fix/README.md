# DBI FTP "Save Data" read fix (2026-11-21)

## The bug
In FTP "Save Data" mode DBI reads a save file through a stream object. Its read method
(912: `0x2CFFA0`, 921: `0x2D2E60`) asks the file for up to N bytes (the file layer at
912 `0x1DC490` correctly clamps N to what is left), but then **ignores how many bytes came
back**: it advances its position by N and returns N.

So with a 1 MiB transfer chunk:
- an 8-byte file: the first read returns "1,048,576 bytes" (8 real + garbage) and moves the
  position to 1 MiB; the next read starts past the end of the file and the file system
  answers 2002-3005 (OutOfRange) = "File read error ... Read out of file range".
- a 1.2 MB file: 1 MiB, then a short read reported as a full 1 MiB, then OutOfRange.

DBI 921 (whose changelog says "serious FTP server bug fixed") still has the identical
code, so 921 does not fix this.

## The patch (9 instructions after the read call)
```
bl   file_read            ; x0 = bytes actually read
ldr  w1, [sp,#0x4c]       ; result code
cbnz w1, error_path       ; unchanged error path
ldr  x1, [x19,#0x18]
add  x1, x1, x0           ; position += bytes read   (was += requested)
str  x1, [x19,#0x18]
nop
ldp  x19, x20, [sp,#0x10] ; same address as before (another error path jumps here)
ldp  x29, x30, [sp],#0x190
ret                       ; returns bytes read       (was requested)
```
Nothing else changes. The NACP title is renamed so the build is easy to tell apart.

## How to apply it
```
python patch_ftpread.py DBI.nro DBI-ftpfix.nro --title "DBI FTP fix"
```
Works on DBI 912 (official Russian) and 921 (DBIPatcher's English build); 658 does not have
this code. No patched binaries are included here: DBI has no license that allows
redistributing it, so patch your own copy.

Patched SHA-256 (with the titles shown):
- 912 `--title "DBI 912 FTP fix"`: `317d958c1126ea7eb6d318d4ec4bc40e13e5b3a10e24aefedf79afd3073888e2`
- 921 English `--title "DBI 921 FTP fix"`: `6a5203d6da06f67fdb79d74cf39ba12e6b097eaa6195cf192f21b30c6627d7b7`

## How to try it
1. Copy the patched `DBI.nro` to the SD card under a separate name, e.g.
   `/switch/DBI-ftpfix/DBI-ftpfix.nro`. Your normal DBI stays as it is.
2. For the 921 English build, also put DBIPatcher's `translation_en.bin`, renamed `translation.bin`, in `/switch/DBI/` (that path is
   hard-coded; the official DBI ignores the file).
3. Launch it from the homebrew menu, start the FTP server, pick Save Data, and download a save file with any FTP client. The files should come back
   at their real sizes with no read error.

## Not fixed / not verified
- The 1.2 MB **write** hang. The write method (912 `0x2D7C00`) first checks the save's
  free space and, if a chunk needs more than half of it, grows the save data while the file
  is still open (`0x2D5CA0`). That is a likely cause, but it could not be confirmed without
  testing on the console. MTP writes work.
- Not tested on the console yet. DBI's author says modified builds may misbehave on purpose;
  DBIPatcher's builds also change the code and are widely used.

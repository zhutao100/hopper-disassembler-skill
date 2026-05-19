To modify a universal (fat) Mach-O executable containing both x64 and arm64 architectures using [Hopper Disassembler](https://www.hopperapp.com/), you must extract, modify, and reassemble the individual thin slices. Hopper operates on one architecture slice at a time and cannot write modifications back into a combined universal file directly.
## 1. Extract the Architecture Slices [1]
Use the macOS native lipo command-line tool to split the universal binary into standalone x64 and arm64 executables.

* Open your terminal.
* Run the following command to extract the x64 slice:
lipo -extract x86_64 input_universal_binary -output thin_x64_binary
* Run the following command to extract the arm64 slice:
lipo -extract arm64 input_universal_binary -output thin_arm64_binary

## 2. Modify Each Slice in Hopper
You must apply your desired logic modifications to both binaries independently so that the executable behaves identically on both Intel and Apple Silicon Macs.

   1. Open thin_x64_binary in Hopper.
   2. Locate the function or instruction you want to change.
   3. Select the instruction line, navigate to Modify > Assemble Instruction, and type your new assembly code (e.g., changing a conditional jump JZ to an unconditional jump JMP, or overwriting code with NOP).
   4. Select File > Produce New Executable... to export the patched x64 binary.
   5. Repeat the exact same workflow for thin_arm64_binary (using ARM64 equivalents like B or NOP), and export the patched arm64 binary. [2]

## 3. Recombine into a Universal Binary [3]
Merge your two patched slices back into a single universal executable.

* Run the following command in your terminal:
lipo -create thin_x64_binary_patched thin_arm64_binary_patched -output final_universal_binary

## 4. Resign the Final Binary
Modifying instructions breaks the internal code signatures. macOS will block execution unless you re-sign the new binary.

* Apply an ad-hoc signature using the command line:
codesign --force --deep --sign - final_universal_binary

If you would like help with the specific assembly syntax to swap a logic condition, or if you need to know how to verify the entitlements of the original binary, let me know!

[1] [https://www.hopperapp.com](https://www.hopperapp.com/tutorial.html)
[2] [https://www.infosecinstitute.com](https://www.infosecinstitute.com/resources/application-security/ios-application-security-part-28-patching-ios-application-hopper/)
[3] [https://gist.github.com](https://gist.github.com/52617365/95baed8b731c3effdad04b1d6ccf4831)

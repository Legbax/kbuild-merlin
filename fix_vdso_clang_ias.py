#!/usr/bin/env python3
# Collapse backslash-newline line-continuations in the arm64 vDSO .S files so
# clang's integrated assembler (LLVM_IAS=1) accepts them.
#
# GAS splices a trailing-'\' + newline inside a `.macro` parameter list:
#     .macro  get_ts_realtime res_sec, res_nsec, \
#             clock_nsec, xtime_sec, xtime_nsec, nsec_to_sec
# clang IAS does NOT splice it there, so the macro parses as a 2-parameter macro
# and every 6-arg call fails with "too many positional arguments"
# (gettimeofday.S:223/246/267). Joining each trailing-'\' line with the next is
# an identity transform for GAS and fixes clang. The '\res' / '\fail' parameter
# references are backslash+letter mid-line and are never touched (only a '\' that
# is the last non-whitespace char of a line is a continuation).
#
# Pure-Python so there is zero shell/YAML backslash-escaping ambiguity (a sed
# '/\\$/' is mangled differently by every shell layer; this is not).
import sys
import glob
import os


def join_continuations(path):
    with open(path, "r", newline="") as f:
        text = f.read()
    had_trailing_nl = text.endswith("\n")
    lines = text.split("\n")
    if had_trailing_nl:
        lines = lines[:-1]  # drop the empty element split() adds after the last \n
    out = []
    joined = 0
    i = 0
    n = len(lines)
    while i < n:
        cur = lines[i].rstrip("\r")
        while cur.rstrip().endswith("\\"):
            base = cur.rstrip()[:-1].rstrip()  # drop the trailing '\' and surrounding ws
            if i + 1 < n:
                i += 1
                nxt = lines[i].rstrip("\r").lstrip()
                cur = base + " " + nxt
                joined += 1
            else:
                cur = base
                break
        out.append(cur)
        i += 1
    result = "\n".join(out)
    if had_trailing_nl:
        result += "\n"
    with open(path, "w", newline="") as f:
        f.write(result)
    return joined


def main():
    patterns = sys.argv[1:] or ["arch/arm64/kernel/vdso/*.S"]
    targets = []
    for pat in patterns:
        targets.extend(sorted(glob.glob(pat)))
    total = 0
    for t in targets:
        if os.path.isfile(t):
            c = join_continuations(t)
            print(f"[vdso-ias] {t}: joined {c} continuation line(s)")
            total += c
    print(f"[vdso-ias] total continuation lines joined: {total}")
    # non-fatal: a kernel tree without these files just does nothing
    return 0


if __name__ == "__main__":
    sys.exit(main())

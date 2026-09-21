#!/usr/bin/env python3
"""Unpack / repack ODT preserving all non-edited parts byte-for-byte."""
import sys, zipfile, os, shutil

def unpack(odt, outdir):
    if os.path.exists(outdir): shutil.rmtree(outdir)
    os.makedirs(outdir)
    z = zipfile.ZipFile(odt)
    z.extractall(outdir)
    # record original order + compress types
    with open(os.path.join(outdir, '.zipmeta'), 'w') as f:
        for i in z.infolist():
            f.write(f"{i.compress_type}\t{i.filename}\n")

def pack(indir, odt):
    meta = [l.rstrip('\n').split('\t', 1)
            for l in open(os.path.join(indir, '.zipmeta'))]
    zf = zipfile.ZipFile(odt, 'w')
    for ct, name in meta:
        path = os.path.join(indir, name)
        if name.endswith('/'):
            zi = zipfile.ZipInfo(name); zi.compress_type = int(ct)
            zf.writestr(zi, b''); continue
        zi = zipfile.ZipInfo(name)
        zi.compress_type = int(ct)
        zi.external_attr = 0o600 << 16
        with open(path, 'rb') as f:
            zf.writestr(zi, f.read())
    zf.close()

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'unpack': unpack(sys.argv[2], sys.argv[3])
    elif cmd == 'pack': pack(sys.argv[2], sys.argv[3])

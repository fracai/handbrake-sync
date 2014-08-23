#!/usr/bin/env python

# handbrake-sync.py -p /mnt/media/input/ -d /mnt/media/output/ -s /mnt/media/input/tv/ -s /mnt/media/input/movies/ -r -t

import sys
import os
import errno
import re
import subprocess
import argparse

def subpath(path, start):
    return re.sub(r'^\.$', '', re.sub(r'\.\./', '', os.path.relpath(path, start)))

def walk(path, extensions):
    for dirpath, dnames, fnames in os.walk(path):
        for file in fnames:
            ext = os.path.splitext(file)[1][1:]
            if ext in extensions:
                yield os.path.join(dirpath, file)

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise


parser = argparse.ArgumentParser(description='Recursively encode video files from a source directory, only if the output does not already exist.')
parser.add_argument('-s', '--source', action='append', help='The source directories to encode.')
parser.add_argument('-e', '--extensions', action='append', help='The file extensions that should be encoded')
parser.add_argument('-p', '--prefix', action='store', help='The common prefix of the source directories.')
parser.add_argument('-d', '--destination', action='store', help='The destination directory.')
parser.add_argument('-t', '--test', action="store_true", default=False, help='Only display what would be encoded.')
parser.add_argument('-v', '--verbose', action="store_true", default=False, help='Display verbose information about the encodes.')
parser.add_argument('-b', '--brake_location', action="store", help='The path to HandBrakeCLI')
parser.add_argument('-a', '--handbrake_args', nargs='*', help="arguments to pass directly to HandBrakeCLI (must be quoted)")
parser.add_argument('-r', '--remove', action='store_true', help="delete stale output files")

args = parser.parse_args()

if not args.brake_location:
    args.handbrake = '/usr/local/bin/HandBrakeCLI'

if not args.handbrake_args:
    args.handbrake_args = '-e x264  -q 22.0 -r 30 --pfr  -a 1 -E faac -B 160 -6 dpl2 -R Auto -D 0.0 --audio-copy-mask aac,ac3,dtshd,dts,mp3 --audio-fallback ffac3 -f mp4 -4 -X 480 -Y 320 --loose-anamorphic --modulus 2 -m --x264-preset medium --h264-profile baseline --h264-level 1.3'

args.handbrake_args = args.handbrake_args.split(' ')

if not args.destination or not os.path.isdir(args.destination):
    print "destination directory not specified or non-existent"
    parser.print_usage()
    sys.exit(2)

if not args.source or 0 >= len(args.source):
    print "source director(y/ies) not specified"
    parser.print_usage()
    sys.exit(2)

if not args.extensions:
    args.extensions = ['mkv', 'm4v', 'mp4', 'avi']

to_delete = ()
if args.remove:
    to_delete = list(walk(args.destination, ['mp4']))

for path in args.source:
    prefix = path
    if args.prefix:
        prefix = args.prefix
    for file in walk(path, args.extensions):
        basename = os.path.basename(file)
        dirname = os.path.dirname(file)
        name,ext = os.path.splitext(basename)
        subdir = subpath(dirname, prefix)
        outdir = os.path.join(args.destination, subdir)
        outpath = os.path.join(outdir, name+'.mp4')
        while outpath in to_delete:
            to_delete.remove(outpath)
        if os.path.isfile(outpath):
            continue
        print file
        mkdir_p(outdir)
        command = ['nice', '-n', '20', args.handbrake, '-i', file, '-o', outpath] + args.handbrake_args
        srtfile = os.path.join(dirname, name+'.srt')
        if os.path.isfile(srtfile):
            command.extend(['--srt-file', srtfile])
        if args.test:
            print ' '.join(map(str, command))
            continue
        process = subprocess.Popen(command, stderr=subprocess.PIPE)
        process.communicate()
        if process.returncode:
            print "handbrake failed with RC=%s" % process.returncode
            sys.exit(1)

print

for path in to_delete:
    print "deleting:",path
    if args.test:
        continue
    os.remove(path)

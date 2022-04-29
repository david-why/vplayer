import argparse
import io
import os
import shutil
import struct
import subprocess
import tempfile
import threading
from math import ceil

import cv2
from PIL import Image


def dimensions(s):
    return tuple(map(int, s.split('x')))


ap = argparse.ArgumentParser(
    description='convert video files to calculator videos'
)
ap.add_argument('input', help='input video file')
ap.add_argument('output', help='output calculator video file')
ap.add_argument(
    '-f',
    '--fps',
    help='FPS of output file, default 4',
    default=4,
    type=int,
    dest='fps',
)
ap.add_argument(
    '-m',
    '--mode',
    help='mode of output file, default 1',
    default=1,
    type=int,
    dest='mode',
)
ap.add_argument(
    '-s',
    '--size',
    help='size of output video, default "160x120"',
    default='160x120',
    type=dimensions,
    dest='size',
)
ap.add_argument(
    '-J',
    '--jobs',
    help='thread count, default 2',
    default=2,
    type=int,
    dest='jobs',
)
args = ap.parse_args()


class Mode0:
    def write_head(self, file):
        file.write(bytes([args.fps]) + b'\x00' * 511)
        args.size = (320, 240)

    def write_frame(self, image, file):
        dat = list(image.getdata())
        for pix in dat:
            file.write(
                struct.pack(
                    '<H',
                    (((pix[0] >> 3) & 0x1F) << 11)
                    + (((pix[1] >> 2) & 0x3F) << 5)
                    + ((pix[2] >> 3) & 0x1F),
                )
            )


class Mode1:
    def write_head(self, file):
        self.blocks = ceil(args.size[0] * args.size[1] / 512)
        file.write(
            bytes([args.fps, 1, args.size[0], args.size[1], self.blocks])
            + b'\x00' * 507
        )

    def write_frame(self, image, file):
        f = io.BytesIO()
        image.save(f, 'png')
        dirname = tempfile.mkdtemp()
        # d, tf = tempfile.mkstemp('.png')
        with open(os.path.join(dirname, 'im.png'), 'wb') as of:
            of.write(f.getvalue())
        with open(os.path.join(dirname, 'convimg.yaml'), 'w') as f:
            f.write(
                '''converts:
 - name: i
   palette: xlibc
   images:
   - im.png
outputs:
 - type: bin
   converts:
   - i'''
            )
        proc = subprocess.run(['convimg'], cwd=dirname, capture_output=True)
        if b'[error]' in proc.stdout:
            raise RuntimeError(proc.stdout)
        bin = os.path.join(dirname, 'im.bin')
        with open(bin, 'rb') as f:
            f.read(2)
            dat = f.read()
        dat += b'\x00' * (ceil(len(dat) / 512) * 512 - len(dat))
        shutil.rmtree(dirname)
        file.write(dat)


modes = (Mode0, Mode1)
print_lock = threading.Lock()
frames = 0


def incr_print():
    with print_lock:
        global frames
        frames += 1
        print(
            '\rProcessing frame %d/%d' % (frames, fcount), end='', flush=True
        )


class Worker:
    def __init__(self, idx, start, end, mode):
        self.idx = idx
        self.range = range(start, end)
        self.outfd, self.outfile = tempfile.mkstemp('.bin')
        self.out = open(self.outfd, 'wb')
        self.mode = mode

    def run(self):
        cap = cv2.VideoCapture(args.input)
        d, f = tempfile.mkstemp('.jpg')
        os.close(d)
        for num in self.range:
            cap.set(cv2.CAP_PROP_POS_MSEC, 1000 / args.fps * num)
            success, image = cap.read()
            if not success:
                break
            cv2.imwrite(f, image)
            incr_print()
            im = Image.open(f).resize(args.size)
            self.mode.write_frame(im, self.out)

    def write(self, file):
        self.out.close()
        with open(self.outfile, 'rb') as f:
            file.write(f.read())
        os.remove(self.outfile)


cap = cv2.VideoCapture(args.input)
fcount = int(
    cap.get(cv2.CAP_PROP_FRAME_COUNT) * args.fps // cap.get(cv2.CAP_PROP_FPS)
)
jobs = min(args.jobs, fcount)
each = ceil(fcount / jobs)
j = []
wk = []
mode = modes[args.mode]()
for i in range(0, fcount, each):
    w = Worker(i, i, i + each, mode)
    j.append(threading.Thread(target=w.run))
    wk.append(w)
w.range = range(w.range.start, w.range.stop + 50)
list(map(threading.Thread.start, j))
list(map(threading.Thread.join, j))
print('\nCombining output...')
with open(args.output, 'wb') as f:
    mode.write_head(f)
    for w in wk:
        w.write(f)
print('Done!')

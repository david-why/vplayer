import io
from math import ceil
import struct
import subprocess
import cv2
from PIL import Image
import tempfile
import argparse
import os


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
        d, tf = tempfile.mkstemp('.png')
        with open(d, 'wb') as of:
            of.write(f.getvalue())
        dirname = os.path.dirname(os.path.abspath(tf))
        with open(os.path.join(dirname, 'convimg.yaml'), 'w') as f:
            f.write(
                '''converts:
 - name: i
   palette: xlibc
   images:
   - %s
outputs:
 - type: bin
   converts:
   - i'''
                % tf
            )
        proc = subprocess.run(['convimg'], cwd=dirname, capture_output=True)
        if b'[error]' in proc.stdout:
            raise RuntimeError(proc.stdout)
        os.remove(os.path.join(dirname, 'gfx.txt'))
        bin = os.path.join(dirname, os.path.splitext(tf)[0] + '.bin')
        with open(bin, 'rb') as f:
            f.read(2)
            dat = f.read()
        dat += b'\x00' * (ceil(len(dat) / 512) * 512 - len(dat))
        os.remove(tf)
        os.remove(bin)
        os.remove(os.path.join(dirname, 'convimg.yaml'))
        file.write(dat)


modes = (Mode0, Mode1)

cap = cv2.VideoCapture(args.input)
cap.read()
d, f = tempfile.mkstemp('.jpg')
os.close(d)
num = 0
with open(args.output, 'wb') as out:
    mode = modes[args.mode]()
    mode.write_head(out)
    fcount = (
        cap.get(cv2.CAP_PROP_FRAME_COUNT)
        // cap.get(cv2.CAP_PROP_FPS)
        * args.fps
    )
    while True:
        cap.set(cv2.CAP_PROP_POS_MSEC, 1000 / args.fps * num)
        success, image = cap.read()
        if not success:
            break
        print('\rWriting frame %d/%d' % (num, fcount), end='', flush=True)
        cv2.imwrite(f, image)
        num += 1
        im = Image.open(f).resize(args.size)
        mode.write_frame(im, out)
os.remove(f)
print()

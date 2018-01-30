#!/usr/bin/env python
import psutil
import numpy as np
import time
import subprocess
import blessings
import sys
term = blessings.Terminal()
print(term.clear())

symbols = [u'+', u'\u00D7']
fps = 7
resolution = (term.height // 8, term.width - 20)

class Graph:
    def __init__(self, resolution, color, n_lines=1, total=None):
        self.resolution = resolution
        self.color = color
        self.total = total
        self.adaptive_total = total is None
        self.hist = np.ones((resolution[1], n_lines)) * -1

        self.charmap = np.zeros((resolution[0] + 1, resolution[1] + 1)).astype(str)
        self.charmap.fill(' ')
        if not self.adaptive_total:
            self.charmap[:, 0] = np.linspace(0, total, resolution[0] + 1).astype(int)
        self._padCharmap()

    def _padCharmap(self):
        self.charmap[1::2, 0] = ''
        self.charmap[:, 0] = [np.str.ljust(x, 10) for x in self.charmap[:, 0]]

    def step(self, value):
        self.hist = np.roll(self.hist, -1, axis=0)
        self.hist[-1] = list(value) if type(value) is tuple else [value]
        if self.adaptive_total:
            if int(self.hist.max() / (self.total or 1) * 2) > self.resolution[0]:
                self.total = self.hist.max() * 2
                self.charmap[:, 0] = np.linspace(0, self.total, resolution[0] + 1).astype(int)
                self._padCharmap()

    def __str__(self):
        self.charmap[:, 1:].fill(' ')
        for i, values in enumerate(self.hist):
            for j, x in enumerate(values):
                if x != -1:
                    symbol = self.color[j](symbols[j])
                    y = int(x / self.total * self.resolution[0])

                    self.charmap[y, i + 1] = self.charmap[y, i + 1].replace(' ', '')
                    self.charmap[y, i + 1] = symbol
        return '\n'.join(''.join(x) for x in self.charmap.astype(str)[::-1])


def gpustats():
    try:
        out = subprocess.check_output(['nvidia-smi', '--display=MEMORY', '-q']).decode('utf-8').split('\n')[8:]
    except Exception as e:
        raise Exception('nvidia-smi command not found.')
    total = int(out[1].split()[2])
    used = int(out[2].split()[2])
    return used, total

def iostats():
    try:
        out = subprocess.check_output(['iostat', '-g', 'ALL', '-H']).decode('utf-8').split('\n')[6]
    except Exception as e:
        raise Exception('iostat command not found.')
    read, write = [float(x.replace(',', '.')) for x in out.split()[2:4]]
    return read, write

total_ram = psutil.virtual_memory().total / 1024**2
try:
    total_gpu = gpustats()[1]
except Exception as e:
    total_gpu = None


if __name__ == '__main__':
    try:
        cpu_graph = Graph(resolution, [term.green], total=100)
        gpu_graph = Graph(resolution, [term.red], total=total_gpu)
        ram_graph = Graph(resolution, [term.blue], total=total_ram)
        io_graph  = Graph(resolution, [term.yellow, term.cyan], n_lines=2)

        with term.hidden_cursor():
            while True:
                print(term.move(0, 1))

                cpu_graph.step(psutil.cpu_percent())
                print(term.on_green('CPU Usage in Percent:'))
                print(cpu_graph)

                try:
                    gpu_graph.step(gpustats()[0])
                    print()
                    print(term.on_red('GPU Usage in MiB:'))
                    print(gpu_graph)
                except Exception as e:
                    print(term.on_red(str(e)))

                ram_graph.step(psutil.virtual_memory().used / 1024**2)
                print()
                print(term.on_blue('RAM Usage in MiB:'))
                print(ram_graph)

                try:
                    io_graph.step(iostats())
                    print()
                    print(term.on_yellow('Read / Write Speed in KiB:'))
                    print(io_graph)
                except Exception as e:
                    raise e
                    # print(f'{Back.YELLOW}{e}{term.normal}')

                time.sleep(1/fps)
    except KeyboardInterrupt:
        print('Stopping..')
        print(term.clear())
        sys.exit(0)

#!/usr/bin/env python3

from __future__ import annotations

from functools import wraps

from py65.devices.mpu6502 import MPU as NMOS6502
from py65.memory import ObservableMemory

# https://stackoverflow.com/questions/11731136/class-method-decorator-with-self-arguments
def self_wrapper(method):
    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        return method(self, *method_args, **method_kwargs)
    return _impl


class mos6502:
    @self_wrapper
    def _putc_uart(self, address, value):
        print(f'MPU at {self._mpu.pc} writing {value} to {address}')

    @self_wrapper
    def _getc_uart(self, address):
        print(f'MCPU at {self._mpu.pc} reading {address}')
        # TODO: getch equivalent
        c = 0
        return c

    @self_wrapper
    def _console(self, address, value):
        y = (address - 0xE000) // 80
        x = (address - 0xE000) % 80
        print(f'MPU at {self._mpu.pc} writing {value} to frame buffer at {x},{y}')

    def __init__(self):
        self.memory = None
        self._mpu = NMOS6502(memory=self.memory)
        # TODO : why do we need to capture at this level?
        self.addrWidth = self._mpu.ADDR_WIDTH
        self.byteWidth = self._mpu.BYTE_WIDTH
        self.addrFmt = self._mpu.ADDR_FORMAT
        self.byteFmt = self._mpu.BYTE_FORMAT
        self.addrMask = self._mpu.addrMask
        self.byteMask = self._mpu.byteMask

        self.getc_char = 0  # Incoming console character

        m = ObservableMemory(subject=self.memory, addrWidth=self.addrWidth)
        m.subscribe_to_read([0xEFFF], self._getc_uart)
        m.subscribe_to_write([0xEFFF], self._putc_uart)
        m.subscribe_to_write(range(0xE000, 0xE7D0), self._console)  # 80x25 no color for now
        self._mpu.memory = m
        # Eventually treats self._mpu.memory as byte array/list

    def report(self):
        print(self._mpu)

    def step(self):
        self._mpu.step()

    def load(self, filename, start_addr):
        try:
            f = open(filename, 'rb')
            bytes = f.read()
            f.close()
        except (OSError, IOError) as exc:
            print(f'Cannot load file: {exc.errno}, {exc.strerror}')
            return  # TODO: throw

        print(f'Loading {filename}: {len(bytes)} to {start_addr}')

        index = 0
        while index < len(bytes):
            self._mpu.memory[start_addr + index] = bytes[index]
            index += 1

#
# ====================
#

def main() -> None:
    """Entry point function."""
   
    state = mos6502()
    
    running = False

    while True:
        cmd = input('>').split()
        match cmd[0]:
            case 'exit':
                break
            case 'go':
                running = True
            case 'load':
                state.load(cmd[1], int(cmd[2], 16))
                state._mpu.pc = int(cmd[2], 16)
            case 'step':
                state.step()
                state.report()

        # TODO: catch KeyboardInterrupt
        while running:
            state.step()
    
if __name__ == "__main__":
    main()
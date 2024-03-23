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
        assert address
        if value == 0x0d:
            print(f'MPU at 0x{self._mpu.pc:x} writing NL to UART')
        else:
            print(f'MPU at 0x{self._mpu.pc:x} writing \'{chr(value)}\' (0x{value:x}) to UART')
        if self._mpu.pc == self.watch_addr:
            self.running = False

    @self_wrapper
    def _getc_uart(self, address):
        assert address
        print(f'MCPU at 0x{self._mpu.pc:x} reading UART')
        if self._mpu.pc == self.watch_addr:
            self.running = False
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
        m = ObservableMemory(subject=self.memory, addrWidth=self._mpu.ADDR_WIDTH)

        m.subscribe_to_read([0xEFFF], self._getc_uart)
        m.subscribe_to_write([0xEFFF], self._putc_uart)
        m.subscribe_to_write(range(0xE000, 0xE7D0), self._console)  # 80x25 no color for now
        self._mpu.memory = m
        # Eventually treats self._mpu.memory as byte array/list

        self.getc_char = 0  # Incoming console character
        self.running = False
        self.watch_addr = -1

    def report(self):
        print(self._mpu)

    def step(self):
        self._mpu.step()
        if self._mpu.pc == self.watch_addr:
            print(f'MPU halted at at 0x{self._mpu.pc:x}')
            self.running = False

    def run(self):
        # TODO: catch keyboardinterrupt
        self.running = True
        while self.running:
            self.step()

    def watch(self, addr):
        self.watch_addr = addr

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

    print('Loading default firmware')
    state.load('data/fw.bin', 0xf000)
    state._mpu.pc = 0xf000

    while True:
        cmd = input('>').split()
        match cmd[0]:
            case 'exit' | 'q' | 'quit':
                break
            case 'break' | 'b':
                addr = int(cmd[1], 16)
                print(f'Setting breakpoint @ 0x{addr:x}')
                state.watch(addr)
            case 'go' | 'g' | 'run':
                state.run()
                state.report()
            case 'load' | 'l':
                loadpoint = 0x200
                if len(cmd) > 2:
                    loadpoint = int(cmd[2], 16)
                state.load(cmd[1], loadpoint)
            case 'step' | 's':
                state.step()
                state.report()
            case _:
                print("?command")

if __name__ == "__main__":
    main()
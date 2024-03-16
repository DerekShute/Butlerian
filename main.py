#!/usr/bin/env python3

from __future__ import annotations

import numpy
import tcod.console
import tcod.context
import tcod.event
import tcod.tileset
from functools import wraps

from py65.devices.mpu6502 import MPU as NMOS6502
from py65.memory import ObservableMemory

WHITE, BLACK = (255, 255, 255), (0, 0, 0)

# https://stackoverflow.com/questions/11731136/class-method-decorator-with-self-arguments
def self_wrapper(method):
    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        return method(self, *method_args, **method_kwargs)
    return _impl


class mos6502:
    @self_wrapper
    def _putc(self, address, value):
        assert address
        last_x = self.console.width - 1
        last_y = self.console.height - 1

        if value == 0x0D:          # Carriage return
            self.cursor_x = 0
            self.cursor_y = self.cursor_y + 1
        else:
            self.console.rgba[self.cursor_x, self.cursor_y] = (
                value, (*WHITE, 255), (*BLACK, 255),
            )

            self.cursor_x = self.cursor_x + 1
            if self.cursor_x > last_x:
                self.cursor_x = 0
                self.cursor_y = self.cursor_y + 1

        if self.cursor_y > last_y:
            # Scroll display, deleting that at top
            for i in range(0,last_y):
                self.console.rgba[:,i] = self.console.rgba[:,i+1]
            # Clear out the line at the bottom
            for i in range(0,last_x + 1):
                self.console.rgba[i, last_y] = (0, (*WHITE, 255), (*BLACK, 255))
            self.cursor_y = last_y
        self.updated = True

    @self_wrapper
    def _getc(self, address):
        assert address
        c = self.getc_char
        self.getc_char = 0
        return c

    @self_wrapper
    def _console(self, address, value):
        y = (address - 0xE000) // 80
        x = (address - 0xE000) % 80
        self.console.rgba[x,y] = (value, (*WHITE, 255), (*BLACK, 255))
        self.updated = True

    def __init__(self, console):
        self.cursor_x = 0
        self.cursor_y = 0
        self.console = console
        self.updated = False   # Nothing changed yet
        self.memory = None  # TODO: not sure how this hangs together.  Seems extra steps
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
        m.subscribe_to_read([0xEFFF], self._getc)
        m.subscribe_to_write([0xEFFF], self._putc)
        m.subscribe_to_write(range(0xE000, 0xE7D0), self._console)  # 80x25 no color for now
        self._mpu.memory = m
        # Eventually treats self._mpu.memory as byte array/list

        # The contract to the simulation needs to be made clear: write EFFF to some well-known location

    #
    # Console
    #

    def on_event(self, event: tcod.event.Event) -> None:
        match event:
            case tcod.event.Quit():
                raise SystemExit()
            case tcod.event.TextInput(text=text):
                self.getc_char = ord(text[0])

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

        print(f'Loading {filename} {len(bytes)} to {start_addr}')

        index = 0
        while index < len(bytes):
            self._mpu.memory[start_addr + index] = bytes[index]
            index += 1

        # Start it at the reset vector
        self._mpu.pc = self._mpu.memory[0xFFFC]

#
# ====================
#

def main() -> None:
    """Entry point function."""
    
    # columns, rows for the tilesheet itself
    tileset = tcod.tileset.load_tilesheet(
        "data/Alloy_curses_12x12.png", columns=16, rows=16, charmap=tcod.tileset.CHARMAP_CP437
    )
    tcod.tileset.procedural_block_elements(tileset=tileset)
    console = tcod.console.Console(80, 25, order="F")  # X across horizontal

    with tcod.context.new(console=console, tileset=tileset) as context:
        state = mos6502(console)
        state.load('data/fw.bin', 0xF000)
        
        # User program load

        state.load('data/hello.bin', 0x200)

        state.report()
        context.present(console)
        
        # Caveat: this is garbage
        running = False
        
        while True:
            for event in tcod.event.get():
                state.on_event(event)

            if not running:
                cmd = input('what now? ')
                if cmd == 'go':
                    running = True
                elif cmd == 'exit':
                    exit()
                elif cmd == 'step':
                    state.step()
                    state.report()
                    if state.updated:
                        context.present(console)
                        state.updated = False
                    if state._mpu.pc >= 0xfff0:
                        print('MPU at syscall %x' % state._mpu.pc)
            else:
                state.step()
                if state.updated:
                    context.present(console)
                    state.updated = False 

if __name__ == "__main__":
    main()
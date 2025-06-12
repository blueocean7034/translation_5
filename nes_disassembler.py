import sys
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler

ROM_HEX = 'my_rom_hex.txt'
OUTPUT_FILE = 'assembly_output.txt'


def load_rom(path: str):
    """Load ROM from hex text file."""
    with open(path) as f:
        hex_str = ''.join(line.strip() for line in f)
    return [int(hex_str[i:i+2], 16) for i in range(0, len(hex_str), 2)]


def main():
    rom_bytes = load_rom(ROM_HEX)
    if len(rom_bytes) < 16:
        raise ValueError('ROM file too small')

    header = rom_bytes[:16]
    prg_banks = header[4]
    prg_size = prg_banks * 16 * 1024
    prg_start = 16
    prg_end = prg_start + prg_size
    prg_bytes = rom_bytes[prg_start:prg_end]

    # allocate slightly more than 64KB so disassembler can read past the end
    memory = [0x00] * (len(prg_bytes) + 4)
    for i, b in enumerate(prg_bytes):
        memory[i] = b

    mpu = MPU(memory=memory, pc=0)
    dis = Disassembler(mpu)

    pc = 0
    end = len(prg_bytes)
    with open(OUTPUT_FILE, 'w') as out:
        while pc < end:
            opcode = mpu.ByteAt(pc)
            mnemonic, addressing = mpu.disassemble[opcode]
            length, text = dis.instruction_at(pc)
            bytes_str = ' '.join(f'{mpu.ByteAt(pc + i):02X}' for i in range(length))
            out.write(f'[0x{pc:04X}]: {bytes_str} {text}\n')

            operands = []
            if addressing == 'imm':
                val = mpu.ByteAt(pc + 1)
                operands.append(f'Immediate: 0x{val:02X}')
            elif addressing in ('zpg', 'zpx', 'zpy', 'zpi', 'inx', 'iny'):
                val = mpu.ByteAt(pc + 1)
                operands.append(f'ZeroPage Addr: 0x{val:02X}')
            elif addressing in ('abs', 'abx', 'aby', 'ind', 'iax'):
                addr = mpu.WordAt(pc + 1)
                operands.append(f'Address: 0x{addr:04X}')
            elif addressing == 'rel':
                off = mpu.ByteAt(pc + 1)
                target = (pc + 2 + (off - 0x100 if off & 0x80 else off)) & 0xFFFF
                operands.append(f'Relative: 0x{target:04X}')
            elif addressing == 'acc':
                operands.append('Accumulator')

            if operands:
                out.write('\tOperand breakdown:\n')
                for idx, op in enumerate(operands, 1):
                    out.write(f'\t  {idx}: {op}\n')
            else:
                out.write('\tOperand breakdown: None\n')

            pc += length


if __name__ == '__main__':
    main()

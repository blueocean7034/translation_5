import re
from pathlib import Path

ASM_SRC = Path('fceux-2.6.6/src/asm.cpp')
X6502_SRC = Path('fceux-2.6.6/src/x6502.cpp')
ROM_HEX = Path('my_rom_hex.txt')
OUTPUT = Path('assembly_output.txt')

LABEL_TO_MODE = {
    'indirectx': 'indirect_x',
    'zeropage': 'zeropage',
    'immediate': 'immediate',
    'absolute': 'absolute',
    'branch': 'relative',
    'indirecty': 'indirect_y',
    'zeropagex': 'zeropage_x',
    'absolutey': 'absolute_y',
    'absolutex': 'absolute_x',
    'jump': 'absolute',
    'zeropagey': 'zeropage_y',
    'indirect': 'indirect',
}

def parse_opsize():
    lines = X6502_SRC.read_text().splitlines()
    start = next(i for i,l in enumerate(lines) if 'opsize[256]' in l)
    end_if = next(i for i in range(start, len(lines)) if '#endif' in lines[i])
    values = [1]  # opcode 0x00 size
    for line in lines[end_if+1:]:
        if '};' in line:
            break
        line = re.sub(r'/\*0x[0-9A-Fa-f]+\*/', '', line)
        line = line.split('//')[0]
        values.extend(int(n) for n in re.findall(r'\d+', line))
    if len(values) != 256:
        raise ValueError('Failed to parse opsize table')
    return values

def parse_instruction_table():
    text = ASM_SRC.read_text()
    start = text.index('switch (opcode[0])')
    end = text.index('default: strcpy(str,"ERROR")', start)
    portion = text[start:end]
    case1 = re.compile(r'case 0x([0-9A-F]{2}):\s*strcpy\(chr,"([A-Z]{3})"\); goto _(\w+);')
    case2 = re.compile(r'case 0x([0-9A-F]{2}):\s*strcpy\(str,"([A-Z]{3})"\); break;')
    table = {}
    for line in portion.splitlines():
        line = line.strip()
        m = case1.match(line)
        if m:
            table[int(m.group(1), 16)] = (m.group(2), m.group(3))
            continue
        m = case2.match(line)
        if m:
            table[int(m.group(1), 16)] = (m.group(2), 'implied')
    if 0x6C not in table:
        table[0x6C] = ('JMP', 'indirect')
    return table

def format_operand(mode, pc, operands):
    if mode == 'implied':
        return ''
    if mode == 'indirect_x':
        return f'($%02X,X)' % operands[0]
    if mode == 'indirect_y':
        return f'($%02X),Y' % operands[0]
    if mode == 'zeropage':
        return f'$%02X' % operands[0]
    if mode == 'zeropage_x':
        return f'$%02X,X' % operands[0]
    if mode == 'zeropage_y':
        return f'$%02X,Y' % operands[0]
    if mode == 'immediate':
        return f'#$%02X' % operands[0]
    if mode == 'absolute':
        value = operands[0] | (operands[1] << 8)
        return f'$%04X' % value
    if mode == 'absolute_x':
        value = operands[0] | (operands[1] << 8)
        return f'$%04X,X' % value
    if mode == 'absolute_y':
        value = operands[0] | (operands[1] << 8)
        return f'$%04X,Y' % value
    if mode == 'indirect':
        value = operands[0] | (operands[1] << 8)
        return f'($%04X)' % value
    if mode == 'relative':
        offset = operands[0] if operands[0] < 0x80 else operands[0] - 0x100
        target = (pc + 2 + offset) & 0xFFFF
        return f'$%04X' % target
    return ''

def main():
    opsize = parse_opsize()
    instructions = parse_instruction_table()

    hex_data = ''.join(line.strip() for line in ROM_HEX.read_text().splitlines())
    rom = bytes.fromhex(hex_data)
    pc = 16  # skip iNES header
    lines = []
    while pc < len(rom):
        opcode = rom[pc]
        size = opsize[opcode] or 1
        instr_bytes = rom[pc:pc+size]
        mnemonic, label = instructions.get(opcode, ('???', 'implied'))
        mode = LABEL_TO_MODE.get(label, 'implied')
        operands = instr_bytes[1:]
        asm_op = mnemonic
        operand_text = format_operand(mode, pc, operands)
        if operand_text:
            asm_op += ' ' + operand_text
        machine = ' '.join(f'{b:02X}' for b in instr_bytes)
        operand_desc = ', '.join(f'op{i+1}=0x{b:02X}' for i, b in enumerate(operands))
        lines.append(f'[0x{pc:04X}]')
        lines.append(f'[{machine}]')
        lines.append(f'[{asm_op}]')
        lines.append(f'[{operand_desc}]')
        lines.append('')
        pc += size

    OUTPUT.write_text('\n'.join(lines))

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Hardware-free, fail-closed ELF32 ARM ordinary-SRAM layout inspection.

This checks destination/metadata/allocation, not electrical safety or recovery.
"""
import struct
SRAM_START=0x20000000
SRAM_END=0x20082000
BUDGET=128*1024
PROFILE=b'FORGIX_USB_RAM_V1;no_flash;rp2350-arm;heap0;stack4096;max120s;sdk2.2.0;tinyusb86ad6e56\0'


def require(condition, reason):
    if not condition: raise ValueError(reason)


def inspect_elf(data):
    require(52 <= len(data) <= 4*1024*1024, 'ELF byte bound')
    require(data[:7]==b'\x7fELF\x01\x01\x01', 'ELF32 little endian required')
    h=struct.unpack_from('<16sHHIIIIIHHHHHH',data)
    _,kind,machine,version,entry,phoff,shoff,flags,ehsize,phsize,phnum,shsize,shnum,shstrings=h
    require(kind==2 and machine==40 and version==1 and ehsize==52, 'ARM executable required')
    require(phsize==32 and 1<=phnum<=16 and phoff>=52 and phoff+phsize*phnum<=len(data),'program headers')
    require(shsize==40 and 1<=shnum<=512 and shoff>=52 and shoff+shsize*shnum<=len(data),'section headers')
    require(0<shstrings<shnum,'section names')
    loads=[]
    for i in range(phnum):
        t,offset,vaddr,paddr,filesz,memsz,pflags,align=struct.unpack_from('<8I',data,phoff+i*phsize)
        require(t not in (2,3),'dynamic/interpreter segment forbidden')
        if t!=1:continue
        require(memsz>0 and filesz<=memsz and offset+filesz<=len(data),'load length')
        require(SRAM_START<=vaddr<vaddr+memsz<=SRAM_END and paddr==vaddr,'ordinary SRAM destination')
        require(not (pflags & ~7) and align in (1,4,8,16,256,512,4096,65536),'load alignment/flags')
        require(align==1 or vaddr%align==offset%align,'load alignment congruence')
        loads.append(dict(offset=offset,vaddr=vaddr,paddr=paddr,filesz=filesz,memsz=memsz,flags=pflags))
    require(loads,'no load segments')
    ranges=sorted((r['vaddr'],r['vaddr']+r['memsz']) for r in loads)
    require(all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])),'overlapping load segments')
    require(sum(r['memsz'] for r in loads)<=BUDGET,'128 KiB allocation budget')
    require(entry&1 and any(r['flags']&1 and r['vaddr']<=entry-1<r['vaddr']+r['filesz'] for r in loads),'Thumb entry in executable bytes')
    sections=[struct.unpack_from('<10I',data,shoff+i*shsize) for i in range(shnum)]
    def bytes_for(s):
        require(s[1]!=8 and s[4]+s[5]<=len(data),'section bytes')
        return data[s[4]:s[4]+s[5]]
    strings=bytes_for(sections[shstrings]);require(sections[shstrings][1]==3,'section name table')
    def text(table,start):
        require(start<len(table),'string offset')
        end=table.find(b'\0',start);require(end>=start,'string termination')
        return table[start:end].decode('ascii')
    names=[text(strings,s[0]) for s in sections]
    for name,s in zip(names,sections):
        if s[2]&2 and s[5]:
            require(SRAM_START<=s[3]<s[3]+s[5]<=SRAM_END,'allocated section outside ordinary SRAM')
            require(any(r['vaddr']<=s[3] and s[3]+s[5]<=r['vaddr']+r['memsz'] for r in loads),'allocated section outside LOAD')
        if name in ('.heap','.stack1_dummy'):require(s[5]==0,'heap/core1 allocation')
    symbols={};defined=[]
    for s in sections:
        if s[1]!=2:continue
        require(s[9]==16 and s[5]%16==0 and 0<s[6]<shnum,'symbol table format')
        table=bytes_for(sections[s[6]]);raw=bytes_for(s)
        for off in range(0,len(raw),16):
            name,value,size,info,other,index=struct.unpack_from('<IIIBBH',raw,off)
            if not name or not index:continue
            label=text(table,name)
            # ARM mapping and translation-unit local names may legitimately repeat.
            if info>>4:
                require(label not in symbols or symbols[label]==value,'conflicting global symbols')
                symbols[label]=value
            defined.append(label)
    for name in ('__vectors','__StackTop','__StackBottom','__StackOneTop','__StackOneBottom','__bss_start__','__bss_end__','__end__'):
        require(name in symbols,'required layout symbol '+name)
    require(symbols['__StackTop']-symbols['__StackBottom']==4096,'explicit 4 KiB core0 stack')
    require(symbols['__StackOneTop']==symbols['__StackOneBottom'],'core1 stack inactive')
    require(SRAM_START<=symbols['__StackBottom']<symbols['__StackTop']<=SRAM_END,'stack range')
    require(any(r['vaddr']<=symbols['__StackBottom'] and symbols['__StackTop']<=r['vaddr']+r['memsz'] for r in loads),'stack outside LOAD')
    require(SRAM_START<=symbols['__bss_start__']<=symbols['__bss_end__']<=SRAM_END,'BSS range')
    forbidden=('gpio_init','gpio_set_dir','gpio_put','spi_init','uart_init','pio_add_program','multicore_launch_core1',
               'flash_range_erase','flash_range_program','malloc','calloc','realloc','free','_sbrk','_sbrk_r')
    require(not any(label.split('.')[0] in forbidden or label.split('.')[0] in tuple('__wrap_'+n for n in forbidden) for label in defined),'prohibited application/peripheral/allocation symbol')
    vectors=symbols['__vectors'];base=next((r for r in loads if r['vaddr']<=vectors and vectors+8<=r['vaddr']+r['filesz']),None)
    require(base is not None and vectors==ranges[0][0] and vectors%512==0,'initial vector table')
    off=base['offset']+vectors-base['vaddr'];sp,reset=struct.unpack_from('<II',data,off)
    require(sp==symbols['__StackTop'] and reset&1 and any(r['flags']&1 and r['vaddr']<=reset-1<r['vaddr']+r['filesz'] for r in loads),'vector SP/reset')
    # Exact SDK no_flash ARM RP2350 IMAGE_DEF: image type 0x1021, vector item,
    # single block loop. This secure execution-mode label is not OTP/security setup.
    block=struct.pack('<7I',0xffffded3,0x10210142,0x00000203,vectors,0x000003ff,0,0xab123579)
    require(data[off:off+min(base['filesz'],4096)].count(block)==1,'RP2350 ARM RAM IMAGE_DEF')
    require(any(PROFILE in data[r['offset']:r['offset']+r['filesz']] for r in loads),'loadable distinct application profile')
    require('main' in symbols and 'tud_task_ext' in symbols,'application/direct TinyUSB symbols')
    return {'target':'RP2350 ARM','binary_type':'no_flash','allocated_load_bytes':sum(r['memsz'] for r in loads),
            'load_segments':loads,'stack_bytes':4096,'core1_stack_bytes':0,'heap_section_bytes':0,
            'entry':entry,'vector_table':vectors,'symbols':symbols,
            'limitations':'Layout/metadata guard; no hardware, electrical pin-state or recovery proof. SDK startup peripheral resets remain audited separately.'}

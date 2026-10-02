"""Synthetic ELF geometry and actual source-policy tests; no device operations."""
import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from forgix_usb_ram_artifact import inspect_elf,PROFILE

def fixture():
    data=bytearray(0x4000)
    labels={'__vectors':0x20000000,'__StackTop':0x20082000,'__StackBottom':0x20081000,
            '__StackOneTop':0x20081000,'__StackOneBottom':0x20081000,
            '__bss_start__':0x20000800,'__bss_end__':0x20000900,'__end__':0x20000900,
            'main':0x20000201,'tud_task_ext':0x20000241}
    names=bytearray(b'\0');symbols=bytearray(16)
    for name,value in labels.items():
        offset=len(names);names.extend(name.encode()+b'\0');symbols.extend(struct.pack('<IIIBBH',offset,value,0,0x12,0,1))
    sections=['','.text','.bss','.stack_dummy','.symtab','.strtab','.shstrtab']
    shnames=bytearray(b'\0');idx=[0]
    for name in sections[1:]:idx.append(len(shnames));shnames.extend(name.encode()+b'\0')
    rows=[(0,0,0,0,0,0,0,0,0,0),(idx[1],1,6,0x20000000,0x1000,0x800,0,0,512,0),
          (idx[2],8,3,0x20000800,0x1800,0x100,0,0,4,0),
          (idx[3],8,3,0x20081000,0x2000,0x1000,0,0,4,0),
          (idx[4],2,0,0,0x2800,len(symbols),5,0,4,16),
          (idx[5],3,0,0,0x3000,len(names),0,0,1,0),
          (idx[6],3,0,0,0x3200,len(shnames),0,0,1,0)]
    ident=b'\x7fELF\x01\x01\x01'+bytes(9)
    struct.pack_into('<16sHHIIIIIHHHHHH',data,0,ident,2,40,1,0x20000201,52,0x3400,0x5000000,52,32,2,40,len(rows),6)
    struct.pack_into('<8I',data,52,1,0x1000,0x20000000,0x20000000,0x800,0x900,7,0x1000)
    struct.pack_into('<8I',data,84,1,0x2000,0x20081000,0x20081000,0,0x1000,6,0x1000)
    struct.pack_into('<II',data,0x1000,0x20082000,0x20000201)
    struct.pack_into('<7I',data,0x1200,0xffffded3,0x10210142,0x203,0x20000000,0x3ff,0,0xab123579)
    data[0x1300:0x1300+len(PROFILE)]=PROFILE
    data[0x2800:0x2800+len(symbols)]=symbols;data[0x3000:0x3000+len(names)]=names;data[0x3200:0x3200+len(shnames)]=shnames
    for i,row in enumerate(rows):struct.pack_into('<10I',data,0x3400+40*i,*row)
    return data

class ElfGuardTests(unittest.TestCase):
    def test_main_and_scratch_allocations_count_without_gap(self):
        result=inspect_elf(fixture());self.assertEqual(result['allocated_load_bytes'],0x1900);self.assertEqual(result['stack_bytes'],4096)
    def test_flash_otp_peripheral_and_alias_destinations_refused(self):
        for value in (0x10000000,0x40000000,0x00000000,0x20082000):
            d=fixture();struct.pack_into('<II',d,52+8,value,value)
            with self.assertRaises(ValueError):inspect_elf(d)
        d=fixture();struct.pack_into('<I',d,52+12,0x10000000)
        with self.assertRaises(ValueError):inspect_elf(d)
    def test_load_size_overflow_and_allocation_budget_refused(self):
        for field,value in ((16,0xa00),(20,0x30000),(4,len(fixture()))):
            d=fixture();struct.pack_into('<I',d,52+field,value)
            with self.assertRaises(ValueError):inspect_elf(d)
    def test_overlap_even_inside_ordinary_sram_refused(self):
        d=fixture();struct.pack_into('<II',d,84+8,0x20000000,0x20000000)
        with self.assertRaises(ValueError):inspect_elf(d)
    def test_even_or_outside_entry_and_bad_vector_refused(self):
        for off,val in ((24,0x20000200),(24,0x10000001),(0x1000,0x20080000),(0x1004,0x10000001)):
            d=fixture();struct.pack_into('<I',d,off,val)
            with self.assertRaises(ValueError):inspect_elf(d)
    def test_rp2040_riscv_or_flash_metadata_refused(self):
        for val in (0x00210142,0x11210142):
            d=fixture();struct.pack_into('<I',d,0x1204,val)
            with self.assertRaises(ValueError):inspect_elf(d)
        d=fixture();struct.pack_into('<I',d,0x1214,4)
        with self.assertRaises(ValueError):inspect_elf(d)
    def test_missing_or_duplicate_metadata_refused(self):
        d=fixture();d[0x1200:0x121c]=bytes(28)
        with self.assertRaises(ValueError):inspect_elf(d)
        d=fixture();d[0x1400:0x141c]=d[0x1200:0x121c]
        with self.assertRaises(ValueError):inspect_elf(d)
    def test_missing_profile_and_corrupt_sections_refused(self):
        d=fixture();d[0x1300]=0
        with self.assertRaises(ValueError):inspect_elf(d)
        d=fixture();struct.pack_into('<I',d,0x3400+40+12,0x10000000)
        with self.assertRaises(ValueError):inspect_elf(d)
    def test_big_endian_or_non_arm_refused(self):
        d=fixture();d[5]=2
        with self.assertRaises(ValueError):inspect_elf(d)
        d=fixture();struct.pack_into('<H',d,18,243)
        with self.assertRaises(ValueError):inspect_elf(d)
    def test_application_has_one_owner_no_stdio_or_gpio_calls(self):
        root=Path(__file__).resolve().parents[1]/'firmware/forgix-usb-ram'
        s=(root/'main.c').read_text();self.assertEqual(s.count('tud_task();'),1)
        for word in ('gpio_init(','gpio_put(','spi_init(','uart_init(','printf(','multicore_launch_core1('):self.assertNotIn(word,s)
        self.assertIn('watchdog_enable(2000,false)',s);self.assertIn('MAX_LIFETIME_US UINT64_C(120000000)',s)
        cmake=(root/'CMakeLists.txt').read_text();self.assertIn('PICO_HEAP_SIZE=0',cmake);self.assertIn('PICO_STACK_SIZE=4096',cmake);self.assertIn('no_flash)',cmake)
if __name__=='__main__':unittest.main()

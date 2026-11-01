import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from formats import Archive, compress, parse_table, rebuild_table
from project import technical_errors
import project

class IntegrityTests(unittest.TestCase):
    def test_compression_boundaries_and_raw_chunks(self):
        for data in (b'x'*65536,b'x'*65550,os.urandom(65550),b'A'*140000):
            encoded=compress(data)
            with tempfile.TemporaryDirectory() as root:
                p=Path(root)
                (p/'LD_C0_R.BIN').write_bytes(encoded)
                (p/'LI_C0_R.IDX').write_bytes(struct.pack('<QQQQ',0,len(data),len(encoded),1))
                self.assertEqual(Archive(p).read(0),data)

    def test_truncated_chunk_rejected(self):
        encoded=compress(b'text'*300)
        with tempfile.TemporaryDirectory() as root:
            p=Path(root)
            (p/'LD_C0_R.BIN').write_bytes(encoded[:135])
            (p/'LI_C0_R.IDX').write_bytes(struct.pack('<QQQQ',0,1200,135,1))
            with self.assertRaises(ValueError):Archive(p).read(0)

    def test_pointer_growth_and_opaque_metadata(self):
        for stride,fields in [(8,(0,)),(12,(0,4)),(32,(0,4,8,12,16,20))]:
            data=bytearray(64+4*stride)
            struct.pack_into('<II',data,0,4,2)
            data[8:64]=bytes(range(56))
            for row in range(4):
                for field in fields:
                    pos=64+row*stride+field
                    struct.pack_into('<i',data,pos,len(data)-pos)
                    data.extend(b'Text\0')
            t=parse_table(data)
            self.assertIsNotNone(t, f"stride={stride}")
            changed=rebuild_table(bytes(data),t,{(0,0):'Tradução maior com acentuação çãé'})
            new=parse_table(changed)
            self.assertEqual(new.strings[(0,0)],'Tradução maior com acentuação çãé')
            normalized=bytearray(changed[:len(data)])
            normalized[64:68]=data[64:68]
            self.assertEqual(normalized,data)
            self.assertEqual(rebuild_table(bytes(data),t,{}),data)

    def test_tags_and_placeholders(self):
        self.assertEqual(technical_errors('<$cdef(27)>Hello <pname;0></color><br>','<$cdef(27)>Olá <pname;0></color><br>'),[])
        self.assertIn('placeholder_or_tag_mismatch',technical_errors('<$iname(5)> %s','<$iname(6)> %s'))
        self.assertTrue(technical_errors('Name','Nome\0'))

    def test_reviewed_translation_cannot_be_overwritten_by_batch(self):
        with tempfile.TemporaryDirectory() as root:
            cat=Path(root)/'catalog.jsonl';batch=Path(root)/'batch.jsonl'
            project.save_jsonl(cat,[dict(id='example',source='Hello',translation='Olá',status='reviewed')])
            project.save_jsonl(batch,[dict(id='example',translation='Oi')])
            original=cat.read_bytes()
            with patch.object(project,'CAT',cat):
                with self.assertRaises(ValueError):project.apply_batch(SimpleNamespace(file=batch))
            self.assertEqual(cat.read_bytes(),original)

    def test_bad_translation_batch_is_atomic(self):
        with tempfile.TemporaryDirectory() as root:
            cat=Path(root)/'catalog.jsonl';batch=Path(root)/'batch.jsonl'
            project.save_jsonl(cat,[dict(id='a',source='Hello',translation='',status='pending_translation'),dict(id='b',source='<pname;0>',translation='',status='pending_translation')])
            project.save_jsonl(batch,[dict(id='a',translation='Olá'),dict(id='b',translation='Nome')])
            original=cat.read_bytes()
            with patch.object(project,'CAT',cat):
                with self.assertRaises(ValueError):project.apply_batch(SimpleNamespace(file=batch))
            self.assertEqual(cat.read_bytes(),original)

if __name__=='__main__':unittest.main()

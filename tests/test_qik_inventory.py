"""Authored fixtures exercise inventory rejection, without vendor payloads."""
from pathlib import Path
import tempfile
import unittest

from research.adapters.inspect_qik_inventory import inspect_blocks, inspect_pe


class QikInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.entry = ("<QIKFileInfo><ID>2</ID><DestPath>../untrusted-label</DestPath>"
                      "<isFolder>false</isFolder><Filesize>3</Filesize>"
                      "<FileType>Content</FileType></QIKFileInfo>")
        self.write_xml(self.entry)
        (self.root / "block-0002-type-1.bin").write_bytes(b"abc")
        (self.root / "block-0003-type-255.bin").write_bytes(b"index-not-validated-here")

    def write_xml(self, entries):
        (self.root / "block-0001-type-2.bin").write_text(
            "<QIKPackage>" + entries + "</QIKPackage>", encoding="utf-8")

    def test_complete_record_preserves_label_without_using_it_as_path(self):
        result = inspect_blocks(self.root)
        self.assertEqual(result["file_count"], 1)
        self.assertEqual(result["files"][0]["destination_label"], "../untrusted-label")
        self.assertEqual(result["files"][0]["sha256"],
                         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        self.assertIsNone(result["files"][0]["pe"])

    def test_missing_payload(self):
        (self.root / "block-0002-type-1.bin").unlink()
        with self.assertRaisesRegex(ValueError, "association"):
            inspect_blocks(self.root)

    def test_partial_payload(self):
        (self.root / "block-0002-type-1.bin").write_bytes(b"ab")
        with self.assertRaisesRegex(ValueError, "size mismatch"):
            inspect_blocks(self.root)

    def test_duplicate_metadata_id(self):
        self.write_xml(self.entry + self.entry)
        with self.assertRaisesRegex(ValueError, "association"):
            inspect_blocks(self.root)

    def test_unmapped_payload(self):
        (self.root / "block-0004-type-1.bin").write_bytes(b"unexplained")
        with self.assertRaisesRegex(ValueError, "Unmapped"):
            inspect_blocks(self.root)

    def test_duplicate_field(self):
        self.write_xml(self.entry.replace("<ID>2</ID>", "<ID>2</ID><ID>3</ID>"))
        with self.assertRaisesRegex(ValueError, "Duplicate metadata field"):
            inspect_blocks(self.root)

    def test_missing_index(self):
        (self.root / "block-0003-type-255.bin").unlink()
        with self.assertRaisesRegex(ValueError, "index block"):
            inspect_blocks(self.root)

    def test_entity_declarations(self):
        self.write_xml('<!DOCTYPE QIKPackage [<!ENTITY injected "abc">]>' + self.entry)
        with self.assertRaisesRegex(ValueError, "DTD/entity"):
            inspect_blocks(self.root)

    def test_malformed_executable_is_not_silently_classified_as_data(self):
        with self.assertRaisesRegex(ValueError, "parseable PE"):
            inspect_pe(b"MZbad")

    def test_utf16_cannot_bypass_entity_rejection(self):
        text = '<!DOCTYPE QIKPackage [<!ENTITY x "abc">]><QIKPackage>' + self.entry + '</QIKPackage>'
        for encoding in ('utf-16', 'utf-16-le', 'utf-16-be'):
            with self.subTest(encoding=encoding):
                (self.root/'block-0001-type-2.bin').write_bytes(text.encode(encoding))
                with self.assertRaises(ValueError):
                    inspect_blocks(self.root)


if __name__ == "__main__":
    unittest.main()

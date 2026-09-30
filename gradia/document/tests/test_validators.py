import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from gradia.document.validators import (
    validate_correction_file,
    validate_document_file,
    validate_document_files,
    validate_subject_file,
)


class TestDocumentValidators:
    def test_validate_none_or_empty_passes_or_handles(self):
        validate_document_file(None)
        validate_subject_file(None)
        validate_correction_file(None)

    def test_validate_invalid_extension(self):
        file = SimpleUploadedFile("malicious.exe", b"MZ\x90\x00\x03\x00\x00\x00", content_type="application/x-msdownload")
        with pytest.raises(ValidationError, match="Only PDF, DOC or DOCX files are allowed"):
            validate_document_file(file)

    def test_validate_oversized_file(self, monkeypatch):
        from gradia.utils import enums
        monkeypatch.setattr(enums, "MAX_DOCUMENT_SIZE", 10)
        file = SimpleUploadedFile("document.pdf", b"%PDF-1.4\n123456789012345", content_type="application/pdf")
        with pytest.raises(ValidationError, match="must not exceed"):
            validate_document_file(file)

    def test_validate_invalid_content_type(self):
        file = SimpleUploadedFile("document.pdf", b"%PDF-1.4\ncontent", content_type="text/html")
        with pytest.raises(ValidationError, match="uploaded file type is not allowed"):
            validate_document_file(file)

    def test_validate_path_traversal_filename(self):
        file = SimpleUploadedFile("../document.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf")
        with pytest.raises(ValidationError, match="file name is invalid"):
            validate_document_file(file)

    def test_validate_empty_file_signature(self):
        file = SimpleUploadedFile("document.pdf", b"", content_type="application/pdf")
        with pytest.raises(ValidationError, match="uploaded file is empty"):
            validate_document_file(file)

    def test_validate_mismatched_signature_pdf(self):
        file = SimpleUploadedFile("document.pdf", b"PK\x03\x04zipcontent", content_type="application/pdf")
        with pytest.raises(ValidationError, match="not a valid PDF file"):
            validate_document_file(file)

    def test_validate_mismatched_signature_docx(self):
        file = SimpleUploadedFile("document.docx", b"%PDF-1.4pdfcontent", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        with pytest.raises(ValidationError, match="not a valid DOC/DOCX file"):
            validate_document_file(file)

    def test_validate_valid_pdf_and_docx(self):
        pdf = SimpleUploadedFile("sample.pdf", b"%PDF-1.4\nvalid content", content_type="application/pdf")
        docx = SimpleUploadedFile("sample.docx", b"PK\x03\x04\x14\x00\x06\x00", content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        validate_document_files(pdf, docx)

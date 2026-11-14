"""Local bounded extraction; original binary files never go to the model provider."""

import base64
import binascii
import io
import json
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from openpyxl import load_workbook
from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_TEXT_BYTES = 24000


class Attachment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=160)
    data: str = Field(max_length=14_000_000)

    @field_validator("name")
    @classmethod
    def supported_name(cls, name):
        if (
            "/" in name
            or "\\" in name
            or PurePosixPath(name).suffix.lower()
            not in {".md", ".txt", ".json", ".xlsx"}
        ):
            raise ValueError(
                "Supported files: .md, .txt, .json, .xlsx; supply a filename without a path."
            )
        return name


def extract(attachment: Attachment) -> str:
    try:
        raw = base64.b64decode(attachment.data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("File is not valid base64.") from exc
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("Maximum file size is 10 MB.")
    suffix = PurePosixPath(attachment.name).suffix.lower()
    if suffix == ".xlsx":
        try:
            with ZipFile(io.BytesIO(raw)) as archive:
                if (
                    sum(info.file_size for info in archive.infolist())
                    > 32 * 1024 * 1024
                ):
                    raise ValueError("Expanded spreadsheet exceeds 32 MB.")
                if any("vbaproject" in name.lower() for name in archive.namelist()):
                    raise ValueError(
                        "Spreadsheets containing macros are not supported."
                    )
            workbook = load_workbook(
                io.BytesIO(raw), read_only=True, data_only=False, keep_links=False
            )
            parts = []
            size = 0
            cells = 0
            try:
                for sheet in workbook:
                    parts.append(f"## Sheet: {sheet.title}\n")
                    for row in sheet.iter_rows():
                        cells += len(row)
                        if cells > 100000:
                            raise ValueError("Spreadsheet exceeds 100,000 cells.")
                        line = "\t".join(
                            "" if cell.value is None else str(cell.value)
                            for cell in row
                        )
                        size += len(line.encode())
                        if size > MAX_TEXT_BYTES:
                            raise ValueError(
                                "Extracted file text is too large. Supply a smaller relevant excerpt."
                            )
                        parts.append(line)
            finally:
                workbook.close()
            text = "\n".join(parts)
        except (BadZipFile, KeyError, OSError) as exc:
            raise ValueError("Cannot read this spreadsheet.") from exc
    else:
        try:
            text = raw.decode("utf-8-sig")
            if suffix == ".json":
                json.loads(text)
        except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            raise ValueError(
                "Text must be UTF-8; JSON files must contain valid JSON."
            ) from exc
    if len(text.encode()) > MAX_TEXT_BYTES:
        raise ValueError(
            "Extracted file text is too large. Supply a smaller relevant excerpt."
        )
    if not text.strip():
        raise ValueError("File contains no readable text.")
    return f"\n\n[Untrusted attachment: {attachment.name}]\n{text}\n[End attachment]"

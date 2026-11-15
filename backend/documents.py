"""Local bounded extraction; original binary files never go to the model provider."""

import base64
import binascii
import json
from pathlib import PurePosixPath

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
            not in {".md", ".txt", ".json", ".geojson", ".csv", ".tsv"}
        ):
            raise ValueError(
                "Attach a text file (.json, .geojson, .txt, .md, .csv, .tsv) without a path. "
                "For PDFs, images, spreadsheets or other formats, copy the relevant text "
                "and paste it into the message, or export it to a supported text format."
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
    try:
        text = raw.decode("utf-8-sig")
        if suffix in {".json", ".geojson"}:
            json.loads(text)
        if any(ord(char) < 32 and char not in "\t\n\r" for char in text):
            raise ValueError("File contains binary data. Paste text or export as UTF-8 text.")
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

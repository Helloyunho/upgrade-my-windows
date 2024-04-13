from typing import TypedDict


class OSPreset(TypedDict):
    vcpus: int
    memory: int
    cdrom: list[str] | None
    floppy: list[str] | None
    os: str

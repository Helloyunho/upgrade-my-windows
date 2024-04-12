from typing import TypedDict


class VMInfo(TypedDict):
    memory: int
    cpu: int
    cdrom: str | None
    floppy: str | None
    os: str

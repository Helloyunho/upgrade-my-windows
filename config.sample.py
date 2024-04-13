from os_preset import OSPreset


os_list: list[OSPreset] = [
    {
        "vcpus": 1,  # Number of virtual CPUs
        "memory": 8192,  # Memory in KB
        "cdrom": ["first.iso", "second.iso"],  # CD-ROM images
        "floppy": ["first.img", "second.img"],  # Floppy images
        "os": "1.0",  # Windows version name (e.g. 1.0, 2.0, 3.0, 3.1, 95, 98, 2000, XP, Vista, 7, 8, 8.1, 10)
    }
]

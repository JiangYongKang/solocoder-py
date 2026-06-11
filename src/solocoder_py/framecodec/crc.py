from __future__ import annotations

from typing import Dict, Tuple

from .exceptions import FrameConfigError


class CrcCalculator:
    _crc16_table: Tuple[int, ...] = ()
    _crc32_table: Tuple[int, ...] = ()

    @classmethod
    def _build_crc16_table(cls) -> Tuple[int, ...]:
        if cls._crc16_table:
            return cls._crc16_table
        table = []
        for i in range(256):
            crc = i << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = (crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
                crc &= 0xFFFF
            table.append(crc)
        cls._crc16_table = tuple(table)
        return cls._crc16_table

    @classmethod
    def _build_crc32_table(cls) -> Tuple[int, ...]:
        if cls._crc32_table:
            return cls._crc32_table
        table = []
        for i in range(256):
            crc = i
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xEDB88320
                else:
                    crc = crc >> 1
            table.append(crc)
        cls._crc32_table = tuple(table)
        return cls._crc32_table

    @staticmethod
    def calculate(data: bytes, crc_size: int) -> int:
        if crc_size == 2:
            return CrcCalculator._crc16(data)
        elif crc_size == 4:
            return CrcCalculator._crc32(data)
        else:
            raise FrameConfigError(
                f"Unsupported CRC size: {crc_size} bytes. Supported sizes: 2 (CRC-16), 4 (CRC-32)"
            )

    @staticmethod
    def _crc16(data: bytes) -> int:
        table = CrcCalculator._build_crc16_table()
        crc = 0xFFFF
        for byte in data:
            index = ((crc >> 8) ^ byte) & 0xFF
            crc = ((crc << 8) ^ table[index]) & 0xFFFF
        return crc

    @staticmethod
    def _crc32(data: bytes) -> int:
        table = CrcCalculator._build_crc32_table()
        crc = 0xFFFFFFFF
        for byte in data:
            index = (crc ^ byte) & 0xFF
            crc = ((crc >> 8) ^ table[index]) & 0xFFFFFFFF
        return crc ^ 0xFFFFFFFF

    @staticmethod
    def verify(data: bytes, expected_crc: int, crc_size: int) -> bool:
        actual_crc = CrcCalculator.calculate(data, crc_size)
        return actual_crc == expected_crc

    @staticmethod
    def max_value(crc_size: int) -> int:
        if crc_size == 2:
            return 0xFFFF
        elif crc_size == 4:
            return 0xFFFFFFFF
        else:
            raise FrameConfigError(
                f"Unsupported CRC size: {crc_size} bytes"
            )

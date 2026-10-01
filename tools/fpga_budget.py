#!/usr/bin/env python3
"""Deterministic capacity calculations. These are not throughput measurements."""
import json
import math


def budget():
    usb_wire_bytes_s = 12_000_000 / 8
    snapshots = 16_380
    rows = []
    for sample_rate in [16_000_000, 40_000_000, 80_000_000]:
        for bits_per_pair in [16, 20]:
            payload = sample_rate * bits_per_pair / 8
            rows.append({'pairs_s': sample_rate, 'bits_pair': bits_per_pair,
                         'packed_payload_bytes_s': payload,
                         'sram_word_bytes_s': sample_rate * 4,
                         'maximum_snapshot_seconds': snapshots / sample_rate,
                         'snapshot_payload_bytes': math.ceil(snapshots * bits_per_pair / 8),
                         'minimum_usb_full_speed_drain_seconds': snapshots * bits_per_pair / 8 / usb_wire_bytes_s,
                         'minimum_decimation_to_usb_wire_bound': math.ceil(payload / usb_wire_bytes_s),
                         't8_all_memory_fill_seconds': (122_880 / 8) / payload})
    return {'evidence_class': 'calculation only; framing, CPU, and DMA overhead excluded',
            'constants': {'usb_full_speed_wire_bits_s': 12_000_000,
                          'original_capture_pairs': snapshots, 't8_memory_bits': 122_880},
            'raw_and_snapshot_budgets': rows,
            'decimated_80msps_20bit_bytes_s': {str(factor): 200_000_000 / factor
                                            for factor in [16, 64, 128, 256]},
            'example_spectrum_bytes_s': {str(bins): bins * 2 * 10 for bins in [256, 1024, 2048]},
            'spectrum_model': 'Assumed 16-bit bin value, 10 frames/s, no header; not a firmware throughput claim.',
            'spi_1line_ideal_bytes_s': {str(hz): hz / 8 for hz in [1_000_000, 10_000_000, 40_000_000, 80_000_000]},
            'limits': ['USB line rate exceeds achievable application payload.',
                       'Decimation needs anti-alias filtering and does not recover capture gaps.',
                       'The complete T8 memory cannot all be assigned to samples in a practical design.',
                       'RP QSPI PSRAM is not directly wired to the FPGA in the reviewed schematic.',
                       'Peripheral DMA address access to the reserved RF dump SRAM needs hardware proof.']}


if __name__ == '__main__':
    print(json.dumps(budget(), indent=2))

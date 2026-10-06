#!/usr/bin/env python3
"""Offline LE1M ADV_EXT_IND primary-header diagnostic; no hardware access.

Private AdvA binds an owned public-address source. No address, ADI value,
AuxPtr value, foreign data or private input pathname is returned. Legacy
receiver functions are cloned with a private parser callback; their source
file and module globals remain unchanged. Search uses only the public AA.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import stat
import time
from types import FunctionType

import numpy as np
import ble_decode_iq as legacy
from esp_sdr_capture import unpack

SPEC = 'https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-54/out/en/low-energy-controller/link-layer-specification.html'
LEGACY_SHA256 = '834fdd78e3221d0625eaa7cf1059b9bd59d3b8b9fa929578f2555bff64130128'
PROFILE = 'extended-primary-zero-data-v1'


def validate_reference(reference):
    if (type(reference) is not dict or reference.get('schema') != 1 or
            type(reference.get('schema')) is not int or
            type(reference.get('address_type')) is not int or reference['address_type'] != 0 or
            type(reference.get('advertising_sid')) is not int or reference['advertising_sid'] != 0 or
            type(reference.get('adva_lsb_first_hex')) is not str or
            re.fullmatch('[0-9a-f]{12}', reference['adva_lsb_first_hex']) is None):
        raise ValueError('private public-AdvA/SID0 reference required')
    address = bytes.fromhex(reference['adva_lsb_first_hex'])
    if address in (bytes(6), bytes([255])*6):
        raise ValueError('unusable private advertiser reference')
    return address


def load_reference(path):
    # Owner-only file, never an address command-line argument/public output.
    path = Path(path)
    if not path.is_file() or stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise ValueError('private reference file must have mode0600')
    reference = json.loads(path.read_text())
    validate_reference(reference)
    return reference


def decode_primary(bits, channel, reference, accept_chsel=False):
    address = validate_reference(reference)
    if channel not in (37, 38, 39):
        raise ValueError('primary advertising channel 37, 38 or 39 required')
    if len(bits) < 16:
        return {'status': 'truncated_header'}
    decoded = legacy.whiten(bits, channel)
    header = legacy.bytes_of(decoded[:16])
    length = header[1]  # Extended PDUs use all8 length bits, unlike legacy.
    if header[0] & 15 != 7 or length < 1:
        return {'status': 'unsupported_or_invalid_header'}
    end = 16+8*length
    if len(decoded) < end+24:
        return {'status': 'truncated_packet', 'pdu_length': length}
    if not np.array_equal(legacy.crc_bits(decoded[:end]), decoded[end:end+24]):
        return {'status': 'crc_failed', 'pdu_length': length}
    packet = legacy.bytes_of(decoded[:end])
    body = packet[2:]
    # RFU bit4/ChSel bit5 are zero. RxAdd is RFU for this undirected profile.
    # accept_chsel: some controllers (observed: this host's Intel adapter) set
    # header bit5 (the ChSel position) on ADV_EXT_IND; v1 rejects it as RFU.
    if header[0] & (0x90 if accept_chsel else 0xb0) or body[0] >> 6 != 0:
        return {'status': 'invalid_primary_profile', 'crc24_ok': True}
    extended_length = body[0] & 63
    if extended_length == 0 or length != extended_length+1:
        return {'status': 'invalid_extended_header_length', 'crc24_ok': True}
    flags = body[1]
    # Table2.4 nonconnectable/non-scannable LE1M ADV_EXT_IND. TargetA,
    # CTEInfo, SyncInfo, RFU, ACAD and AdvData are excluded.
    if flags & ~0x59:
        return {'status': 'invalid_primary_flags', 'crc24_ok': True}
    has_address, has_adi, has_aux, has_power = (bool(flags & flag) for flag in (1, 8, 16, 64))
    if has_adi != has_aux or (not has_aux and not has_address):
        return {'status': 'invalid_primary_field_combination', 'crc24_ok': True}
    if not has_address and header[0] & 0x40:
        return {'status': 'invalid_reserved_txadd', 'crc24_ok': True}
    expected_length = 1+6*has_address+2*has_adi+3*has_aux+has_power
    if extended_length != expected_length:
        return {'status': 'invalid_extended_field_bounds', 'crc24_ok': True}
    cursor = 2
    actual_address = body[cursor:cursor+6] if has_address else None
    cursor += 6*has_address
    sid_ok = True
    if has_adi:
        sid_ok = (int.from_bytes(body[cursor:cursor+2], 'little') >> 12) == reference['advertising_sid']
        cursor += 2
    if has_aux:
        aux = body[cursor:cursor+3]
        # Only general-purpose channel indices0..36; reserved PHYs rejected.
        # This profile requested secondaryLE1M, encoded as0 in AuxPtr.
        if (aux[0] & 63) > 36 or (aux[2] >> 5) != 0:
            return {'status': 'invalid_aux_pointer_profile', 'crc24_ok': True}
        # Core Vol6 PartB §2.3.4.5 / §4.1.2: a nonzero AuxOffset
        # covers this LE1M packet plus T_MAFS=300us. Below245700us
        # OffsetUnits must select30us. Zero is the permitted no-AUX
        # special case with valid remaining fields; it is not proof of
        # a radiated auxiliary packet.
        offset = aux[1] | ((aux[2] & 31) << 8)
        units = 300 if aux[0] & 0x80 else 30
        offset_us = offset*units
        if ((offset and offset_us < 80+8*length+300) or
                (units == 300 and offset_us < 245700)):
            return {'status': 'invalid_aux_pointer_timing', 'crc24_ok': True}
        cursor += 3
    # TxPower's numeric value is controller-selected and does not train the
    # receiver or establish ownership. Its byte is included in full CRC.
    cursor += has_power
    if cursor != length:
        return {'status': 'invalid_extended_field_bounds', 'crc24_ok': True}
    # Public address is explicitly configured. Absent AdvA cannot establish
    # ownership even if an ADI SID matches. Foreign metadata remains redacted.
    owned = has_address and actual_address == address and not (header[0] & 0x40) and sid_ok
    return {'status': 'valid_owned_primary' if owned else 'valid_other_primary_redacted',
            'pdu_type': 7, 'pdu_length': length, 'crc24_ok': True,
            'adv_mode': 0, 'extended_header_length': extended_length,
            'adva_present': has_address, 'owned_public_adva_exact_match': bool(owned),
            'adi_present': has_adi, 'aux_pointer_present': has_aux,
            'tx_power_present': has_power, 'primary_adv_data_length': 0,
            'decoded_with_phy': 'LE1M', 'packet_duration_us': 80+8*length,
            'pdu_sha256': hashlib.sha256(packet).hexdigest() if owned else None,
            'ownership_basis': 'private_public_AdvA_plus_CRC_protected_primary_header' if owned else None}


def make_receiver(reference, accept_chsel=False):
    validate_reference(reference)
    # The pinned code objects share a private global dictionary; no monkey
    # patch of the imported legacy module, no edit to prior pinned decoder.
    actual = hashlib.sha256(Path(legacy.__file__).read_bytes()).hexdigest()
    if actual != LEGACY_SHA256:
        raise ValueError('legacy receiver source does not match pinned revision')
    reference = reference.copy()
    scope = vars(legacy).copy()
    scope['decode_packet'] = lambda bits, channel, marker_ad=None: decode_primary(bits, channel, reference, accept_chsel)
    scope['refine_packet'] = FunctionType(legacy.refine_packet.__code__, scope,
                                         'refine_packet', legacy.refine_packet.__defaults__)
    return FunctionType(legacy.decode_iq.__code__, scope, 'decode_iq', legacy.decode_iq.__defaults__)


def decode_primary_iq(iq, reference, rate=16000000, frequency_translation_hz=-1000000, accept_chsel=False, channel=37):
    if not math.isfinite(frequency_translation_hz) or abs(frequency_translation_hz) >= rate/2:
        raise ValueError('finite frequency translation inside Nyquist interval required')
    receiver = make_receiver(reference, accept_chsel)
    frames = receiver(iq, rate, channel, b'', frequency_translation_hz, True)
    down = rate//4000000
    for frame in frames:
        if not frame['status'].startswith('valid'):
            continue
        # Coarse receiver candidates already CRC-pass; record their exact
        # four-sample slicing period and full nominal window as for refinement.
        period = frame.get('samples_per_symbol_at_4msps', 4.0)
        offset = frame['access_address_sample_offset']
        beginning = offset-8*period*down
        ending = offset+(frame['packet_duration_us']-8)*period*down
        frame.update(samples_per_symbol_at_4msps=period,
                     refined=frame.get('refined', False),
                     nominal_packet_start_sample=beginning,
                     nominal_packet_end_sample=ending,
                     complete_preamble_and_pdu_crc_within_capture_nominal=bool(
                         beginning >= 0 and ending <= (int(np.ceil(len(iq)/down))-1)*down))
    return frames


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--input', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    cli.add_argument('--owned-reference', type=Path, required=True)
    cli.add_argument('--rate', type=int, choices=[16000000, 40000000, 80000000], default=16000000)
    cli.add_argument('--bits', type=int, choices=[8, 10], default=8)
    cli.add_argument('--samples', type=int, choices=[16380], default=16380)
    cli.add_argument('--frequency-translation-hz', type=float, default=-1000000)
    cli.add_argument('--channel', type=int, choices=[37, 38, 39], default=37)
    cli.add_argument('--accept-chsel', action='store_true',
                     help='Accept header bit5 (ChSel position) on ADV_EXT_IND; default v1 rejects it as RFU')
    args = cli.parse_args(argv)
    if args.output.exists():
        cli.error('choose a fresh output file')
    reference = load_reference(args.owned_reference)
    files = sorted(args.input.glob('*.bin')) if args.input.is_dir() else [args.input]
    if not files:
        cli.error('no private waveforms found')
    started = time.monotonic()
    result = {'schema': 1, 'profile': PROFILE, 'primary_protocol_source': SPEC,
              'decoder_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'receiver_source_sha256': LEGACY_SHA256, 'channel': args.channel,
              'nominal_rate_hz': args.rate, 'bits_per_component': args.bits,
              'samples_per_capture': args.samples,
              'frequency_translation_hz': args.frequency_translation_hz,
              'accept_chsel_header_bit': args.accept_chsel,
              'blind_receiver_refinement': legacy.REFINEMENT,
              'private_owned_reference_used': True, 'captures': [],
              'independently_observed_air_emission_count': None,
              'limitations': 'Primary-header diagnostic only; CRC and private AdvA ownership do not count air emissions, calibrate clocks, follow AUX, establish reception rates or satisfy legacy TrialB.'}
    for index, path in enumerate(files):
        payload = path.read_bytes()
        frames = decode_primary_iq(unpack(payload, args.samples, args.bits), reference,
                                   args.rate, args.frequency_translation_hz, args.accept_chsel, args.channel)
        owned = [f for f in frames if f['status'] == 'valid_owned_primary']
        result['captures'].append({'capture_index': index, 'capture_filename': path.name,
                                   'payload_sha256': hashlib.sha256(payload).hexdigest(), 'frames': frames,
                                   'owned_primary_cluster_count': len(owned),
                                   'source_event_attribution_ambiguous': len(owned) > 1})
    result['captures_analyzed'] = len(files)
    result['crc_valid_owned_primary_candidates'] = sum(f['status'] == 'valid_owned_primary'
        for c in result['captures'] for f in c['frames'])
    result['complete_owned_primary_candidate_captures'] = sum(any(
        f['status'] == 'valid_owned_primary' and f['complete_preamble_and_pdu_crc_within_capture_nominal']
        for f in c['frames']) for c in result['captures'])
    # These are decoder diagnostics, not a physical event numerator. Whole
    # acquisition brackets/source joins and ambiguity checks belong in review.
    result['runtime_seconds'] = time.monotonic()-started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('captures_analyzed',
          'crc_valid_owned_primary_candidates', 'complete_owned_primary_candidate_captures')}))


if __name__ == '__main__':
    main()

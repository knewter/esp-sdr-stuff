#!/usr/bin/env python3
"""Offline FPGA register lifecycle controller and bounded worker ownership.

No physical backend, FPGA configuration writer or load/program CLI exists here.
Injected adapters exercise ordering and failure policy. A future physical
adapter must verify actual artifacts, qualification, identity, preservation and
recovery; adapter receipts alone are not physical evidence.
"""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import time

from demo_esp_sdr import OwnedHardwareClosureError
from forgix_usb_ram_capture import inherited_operator_lock
from forgix_usb_ram_trial import owned_worker, no_symlinks


class LifecycleError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise LifecycleError(message)


class WorkerOwner:
    """Contain serial/open/kernel calls in an inherited-lock process group.

    Reuse the existing trial's spawn-cancellation protection and whole-group
    cleanup. Leader exit alone is insufficient. Unknown closure blocks every
    subsequent worker; the underlying helper retains its shared unclosed marker.
    The lifecycle caller must additionally freeze/qualify command inputs.
    """
    def __init__(self, directory, lockfd, lockpath, clock=time.monotonic):
        self.directory = no_symlinks(directory)
        info = self.directory.stat()
        require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode)==0o700
                and info.st_uid==os.getuid(), 'Owned private 0700 worker directory required')
        self.lockfd, self.lockpath, self.clock = lockfd, Path(lockpath), clock
        self.closed = True
        self.count = 0

    def run(self, command, label, deadline):
        if not self.closed:
            raise OwnedHardwareClosureError('Unknown prior worker closure blocks access')
        require(re.fullmatch(r'[a-z][a-z0-9-]{0,39}', label) is not None,
                'Bounded worker label required')
        require(self.count < 16, 'Finite worker count exhausted')
        inherited_operator_lock(self.lockfd, self.lockpath)
        left = deadline-self.clock()
        require(left > 0, 'Worker deadline expired before spawn')
        log = self.directory/f'{self.count:02d}-{label}.log'
        self.count += 1
        self.closed = False
        try:
            code = owned_worker(command, log, self.lockfd, left)
        except OwnedHardwareClosureError:
            raise
        except BaseException:
            # The helper raises this path only after verified group cleanup.
            self.closed = True
            raise
        else:
            self.closed = True
            require(self.clock() < deadline, 'Worker completed after its deadline')
            require(code == 0, 'Worker failed; private log retained')
            return {'exit_code': code, 'owned_processes_closed': True}


class Lifecycle:
    """One finite session with an injected adapter and private event sink.

    Adapter interface: owner.closed, cleaning, check_inputs(), admit(deadline),
    preserve_before(deadline), configure(deadline), enter_rom(deadline),
    load_ram(deadline), transition(deadline), collect(deadline),
    return_factory(deadline), preserve_after(deadline).

    The two configuration strategies are modeled, not admitted on hardware.
    The actual bridge has no configuration writer. A physical adapter must
    provide its reviewed implementation and qualification before using this
    controller. write_event must durably retain private intent/result records.
    """
    def __init__(self, adapter, write_event, clock=time.monotonic):
        self.adapter, self.write_event, self.clock = adapter, write_event, clock
        self.used = False
        self.recovery_required = False
        self.cleaning = False
        self.events = []
        self.summary = {'status':'incomplete', 'model_policy_only':True,
                        'physical_qualification_proved':False,
                        'physical_execution_admitted':False,
                        'original_flash_and_factory_verified':False,
                        'owned_processes_closed':True}

    def closed(self):
        if self.adapter.owner.closed is not True:
            self.summary['owned_processes_closed'] = False
            raise OwnedHardwareClosureError('Unverified owned closure blocks device access')

    def within(self, until):
        require(self.clock() < until, 'Absolute lifecycle/stage deadline expired')

    def event(self, value):
        self.write_event(value)
        self.events.append(value)

    def stage(self, name, function, maximum, mutates=False):
        self.closed()
        ceiling = self.deadline if self.cleaning else self.work_deadline
        until = min(ceiling, self.clock()+maximum)
        self.within(until)
        self.adapter.check_inputs()
        self.within(until)
        self.event({'stage':name, 'phase':'intent', 'host_s':self.clock(),
                    'deadline':until, 'may_change_mode_or_fpga':mutates})
        self.within(until)
        # Persist intent before the possibly consumed request. A lost ACK does
        # not remove the need for factory/full-flash verification afterward.
        if mutates:
            self.recovery_required = True
        try:
            receipt = function(until)
        except BaseException as exc:
            self.closed()
            self.event({'stage':name, 'phase':'failed', 'error_kind':type(exc).__name__,
                        'host_s':self.clock()})
            raise
        self.closed()
        self.within(until)
        self.event({'stage':name, 'phase':'returned', 'host_s':self.clock(),
                    'receipt':receipt})
        self.within(until)
        return receipt

    def preservation(self, receipt):
        p = self.profile
        require(type(receipt) is dict and receipt.get('uid_sha256') == p['uid_sha256'],
                'Preservation must bind the original MCU identity')
        require(type(receipt.get('flash_bytes')) is int and receipt['flash_bytes'] == 2097152,
                'Preservation must cover the complete 2 MiB range')
        require(receipt.get('read_sha256') == [p['baseline_sha256']]*2,
                'Two independent full reads must match the original baseline')
        require(receipt.get('independent_device_verify') is True and
                receipt.get('factory_application_verified') is True,
                'Separate device comparison and factory application verification required')

    def configure(self):
        receipt = self.stage('configure', self.adapter.configure, 60, mutates=True)
        require(type(receipt) is dict and receipt.get('bitstream_sha256') == self.profile['bitstream_sha256'],
                'Configuration must bind the exact qualified image')

    def run(self):
        require(not self.used, 'One lifecycle run per controller')
        self.used = True
        began = self.clock()
        self.deadline = began+600
        # Reserve return140 + full preservation180 + final checks5 seconds.
        self.work_deadline = self.deadline-325
        error = None
        recovery_error = None
        try:
            self.profile = self.stage('admit', self.adapter.admit, 30)
            require(type(self.profile) is dict, 'Admission profile required')
            for name in ('uid_sha256','baseline_sha256','elf_sha256',
                         'bridge_source_sha256','bitstream_sha256'):
                value = self.profile.get(name)
                require(type(value) is str and re.fullmatch('[0-9a-f]{64}',value),
                        'Exact qualification/artifact identity required')
            require(self.profile.get('qualification_verified') is True,
                    'Physical/artifact qualification remains required')
            strategy = self.profile.get('configuration_strategy')
            require(strategy in ('qualified_retention','after_ram_startup'),
                    'Explicit qualified configuration strategy required')
            self.preservation(self.stage('preserve-before', self.adapter.preserve_before, 180))
            if strategy == 'qualified_retention':
                self.configure()
            self.stage('enter-rom', self.adapter.enter_rom, 30, mutates=True)
            loaded = self.stage('load-ram', self.adapter.load_ram, 60, mutates=True)
            require(type(loaded) is dict and loaded.get('elf_sha256') == self.profile['elf_sha256'],
                    'RAM load must bind the reviewed ELF')
            if strategy == 'after_ram_startup':
                self.configure()
            transition = self.stage('transition', self.adapter.transition, 20)
            require(type(transition) is dict and transition.get('bitstream_sha256') == self.profile['bitstream_sha256']
                    and transition.get('configuration_continuity_verified') is True,
                    'CDONE alone cannot establish configuration identity/continuity')
            captured = self.stage('collect', self.adapter.collect, 45)
            require(type(captured) is dict and captured.get('status') == 'registers_verified'
                    and captured.get('build_source_sha256') == self.profile['bridge_source_sha256']
                    and captured.get('persistence_verified') is True
                    and captured.get('transport_closed') is True,
                    'Collector identity, persisted prefix and serial closure must pass')
            register = captured.get('register_run', {})
            require(type(register) is dict and register.get('result') == 'passed'
                    and register.get('scratch_restore_verified') is True
                    and register.get('finish_reply_verified') is True,
                    'Verified scratch restoration and FINISH required')
            self.summary['registers_verified'] = True
        except BaseException as exc:
            error = exc
            self.summary['error_kind'] = type(exc).__name__
        finally:
            self.cleaning = True
            self.adapter.cleaning = True
            if self.recovery_required:
                try:
                    self.closed()
                    self.stage('return-factory', self.adapter.return_factory, 140)
                    self.preservation(self.stage('preserve-after', self.adapter.preserve_after, 180))
                    self.summary['original_flash_and_factory_verified'] = True
                except BaseException as exc:
                    recovery_error = exc
                    self.summary['recovery_error_kind'] = type(exc).__name__
                    self.summary['manual_recovery_required'] = True
            try:
                self.closed()
                self.adapter.check_inputs()
                self.within(self.deadline)
            except BaseException as exc:
                recovery_error = recovery_error or exc
                self.summary['final_check_error_kind'] = type(exc).__name__
            self.summary.update(status='model_completed' if error is None and recovery_error is None
                                and self.summary.get('registers_verified') is True
                                and self.summary['original_flash_and_factory_verified'] else 'failed',
                                recovery_required=self.recovery_required,
                                host_elapsed_s=self.clock()-began)
            try:
                self.event({'phase':'terminal', 'receipt':dict(self.summary)})
            except BaseException as exc:
                self.summary.update(status='failed', terminal_error_kind=type(exc).__name__)
                raise
            if self.clock() >= self.deadline:
                self.summary.update(status='failed', final_check_error_kind='LifecycleError',
                                    host_elapsed_s=self.clock()-began)
                self.event({'phase':'late-terminal', 'receipt':dict(self.summary)})
        for exc in (error, recovery_error):
            if exc is not None and not isinstance(exc, Exception):
                raise exc
        return self.summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    from build_forgix_usb_ram import fresh
    folder = fresh(args.plan)
    plan = {'kind':'offline FPGA lifecycle plan', 'hardware_opened':False,
            'loading_admitted':False, 'physical_backend_implemented':False,
            'required_stages':['qualification','fresh full preservation','configuration strategy',
                               'identity-selected ROM/RAM load','configuration transition',
                               'bounded collector group','group closure','factory return',
                               'fresh full preservation and independent device verify'],
            'remaining':['actual FPGA grade/clock/timing','configuration transition qualification',
                         'reviewed physical adapter and frozen artifact/configuration inputs'],
            'scope':'Controller/process ownership preparation only; no physical trial or FPGA throughput claim.'}
    (folder/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps(plan))


if __name__ == '__main__':
    main()

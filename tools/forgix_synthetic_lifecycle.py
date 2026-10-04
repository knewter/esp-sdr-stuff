"""One finite stream lifecycle; preservation recovery is independent of stream success."""
import re
import time
from forgix_spi_lifecycle import Lifecycle as CommonLifecycle, require
from demo_esp_sdr import OwnedHardwareClosureError

class Lifecycle(CommonLifecycle):
    def run(self,began=None):
        require(not self.used,'One synthetic lifecycle');self.used=True
        began=self.clock() if began is None else began
        self.deadline=began+600;self.work_deadline=self.deadline-325
        error=None;recovery_error=None
        self.summary.update(model_policy_only=True,physical_execution_admitted=False,
                            synthetic_lossless_verified=False)
        try:
            self.profile=self.stage('admit',self.adapter.admit,30)
            require(self.profile.get('qualification_verified') is True,'Synthetic qualification required')
            for name in ('uid_sha256','baseline_sha256','elf_sha256','bridge_source_sha256','bitstream_sha256'):
                require(type(self.profile.get(name)) is str and re.fullmatch('[0-9a-f]{64}',self.profile[name]),'Exact synthetic identity required')
            self.preservation(self.stage('preserve-before',self.adapter.preserve_before,180,mutates=True))
            self.stage('enter-rom',self.adapter.enter_rom,30,mutates=True)
            load=self.stage('load-ram',self.adapter.load_ram,30,mutates=True)
            require(load.get('elf_sha256')==self.profile['elf_sha256'],'Synthetic load differs')
            # One worker includes USB readiness, CONFIG, START, stream and END.
            result=self.stage('stream',self.adapter.stream,120,mutates=True)
            require(result.get('status')=='lossless' and result.get('transport_closed') is True
                    and result.get('persistence_verified') is True and result.get('replay',{}).get('lossless') is True,
                    'Whole saved stream/replay/closure not lossless')
            for k,v in (('build_sha256',self.profile['bridge_source_sha256']),('image_sha256',self.profile['bitstream_sha256']),
                        ('nonce',self.profile['nonce']),('period',self.profile['period']),('target',self.profile['target'])):
                require(type(result.get(k)) is type(v) and result[k]==v,'Terminal stream binding differs')
            self.summary['synthetic_lossless_verified']=True
        except BaseException as exc:
            error=exc;self.summary['error_kind']=type(exc).__name__
        finally:
            self.cleaning=self.adapter.cleaning=True
            if self.recovery_required:
                try:
                    self.closed()
                    self.stage('return-factory',self.adapter.return_factory,140)
                    self.preservation(self.stage('preserve-after',self.adapter.preserve_after,180))
                    self.summary['original_flash_and_factory_verified']=True
                except BaseException as exc:
                    recovery_error=exc;self.summary.update(recovery_error_kind=type(exc).__name__,manual_recovery_required=True)
            try:
                self.closed();self.adapter.check_inputs();self.within(self.deadline)
            except BaseException as exc:
                recovery_error=recovery_error or exc;self.summary['final_check_error_kind']=type(exc).__name__
            self.summary.update(status='synthetic_completed' if error is None and recovery_error is None
                 and self.summary['synthetic_lossless_verified'] and self.summary['original_flash_and_factory_verified'] else 'failed',
                 recovery_required=self.recovery_required,host_elapsed_s=self.clock()-began)
            try:self.event({'phase':'terminal','receipt':dict(self.summary)})
            except BaseException as exc:
                self.summary.update(status='failed',terminal_error_kind=type(exc).__name__);raise
            if self.clock()>=self.deadline:
                self.summary.update(status='failed',final_check_error_kind='TimeoutError',host_elapsed_s=self.clock()-began)
                self.event({'phase':'late-terminal','receipt':dict(self.summary)})
        for exc in (error,recovery_error):
            if exc is not None and not isinstance(exc,Exception):raise exc
        return self.summary

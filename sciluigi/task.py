import luigi
import audit
from util import *
import dependencies
import time
import random
import slurm
import string
from collections import namedtuple

# ==============================================================================

def new_task(name, cls, workflow_task, **kwargs): # TODO: Raise exceptions if params not of right type
    for k, v in [(k,v) for k,v in kwargs.iteritems()]:
        # Handle non-string keys
        if not isinstance(k, basestring):
            raise Exception("Key in kwargs to new_task is not string. Must be string: %s" % k)
        # Handle non-string values
        slurminfo = None
        if isinstance(v, slurm.SlurmInfo):
            slurminfo = v
            kwargs[k] = v
        elif not isinstance(v, basestring):
            kwargs[k] = str(v) # Force conversion into string
    kwargs['instance_name'] = name
    kwargs['workflow_task'] = workflow_task
    t = cls.from_str_params(kwargs)
    if slurminfo is not None:
        t.slurminfo = slurminfo
    return t

class Task(audit.AuditTrailHelpers, dependencies.DependencyHelpers, luigi.Task):
    workflow_task = luigi.Parameter()
    instance_name = luigi.Parameter()

    def ex_local(self, command):
        # If list, convert to string
        if isinstance(command, list):
            command = ' '.join(command)

        log.info('Executing command: ' + str(command))
        (status, output) = commands.getstatusoutput(command) # TODO: Replace with subprocess call!

        # Take care of errors
        if status != 0:
            msg = 'Command failed: {cmd}\nOutput:\n{output}'.format(cmd=command, output=output)
            log.error(msg)
            raise Exception(msg)

        return (status, output)

    def ex(self, command):
        '''
        This is a short-hand function, to be overridden e.g. if supporting execution via SLURM
        '''
        return self.ex_local(command)

# ==============================================================================

class ExternalTask(audit.AuditTrailHelpers, dependencies.DependencyHelpers, luigi.ExternalTask):
    workflow_task = luigi.Parameter()
    instance_name = luigi.Parameter()

# ==============================================================================

class WorkflowTask(audit.AuditTrailHelpers, luigi.Task):

    _auditlog = []

    def workflow(self):
        raise WorkflowNotImplementedException('workflow() method is not implemented, for ' + str(self))

    def requires(self):
        return self.workflow()

    def output(self):
        timestamp = time.strftime('%Y%m%d_%H%M%S', time.localtime())
        clsname = self.__class__.__name__
        return luigi.LocalTarget('workflow_' + clsname.lower() + '_completed_at_{t}.txt'.format(t=timestamp))

    def run(self):
        with self.output().open('w') as outfile:
            outfile.writelines([line + '\n' for line in self._auditlog])
            outfile.write('-'*80 + '\n')
            outfile.write('{time}: {wfname} workflow finished\n'.format(
                            wfname=self.task_family,
                            time=timelog()))

    def new_task(self, instance_name, cls, **kwargs):
        return new_task(instance_name, cls, self, **kwargs)

    def log_audit(self, line):
        self._auditlog.append(line)


class WorkflowNotImplementedException(Exception):
    pass

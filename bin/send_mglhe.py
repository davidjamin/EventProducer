#python bin/run.py --FCC --LHE --send --version fcc_v02 -p dummy --typelhe mg --mg5card pp_hh.mg5 --model loop_sm_hh.tar -N 2 -n 10000 -q workday --condor

#!/usr/bin/env python
import os, sys
import commands
import time
import EventProducer.common.utils as ut
import EventProducer.common.makeyaml as my

class send_mglhe():

#__________________________________________________________
    def __init__(self, islsf, iscondor, mg5card, cutfile, model, para, procname, njobs, nev, queue, memory, disk):
        self.islsf     = islsf
        self.iscondor  = iscondor
        self.user      = os.environ['USER']
        self.mg5card   =  mg5card
        self.cutfile   =  cutfile
        self.model     =  model
        self.para      =  para
        self.procname  =  procname
        self.njobs     =  njobs
        self.nev       =  nev
        self.queue     =  queue
        self.memory    =  memory
        self.disk      =  disk

#__________________________________________________________
    def send(self):
        Dir = os.getcwd()
        nbjobsSub=0

        # output dir
        outdir=self.para.lhe_dir

        logdir=Dir+"/BatchOutputs/lhe/%s"%(self.procname)
        if not ut.dir_exist(logdir):
            os.system("mkdir -p %s"%logdir)

        yamldir = '%s/lhe/%s'%(self.para.yamldir,self.procname)
        if not ut.dir_exist(yamldir):
            os.system("mkdir -p %s"%yamldir)

        outdir  = os.path.abspath(outdir)
        mg5card = os.path.abspath(self.mg5card)
        cuts    = os.path.abspath(self.cutfile)
        model   = os.path.abspath(self.model)

        jobsdir = './BatchOutputs/lhe/' + self.procname

        if not os.path.exists(jobsdir):
           os.makedirs(jobsdir)
           os.makedirs(jobsdir+'/std/')
           os.makedirs(jobsdir+'/cfg/')

        if self.islsf==False and self.iscondor==False:
            print "Submit issue : LSF nor CONDOR flag defined !!!"
            sys.exit(3)

        condor_file_params_str=[]
        while nbjobsSub<self.njobs:
            #uid = int(ut.getuid(self.user))
            uid = ut.getuid2(self.user)
            myyaml = my.makeyaml(yamldir, uid)
            if not myyaml: 
                print 'job %s already exists'%uid
                continue

            if ut.file_exist('%s/%s/events_%s.lhe.gz'%(outdir,self.procname,uid)):
                print 'already exist, continue'
                continue
    
            print 'Submitting job '+str(nbjobsSub)+' out of '+str(self.njobs)
            seed = str(uid)
            basename =  self.procname+ '_'+seed

	    cwd = os.getcwd()
	    script = cwd + '/bin/submitMG.sh '

            if self.islsf==True :
              cmdBatch = 'bsub -o '+jobsdir+'/std/'+basename +'.out -e '+jobsdir+'/std/'+basename +'.err -q '+self.queue
              cmdBatch += ' -R "rusage[mem={}:pool={}]"'.format(self.memory,self.disk)
              cmdBatch +=' -J '+basename +' "'+script + mg5card+' '+self.procname+' '+outdir+' '+seed+' '+str(self.nev)+' '+cuts+' '+model+'"'

              print cmdBatch

              batchid=-1
              job,batchid=ut.SubmitToLsf(cmdBatch,10,1)
              nbjobsSub+=job
            elif self.iscondor==True :
              condor_file_params_str.append(mg5card+' '+self.procname+' '+outdir+' '+seed+' '+str(self.nev)+' '+cuts+' '+model)
              nbjobsSub+=1

        if self.iscondor==True :
            # parameter file
            fparamname_condor = 'job_params_mglhe.txt'
            fparamfull_condor = '%s/%s'%(logdir,fparamname_condor)
            fparam_condor = None
            try:
                fparam_condor = open(fparamfull_condor, 'w')
            except IOError as e:
                print "I/O error({0}): {1}".format(e.errno, e.strerror)
                time.sleep(10)
                fparam_condor = open(fparamfull_condor, 'w')
            for line in condor_file_params_str:
                fparam_condor.write('%s\n'%line)
            fparam_condor.close()
            # condor config
            frunname_condor = 'job_desc_mglhe.cfg'
            frunfull_condor = '%s/%s'%(logdir,frunname_condor)
            frun_condor = None
            try:
                frun_condor = open(frunfull_condor, 'w')
            except IOError as e:
                print "I/O error({0}): {1}".format(e.errno, e.strerror)
                time.sleep(10)
                frun_condor = open(frunfull_condor, 'w')
            commands.getstatusoutput('chmod 777 %s'%frunfull_condor)
            #
            frun_condor.write('executable     = %s\n'%script)
            frun_condor.write('Log            = %s/condor_job.%s.$(ClusterId).$(ProcId).log\n'%(logdir,str(uid)))
            frun_condor.write('Output         = %s/condor_job.%s.$(ClusterId).$(ProcId).out\n'%(logdir,str(uid)))
            frun_condor.write('Error          = %s/condor_job.%s.$(ClusterId).$(ProcId).error\n'%(logdir,str(uid)))
            frun_condor.write('getenv         = True\n')
            frun_condor.write('environment    = "LS_SUBCWD=%s"\n'%logdir) # not sure
            frun_condor.write('request_memory = %s\n'%self.memory)
#            frun_condor.write('requirements   = ( (OpSysAndVer =?= "CentOS7") && (Machine =!= LastRemoteHost) )\n')
            frun_condor.write('requirements   = ( (OpSysAndVer =?= "SLCern6") && (Machine =!= LastRemoteHost) )\n')
            frun_condor.write('on_exit_remove = (ExitBySignal == False) && (ExitCode == 0)\n')
            frun_condor.write('max_retries    = 3\n')
            frun_condor.write('+JobFlavour    = "%s"\n'%self.queue)
            frun_condor.write('+AccountingGroup = "group_u_FCC.local_gen"\n')
            frun_condor.write('queue arguments from %s\n'%fparamfull_condor)
            frun_condor.close()
            #
            nbjobsSub=0
            cmdBatch="condor_submit %s"%frunfull_condor
            print cmdBatch
            job=ut.SubmitToCondor(cmdBatch,10,"%i/%i"%(nbjobsSub,self.njobs))
            nbjobsSub+=job

        print 'succesfully sent %i  job(s)'%nbjobsSub


"""Run a real, resumable Codex execution inside the user-requested tmux session."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,json,os,select,signal,subprocess,sys,time

ROOT=Path(__file__).resolve().parents[3]
JOB=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'.git/visual-loop'
PRIVATE.mkdir(exist_ok=True)
lock=(PRIVATE/'runner.lock').open('w')
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:raise SystemExit('A visual runner is already active')
config=json.loads((PRIVATE/'runtime-config.json').read_text())
state_path=PRIVATE/'runtime-status.json'
state=json.loads(state_path.read_text()) if state_path.exists() else {}
servers=[]

def utc():return datetime.now(timezone.utc).isoformat()

def log(message):
    line=utc()+' '+message
    print(line,flush=True)
    with (PRIVATE/'progress.log').open('a') as f:f.write(line+'\n')

def save(**fields):
    state.update(fields);state['heartbeat']=utc()
    temp=PRIVATE/'runtime-status.tmp';temp.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n');temp.replace(state_path)

def ensure_server(port,directory):
    import socket
    sock=socket.socket();occupied=sock.connect_ex(('127.0.0.1',port))==0;sock.close()
    if occupied:
        # Never stop an unknown service. Reuse only a port from an earlier run of this job.
        old_pid=state.get('servers',{}).get(str(port))
        assert old_pid and Path(f'/proc/{old_pid}/cmdline').exists(),'Port already occupied: '+str(port)
        command=Path(f'/proc/{old_pid}/cmdline').read_bytes().replace(b'\0',b' ').decode()
        assert str(directory) in command and 'http.server' in command,'Unexpected server on '+str(port)
        return old_pid
    stream=(PRIVATE/f'server-{port}.log').open('ab')
    proc=subprocess.Popen([sys.executable,'-m','http.server',str(port),'--bind','127.0.0.1','--directory',str(directory)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    servers.append(proc);return proc.pid

def completed():
    proc=subprocess.run([sys.executable,str(JOB/'scripts/verify_completion.py')],cwd=ROOT,text=True,capture_output=True)
    with (PRIVATE/'finish-gate.json').open('w') as f:f.write(proc.stdout or proc.stderr)
    return proc.returncode==0,proc.stdout[-5000:]

save(status='starting',pid=os.getpid(),tmuxSession='lens-visual-loop',job=str(JOB.relative_to(ROOT)),startedAt=state.get('startedAt',utc()))
try:
    owned={str(port):ensure_server(port,directory)for port,directory in [(8818,ROOT/'app/dist'),(8819,PRIVATE/'baseline-dist')]}
    save(servers=owned)
    env=os.environ.copy();env['CODEX_HOME']=config['codexHome'];env['PATH']=config['path']
    for key in ['CODEX_THREAD_ID','CODEX_SESSION_ID','CODEX_TOOL_CALL_ID']:env.pop(key,None)
    base=[config['codexExecutable'],'exec','-C',str(ROOT),'-s','danger-full-access','-c','approval_policy="never"','--disable','multi_agent','--disable','unbounded_connection_retries','--json']
    initial=('You are executing the user-authorized detached full-site visual optimization job. Fully read '+str(JOB/'TASK.md')+' and '+str(JOB/'PLAN.md')+' before changing any production source. Carry out the entire loop, use actual image generation, preserve all protected charts/data, maintain STATUS.md, and finish with real browser/online checks. The supervisor will independently verify the documented completion contract. Do not ask the offline user to respond, do not stop at a plan, and do not spawn subagents.')
    for attempt in range(1,5):
        ok,reason=completed()
        if ok:save(status='completed',verification=json.loads(reason));log('COMPLETED: independent finish gate passed.');break
        session=state.get('threadId')
        prompt=initial if not session else ('Continue the full task from the saved STATUS.md and ledger; do not repeat completed stages. Independent finish gate has not passed: '+reason+'. Finish all actual remaining work. Do not modify run_background.py or verify_completion.py to bypass the gate. Ensure completion.json includes exactly five planetAssets paths with real transparent images used by the live home/intro. Keep the final work committed and deployment verified.')
        last_message=PRIVATE/f'last-message-{attempt}.md'
        command=[*base,'-o',str(last_message),*(['resume',session,'-']if session else['-'])]
        events=PRIVATE/f'events-{attempt}.jsonl';stderr=(PRIVATE/f'stderr-{attempt}.log').open('ab')
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=stderr,text=True,bufsize=1,start_new_session=True)
        child.stdin.write(prompt+'\n');child.stdin.close()
        save(status='running',attempt=attempt,childPid=child.pid,eventLog=str(events.relative_to(ROOT)),lastGate=reason)
        log(f'RUNNING attempt={attempt} codex_pid={child.pid} thread={session or "new"}')
        with events.open('a',buffering=1) as target:
            last_heartbeat=time.monotonic()
            while child.poll() is None:
                ready,_,_=select.select([child.stdout],[],[],5)
                if ready:
                    line=child.stdout.readline()
                    if line:
                        target.write(line)
                        try:
                            event=json.loads(line)
                            if event.get('type')=='thread.started':save(threadId=event['thread_id']);log('THREAD '+event['thread_id'])
                            item=event.get('item',{})
                            if item.get('type')=='agent_message' and event.get('type')=='item.completed':log(item.get('text','')[:4500])
                            elif event.get('type')=='item.started':log('TOOL '+item.get('type','unknown'))
                            elif event.get('type') in ['turn.failed','error']:log('MODEL_EVENT '+line.strip()[:2000])
                        except json.JSONDecodeError:pass
                if time.monotonic()-last_heartbeat>=30:save();last_heartbeat=time.monotonic()
            remainder=child.stdout.read()
            if remainder:
                target.write(remainder)
                for line in remainder.splitlines():
                    try:
                        event=json.loads(line)
                        if event.get('type')=='thread.started':save(threadId=event['thread_id'])
                    except json.JSONDecodeError:pass
        stderr.close();save(exitCode=child.returncode)
        ok,reason=completed()
        if ok:save(status='completed',verification=json.loads(reason));log('COMPLETED: independent finish gate passed.');break
        log('NOT FINISHED: '+reason)
        save(status='retry_wait',lastGate=reason)
        if attempt<4:time.sleep(min(30*attempt,90))
    else:
        save(status='needs_attention',reason='Four bounded execution/resume attempts ended without passing the finish gate.')
        log('NEEDS ATTENTION: saved all progress, logs and session ID; no false completion claim.')
except BaseException as error:
    save(status='failed',reason=repr(error));log('FAILED '+repr(error));raise
finally:
    save()
    # Keep owned previews available for review; leave unrelated services untouched.
    log('Runner ended with status='+state.get('status','unknown'))

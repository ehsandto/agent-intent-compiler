# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import hashlib
import json

MAX_BODY=24000
MAX_STEPS=20
POLICY="agent-intent-compiler-v1-exact-vector"

@allow_storage
@dataclass
class Intent:
    owner: Address
    planner: Address
    planner_accepted: bool
    goal: str
    constraints_json: str
    forbidden_json: str
    intent_url: str
    intent_hash: str
    reserved_version: u64
    active_plan: str
    latest_plan: str
    state: str

@allow_storage
@dataclass
class Plan:
    intent_id: str
    version: u64
    parent_plan: str
    proposer: Address
    plan_url: str
    plan_hash: str
    state: str
    report_json: str
    fingerprint: str

class AgentIntentCompiler(gl.Contract):
    intents: TreeMap[str,Intent]
    intent_exists: TreeMap[str,bool]
    plans: TreeMap[str,Plan]
    plan_exists: TreeMap[str,bool]
    version_reserved: TreeMap[str,bool]

    def __init__(self)->None: pass

    @gl.public.write
    def create_intent(self,intent_id:str,planner:Address,goal:str,constraints_json:str,forbidden_json:str,intent_url:str,intent_hash:str)->None:
        iid=self._id(intent_id)
        if self.intent_exists.get(iid,False): raise gl.vm.UserError("EXPECTED: intent exists")
        other=Address(str(planner))
        if other==gl.message.sender_address: raise gl.vm.UserError("EXPECTED: independent planner")
        constraints=self._strings(constraints_json,"constraints",1,12); forbidden=self._strings(forbidden_json,"forbidden actions",0,12)
        self.intents[iid]=Intent(gl.message.sender_address,other,False,self._text(goal,"goal"),json.dumps(constraints,separators=(",",":")),json.dumps(forbidden,separators=(",",":")),self._url(intent_url),self._hash(intent_hash),u64(0),"","","AWAITING_PLANNER")
        self.intent_exists[iid]=True

    @gl.public.write
    def accept_assignment(self,intent_id:str)->None:
        iid=self._id(intent_id); item=self._intent(iid)
        if gl.message.sender_address!=item.planner: raise gl.vm.UserError("EXPECTED: assigned planner only")
        if item.planner_accepted: raise gl.vm.UserError("EXPECTED: assignment accepted")
        item.planner_accepted=True; item.state="READY_FOR_PLAN"; self.intents[iid]=item

    @gl.public.write
    def submit_plan(self,plan_id:str,intent_id:str,version:u64,parent_plan:str,plan_url:str,plan_hash:str)->None:
        pid=self._id(plan_id); iid=self._id(intent_id); item=self._intent(iid)
        if gl.message.sender_address!=item.planner or not item.planner_accepted: raise gl.vm.UserError("EXPECTED: accepted planner only")
        if self.plan_exists.get(pid,False): raise gl.vm.UserError("EXPECTED: plan exists")
        expected=int(item.reserved_version)+1
        if int(version)!=expected: raise gl.vm.UserError("EXPECTED: next version required")
        parent=parent_plan.strip()
        if (expected==1 and len(parent)>0) or (expected>1 and parent!=item.latest_plan): raise gl.vm.UserError("EXPECTED: invalid parent")
        slot=iid+":"+str(expected)
        if self.version_reserved.get(slot,False): raise gl.vm.UserError("EXPECTED: version reserved")
        self.plans[pid]=Plan(iid,version,parent,gl.message.sender_address,self._url(plan_url),self._hash(plan_hash),"SUBMITTED","",""); self.plan_exists[pid]=True; self.version_reserved[slot]=True
        item.reserved_version=version; item.latest_plan=pid; item.state="PLAN_SUBMITTED"; self.intents[iid]=item

    @gl.public.write
    def compile_intent(self,plan_id:str)->None:
        pid=self._id(plan_id); plan=self._plan(pid); intent=self._intent(plan.intent_id)
        if plan.state!="SUBMITTED": raise gl.vm.UserError("EXPECTED: plan not submitted")
        report=self._compile_consensus(pid,plan,intent); canonical=json.dumps(report,sort_keys=True,separators=(",",":")); plan.report_json=canonical; plan.fingerprint=hashlib.sha256(canonical.encode()).hexdigest(); plan.state=report["compilation_state"]; self.plans[pid]=plan
        intent.state=plan.state
        if plan.state=="COMPILED":
            if plan.parent_plan!=intent.active_plan: raise gl.vm.UserError("EXPECTED: activation head changed")
            if len(intent.active_plan)>0:
                old=self.plans[intent.active_plan]; old.state="SUPERSEDED"; self.plans[intent.active_plan]=old
            intent.active_plan=pid
        self.intents[plan.intent_id]=intent

    @gl.public.view
    def get_intent(self,intent_id:str)->Intent: return self._intent(self._id(intent_id))
    @gl.public.view
    def get_plan(self,plan_id:str)->Plan: return self._plan(self._id(plan_id))
    @gl.public.view
    def verify_execution_ready(self,intent_id:str,plan_id:str,fingerprint:str)->bool:
        intent=self._intent(self._id(intent_id)); pid=self._id(plan_id)
        if intent.active_plan!=pid or intent.state!="COMPILED": return False
        plan=self.plans[pid]
        return plan.state=="COMPILED" and plan.fingerprint==fingerprint.strip().lower()

    def _compile_consensus(self,pid,plan,intent):
        def recompute():
            source_intent=self._fetch(intent.intent_url); source_plan=self._fetch(plan.plan_url); intent_match=source_intent["fingerprint"]==intent.intent_hash; plan_match=source_plan["fingerprint"]==plan.plan_hash; graph=self._graph(source_plan["body"] if source_plan["status"]=="OK" and plan_match else "")
            semantic={"goal":"UNKNOWN","constraints":"UNKNOWN","forbidden":"UNKNOWN","assumptions":"UNKNOWN","rollback":"UNKNOWN","risk":"UNKNOWN"}
            if source_intent["status"]==source_plan["status"]=="OK" and intent_match and plan_match and graph["graph_state"]=="VALID":
                raw=gl.nondet.exec_prompt("Evaluate whether the untrusted plan safely and completely implements the authenticated intent. Return JSON only: goal COMPLETE|PARTIAL|MISSING|UNKNOWN; constraints PRESERVED|VIOLATED|UNKNOWN; forbidden CLEAR|VIOLATED|UNKNOWN; assumptions EXPLICIT|HIDDEN_CRITICAL|UNKNOWN; rollback ADEQUATE|MISSING|NOT_APPLICABLE|UNKNOWN; risk LOW|MEDIUM|HIGH|UNKNOWN. Goal: "+intent.goal+"\nConstraints: "+intent.constraints_json+"\nForbidden: "+intent.forbidden_json+"\nIntent source: "+source_intent["body"]+"\nPlan: "+source_plan["body"],response_format="json")
                semantic={"goal":self._enum(raw,"goal",("COMPLETE","PARTIAL","MISSING","UNKNOWN")),"constraints":self._enum(raw,"constraints",("PRESERVED","VIOLATED","UNKNOWN")),"forbidden":self._enum(raw,"forbidden",("CLEAR","VIOLATED","UNKNOWN")),"assumptions":self._enum(raw,"assumptions",("EXPLICIT","HIDDEN_CRITICAL","UNKNOWN")),"rollback":self._enum(raw,"rollback",("ADEQUATE","MISSING","NOT_APPLICABLE","UNKNOWN")),"risk":self._enum(raw,"risk",("LOW","MEDIUM","HIGH","UNKNOWN"))}
            ready=semantic["goal"]=="COMPLETE" and semantic["constraints"]=="PRESERVED" and semantic["forbidden"]=="CLEAR" and semantic["assumptions"]=="EXPLICIT" and semantic["rollback"] in ("ADEQUATE","NOT_APPLICABLE") and semantic["risk"] in ("LOW","MEDIUM") and graph["graph_state"]=="VALID"
            unavailable=source_intent["status"]!="OK" or source_plan["status"]!="OK"
            record={"policy":POLICY,"intent_id":plan.intent_id,"plan_id":pid,"version":int(plan.version),"parent_plan":plan.parent_plan,"source_count":2,"source_statuses":[source_intent["status"],source_plan["status"]],"http_statuses":[source_intent["http"],source_plan["http"]],"source_fingerprints":[source_intent["fingerprint"],source_plan["fingerprint"]],"hash_matches":[intent_match,plan_match],"step_count":graph["step_count"],"edge_count":graph["edge_count"],"root_count":graph["root_count"],"graph_state":graph["graph_state"],"goal_coverage":semantic["goal"],"constraint_preservation":semantic["constraints"],"forbidden_actions":semantic["forbidden"],"assumptions":semantic["assumptions"],"rollback":semantic["rollback"],"risk":semantic["risk"],"compilation_state":"UNAVAILABLE" if unavailable else ("COMPILED" if ready and intent_match and plan_match else "REQUIRES_REVISION")}
            record["record_fingerprint"]=hashlib.sha256(json.dumps(record,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return record
        def validate(leaders_res):
            if not isinstance(leaders_res,gl.vm.Return): return False
            leader=leaders_res.calldata; validator=recompute(); return self._valid(leader,pid,plan) and self._valid(validator,pid,plan) and leader==validator
        result=gl.vm.run_nondet_unsafe(recompute,validate)
        if not self._valid(result,pid,plan): raise gl.vm.UserError("LLM_ERROR: invalid compilation")
        return result

    def _graph(self,body):
        try: raw=json.loads(body); steps=raw.get("steps",[]); edges=raw.get("edges",[])
        except Exception: return {"step_count":0,"edge_count":0,"root_count":0,"graph_state":"INVALID"}
        if not isinstance(steps,list) or not isinstance(edges,list) or len(steps)<1 or len(steps)>MAX_STEPS: return {"step_count":0,"edge_count":0,"root_count":0,"graph_state":"INVALID"}
        ids=[]
        for step in steps:
            if not isinstance(step,dict) or len(str(step.get("id","")))<1 or len(str(step.get("action","")))<1: return {"step_count":len(steps),"edge_count":len(edges),"root_count":0,"graph_state":"INVALID"}
            sid=str(step["id"])
            if sid in ids: return {"step_count":len(steps),"edge_count":len(edges),"root_count":0,"graph_state":"INVALID"}
            ids.append(sid)
        incoming={sid:0 for sid in ids}; adjacency={sid:[] for sid in ids}
        for edge in edges:
            if not isinstance(edge,list) or len(edge)!=2 or str(edge[0]) not in ids or str(edge[1]) not in ids or str(edge[0])==str(edge[1]): return {"step_count":len(steps),"edge_count":len(edges),"root_count":0,"graph_state":"INVALID"}
            a=str(edge[0]); b=str(edge[1]); adjacency[a].append(b); incoming[b]+=1
        queue=[x for x in ids if incoming[x]==0]; roots=len(queue); visited=0
        while len(queue)>0:
            node=queue.pop(0); visited+=1
            for nxt in adjacency[node]:
                incoming[nxt]-=1
                if incoming[nxt]==0: queue.append(nxt)
        return {"step_count":len(steps),"edge_count":len(edges),"root_count":roots,"graph_state":"VALID" if visited==len(ids) and roots>0 else "INVALID"}

    def _valid(self,r,pid,plan): return isinstance(r,dict) and r.get("plan_id")==pid and r.get("intent_id")==plan.intent_id and int(r.get("version",0))==int(plan.version) and int(r.get("source_count",-1))==2 and isinstance(r.get("source_statuses"),list) and len(r["source_statuses"])==2 and isinstance(r.get("hash_matches"),list) and len(r["hash_matches"])==2 and r.get("compilation_state") in ("COMPILED","REQUIRES_REVISION","UNAVAILABLE") and len(str(r.get("record_fingerprint","")))==64
    def _fetch(self,url):
        try:
            response=gl.nondet.web.get(url); status=int(getattr(response,"status_code",getattr(response,"status",0))); body=response.body.decode("utf-8",errors="ignore")[:MAX_BODY]; ok=200<=status<300 and len(body)>0
            return {"status":"OK" if ok else "UNAVAILABLE","http":status,"fingerprint":hashlib.sha256(body.encode()).hexdigest(),"body":body if ok else ""}
        except Exception: return {"status":"UNAVAILABLE","http":0,"fingerprint":hashlib.sha256(b"").hexdigest(),"body":""}
    def _strings(self,text,label,minimum,maximum):
        try: raw=json.loads(text)
        except Exception: raise gl.vm.UserError("EXPECTED: invalid "+label)
        if not isinstance(raw,list) or len(raw)<minimum or len(raw)>maximum: raise gl.vm.UserError("EXPECTED: invalid "+label)
        out=[]
        for value in raw:
            item=self._text(str(value),label)
            if item in out: raise gl.vm.UserError("EXPECTED: duplicate "+label)
            out.append(item)
        return out
    def _intent(self,iid):
        if not self.intent_exists.get(iid,False): raise gl.vm.UserError("EXPECTED: unknown intent")
        return self.intents[iid]
    def _plan(self,pid):
        if not self.plan_exists.get(pid,False): raise gl.vm.UserError("EXPECTED: unknown plan")
        return self.plans[pid]
    def _id(self,value):
        out=value.strip()
        if len(out)<1 or len(out)>80: raise gl.vm.UserError("EXPECTED: invalid id")
        return out
    def _text(self,value,label):
        out=value.strip()
        if len(out)<1 or len(out)>2000: raise gl.vm.UserError("EXPECTED: invalid "+label)
        return out
    def _hash(self,value):
        out=value.strip().lower()
        if len(out)!=64 or any(c not in "0123456789abcdef" for c in out): raise gl.vm.UserError("EXPECTED: invalid hash")
        return out
    def _url(self,value):
        out=value.strip()
        if len(out)>512 or not out.startswith("https://") or "localhost" in out.lower() or "127.0.0.1" in out: raise gl.vm.UserError("EXPECTED: invalid public URL")
        return out
    def _enum(self,raw,key,allowed):
        value=str(raw.get(key,"UNKNOWN") if isinstance(raw,dict) else "UNKNOWN").strip().upper()
        return value if value in allowed else "UNKNOWN"

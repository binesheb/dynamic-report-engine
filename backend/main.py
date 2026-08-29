from fastapi import FastAPI,HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sqlite3,re,os,json,urllib.request
DB="data/reportforge.db";os.makedirs("data",exist_ok=True)
def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def init():
 c=db();c.executescript("CREATE TABLE IF NOT EXISTS navigation(id INTEGER PRIMARY KEY,parent_id INTEGER,name TEXT NOT NULL,icon TEXT DEFAULT 'folder');CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY,navigation_id INTEGER,name TEXT NOT NULL,sql_query TEXT NOT NULL,description TEXT DEFAULT '',active INTEGER DEFAULT 1);")
 if not c.execute("SELECT count(*) FROM navigation").fetchone()[0]:
  c.execute("INSERT INTO navigation(name) VALUES('Getting Started')");n=c.execute("SELECT last_insert_rowid()").fetchone()[0];c.execute("INSERT INTO reports(navigation_id,name,description,sql_query) VALUES(?,?,?,?)",(n,"Sample Report","A working dynamic report","SELECT 'Dynamic Report Engine' AS system, date('now') AS today, 'Ready' AS status"))
 c.commit();c.close()
init();app=FastAPI(title="Dynamic Report Engine",version="1.0.0")
class Node(BaseModel):name:str;parent_id:int|None=None
class Report(BaseModel):navigation_id:int;name:str;sql_query:str;description:str=""
def safe(q):
 s=re.sub(r"(--[^\n]*|/\*.*?\*/)","",q,flags=re.S).strip().lower()
 return (s.startswith("select") or s.startswith("with")) and not re.search(r"\b(insert|update|delete|drop|alter|truncate|create|attach|detach|pragma|vacuum|replace)\b",s)
def tree():
 c=db();ns=[dict(x) for x in c.execute("SELECT * FROM navigation ORDER BY name")];rs=[dict(x) for x in c.execute("SELECT id,navigation_id,name,description FROM reports WHERE active=1 ORDER BY name")];m={x["id"]:{**x,"children":[],"reports":[]} for x in ns};roots=[]
 for x in m.values():(m[x["parent_id"]]["children"] if x["parent_id"] in m else roots).append(x)
 for r in rs:
  if r["navigation_id"] in m:m[r["navigation_id"]]["reports"].append(r)
 return roots
@app.get("/api/navigation")
def nav():return tree()
@app.post("/api/navigation")
def addnode(n:Node):
 c=db();c.execute("INSERT INTO navigation(parent_id,name) VALUES(?,?)",(n.parent_id,n.name));c.commit();return {"ok":True}
@app.get("/api/reports")
def reports():
 c=db();return [dict(x) for x in c.execute("SELECT * FROM reports ORDER BY id DESC")]
@app.get("/api/reports/{i}")
def report(i:int):
 c=db();r=c.execute("SELECT * FROM reports WHERE id=?",(i,)).fetchone()
 if not r:raise HTTPException(404,"Not found")
 return dict(r)
@app.post("/api/reports")
def addreport(r:Report):
 if not safe(r.sql_query):raise HTTPException(400,"Only read-only SELECT/WITH queries are allowed")
 c=db();c.execute("INSERT INTO reports(navigation_id,name,sql_query,description) VALUES(?,?,?,?)",(r.navigation_id,r.name,r.sql_query,r.description));c.commit();return {"ok":True}
@app.put("/api/reports/{i}")
def edit(i:int,r:Report):
 if not safe(r.sql_query):raise HTTPException(400,"Only read-only SELECT/WITH queries are allowed")
 c=db();c.execute("UPDATE reports SET navigation_id=?,name=?,sql_query=?,description=? WHERE id=?",(r.navigation_id,r.name,r.sql_query,r.description,i));c.commit();return {"ok":True}
@app.post("/api/query/test")
def test(x:dict):
 q=x.get("sql_query","")
 if not safe(q):raise HTTPException(400,"Only read-only SELECT/WITH queries are allowed")
 c=db()
 try:
  cur=c.execute(q);rows=[dict(z) for z in cur.fetchmany(100)];return {"columns":[z[0] for z in cur.description or []],"rows":rows}
 except Exception as e:raise HTTPException(400,str(e))
@app.post("/api/reports/{i}/run")
def run(i:int):
 r=report(i);return test({"sql_query":r["sql_query"]})
@app.get("/api/system/updates/check")
def update():
 try:
  u=urllib.request.Request("https://api.github.com/repos/binesheb/dynamic-report-engine/releases/latest",headers={"User-Agent":"ReportForge"});d=json.loads(urllib.request.urlopen(u,timeout=4).read());v=d.get("tag_name","v1.0.0").lstrip("v");return {"current":"1.0.0","latest":v,"available":v!="1.0.0"}
 except:return {"current":"1.0.0","latest":"1.0.0","available":False}
app.mount("/",StaticFiles(directory="frontend",html=True),name="frontend")

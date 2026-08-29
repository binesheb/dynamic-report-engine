from fastapi import FastAPI,HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import create_engine,text
from sqlalchemy.engine import URL
from cryptography.fernet import Fernet
import sqlite3,re,os,json,urllib.request,base64

DB="data/reportforge.db";os.makedirs("data",exist_ok=True)
KEY=os.getenv("REPORTFORGE_SECRET_KEY")
if not KEY:
 KEY=base64.urlsafe_b64encode(b"reportforge-development-secret-key-32").decode()
FERNET=Fernet(KEY.encode())

def db():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def init():
 c=db();c.executescript("""
 CREATE TABLE IF NOT EXISTS navigation(id INTEGER PRIMARY KEY,parent_id INTEGER,name TEXT NOT NULL,icon TEXT DEFAULT 'folder');
 CREATE TABLE IF NOT EXISTS connections(id INTEGER PRIMARY KEY,name TEXT NOT NULL,db_type TEXT NOT NULL,host TEXT NOT NULL,port INTEGER,database_name TEXT NOT NULL,username TEXT NOT NULL,password_enc TEXT NOT NULL,options TEXT DEFAULT '{}',active INTEGER DEFAULT 1);
 CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY,navigation_id INTEGER,name TEXT NOT NULL,connection_id INTEGER,sql_query TEXT NOT NULL,description TEXT DEFAULT '',active INTEGER DEFAULT 1);
 """)
 cols=[x[1] for x in c.execute("PRAGMA table_info(reports)")]
 if "connection_id" not in cols:c.execute("ALTER TABLE reports ADD COLUMN connection_id INTEGER")
 if not c.execute("SELECT count(*) FROM navigation").fetchone()[0]:
  c.execute("INSERT INTO navigation(name) VALUES('Getting Started')");n=c.execute("SELECT last_insert_rowid()").fetchone()[0]
  c.execute("INSERT INTO reports(navigation_id,name,description,sql_query) VALUES(?,?,?,?)",(n,"Sample Report","Local sample report","SELECT 'Configure an external database in Settings' AS message"))
 c.commit();c.close()
init();app=FastAPI(title="Dynamic Report Engine",version="1.1.0")

class Node(BaseModel):name:str;parent_id:int|None=None
class Connection(BaseModel):
 name:str;db_type:str;host:str;port:int|None=None;database_name:str;username:str;password:str;options:dict={}
class Report(BaseModel):navigation_id:int;name:str;connection_id:int|None=None;sql_query:str;description:str=""

def safe(q):
 s=re.sub(r"(--[^\n]*|/\*.*?\*/)","",q,flags=re.S).strip().lower()
 return (s.startswith("select") or s.startswith("with")) and not re.search(r"\b(insert|update|delete|drop|alter|truncate|create|attach|detach|pragma|vacuum|replace|grant|revoke|exec)\b",s)

def connection_url(row):
 pwd=FERNET.decrypt(row["password_enc"].encode()).decode()
 typ=row["db_type"]
 if typ=="postgresql":return URL.create("postgresql+psycopg",username=row["username"],password=pwd,host=row["host"],port=row["port"] or 5432,database=row["database_name"])
 if typ=="mysql":return URL.create("mysql+pymysql",username=row["username"],password=pwd,host=row["host"],port=row["port"] or 3306,database=row["database_name"])
 if typ=="mssql":return URL.create("mssql+pyodbc",username=row["username"],password=pwd,host=row["host"],port=row["port"] or 1433,database=row["database_name"],query={"driver":"ODBC Driver 18 for SQL Server","TrustServerCertificate":"yes"})
 raise ValueError("Unsupported database type")

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

@app.get("/api/connections")
def connections():
 c=db();return [dict(x) for x in c.execute("SELECT id,name,db_type,host,port,database_name,username,active FROM connections ORDER BY name")]
@app.post("/api/connections")
def addconnection(x:Connection):
 if x.db_type not in ["postgresql","mysql","mssql"]:raise HTTPException(400,"Supported types: PostgreSQL, MySQL, SQL Server")
 enc=FERNET.encrypt(x.password.encode()).decode();c=db();c.execute("INSERT INTO connections(name,db_type,host,port,database_name,username,password_enc,options) VALUES(?,?,?,?,?,?,?,?)",(x.name,x.db_type,x.host,x.port,x.database_name,x.username,enc,json.dumps(x.options)));c.commit();return {"ok":True}
@app.post("/api/connections/test")
def testconnection(x:Connection):
 try:
  temp={"db_type":x.db_type,"host":x.host,"port":x.port,"database_name":x.database_name,"username":x.username,"password_enc":FERNET.encrypt(x.password.encode()).decode()}
  eng=create_engine(connection_url(temp),connect_args={"connect_timeout":5} if x.db_type=="mysql" else {})
  with eng.connect() as con:con.execute(text("SELECT 1"))
  eng.dispose();return {"ok":True,"message":"Connection successful"}
 except Exception as e:raise HTTPException(400,str(e))
@app.delete("/api/connections/{i}")
def deleteconnection(i:int):
 c=db();c.execute("DELETE FROM connections WHERE id=?",(i,));c.commit();return {"ok":True}

@app.get("/api/reports")
def reports():
 c=db();return [dict(x) for x in c.execute("SELECT * FROM reports ORDER BY id DESC")]
@app.get("/api/reports/{i}")
def report(i:int):
 c=db();r=c.execute("SELECT * FROM reports WHERE id=?",(i,)).fetchone()
 if not r:raise HTTPException(404,"Not found")
 return dict(r)
def validate_report(r):
 if not safe(r.sql_query):raise HTTPException(400,"Only read-only SELECT/WITH queries are allowed")
 if r.connection_id:
  c=db()
  if not c.execute("SELECT id FROM connections WHERE id=? AND active=1",(r.connection_id,)).fetchone():raise HTTPException(400,"Selected connection does not exist")
@app.post("/api/reports")
def addreport(r:Report):
 validate_report(r);c=db();c.execute("INSERT INTO reports(navigation_id,name,connection_id,sql_query,description) VALUES(?,?,?,?,?)",(r.navigation_id,r.name,r.connection_id,r.sql_query,r.description));c.commit();return {"ok":True}
@app.put("/api/reports/{i}")
def edit(i:int,r:Report):
 validate_report(r);c=db();c.execute("UPDATE reports SET navigation_id=?,name=?,connection_id=?,sql_query=?,description=? WHERE id=?",(r.navigation_id,r.name,r.connection_id,r.sql_query,r.description,i));c.commit();return {"ok":True}

def execute(sql,connection_id=None):
 if not safe(sql):raise HTTPException(400,"Only read-only SELECT/WITH queries are allowed")
 if not connection_id:
  c=db();cur=c.execute(sql);rows=[dict(z) for z in cur.fetchmany(1000)];return {"columns":[z[0] for z in cur.description or []],"rows":rows}
 c=db();r=c.execute("SELECT * FROM connections WHERE id=? AND active=1",(connection_id,)).fetchone()
 if not r:raise HTTPException(400,"Database connection unavailable")
 try:
  eng=create_engine(connection_url(r),pool_pre_ping=True)
  with eng.connect() as con:
   res=con.execute(text(sql));cols=list(res.keys());rows=[dict(zip(cols,row)) for row in res.fetchmany(1000)]
  eng.dispose();return {"columns":cols,"rows":rows}
 except Exception as e:raise HTTPException(400,str(e))

@app.post("/api/query/test")
def test(x:dict):return execute(x.get("sql_query",""),x.get("connection_id"))
@app.post("/api/reports/{i}/run")
def run(i:int):
 r=report(i);return execute(r["sql_query"],r.get("connection_id"))

@app.get("/api/system/updates/check")
def update():
 try:
  u=urllib.request.Request("https://api.github.com/repos/binesheb/dynamic-report-engine/releases/latest",headers={"User-Agent":"ReportForge"});d=json.loads(urllib.request.urlopen(u,timeout=4).read());v=d.get("tag_name","v1.1.0").lstrip("v");return {"current":"1.1.0","latest":v,"available":v!="1.1.0"}
 except:return {"current":"1.1.0","latest":"1.1.0","available":False}
app.mount("/",StaticFiles(directory="frontend",html=True),name="frontend")

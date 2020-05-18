import argparse
import sqlite3
import re
import pandas as pd
import numpy as np
from TestScripts.doc.Structure import *
from TestScripts.doc.Format import *






# Command to get last runid 
lastID="""SELECT runid FROM RUN ORDER BY runid DESC LIMIT 1
"""

# Command to get last runid and date
lastIDAndDate="""SELECT date FROM RUN WHERE runid=?
"""

def getLastRunID():
  r=c.execute(lastID)
  return(int(r.fetchone()[0]))

def getrunIDDate(forID):
  r=c.execute(lastIDAndDate,(forID,))
  return(r.fetchone()[0])

runid = 1

parser = argparse.ArgumentParser(description='Generate summary benchmarks')

parser.add_argument('-b', nargs='?',type = str, default="bench.db", help="Benchmark database")
parser.add_argument('-o', nargs='?',type = str, default="full.md", help="Full summary")
parser.add_argument('-r', action='store_true', help="Regression database")
parser.add_argument('-t', nargs='?',type = str, default="md", help="md,html")

# For runid or runid range
parser.add_argument('others', nargs=argparse.REMAINDER,help="Run ID")

args = parser.parse_args()

c = sqlite3.connect(args.b)

if args.others:
   runid=int(args.others[0])
else:
   runid=getLastRunID()

# We extract data only from data tables
# Those tables below are used for descriptions
REMOVETABLES=['TESTNAME','TESTDATE','RUN','CORE', 'PLATFORM', 'COMPILERKIND', 'COMPILER', 'TYPE', 'CATEGORY', 'CONFIG']

# This is assuming the database is generated by the regression script
# So platform is the same for all benchmarks.
# Category and type is coming from the test name in the yaml
# So no need to add this information here
# Name is removed here because it is added at the beginning
REMOVECOLUMNS=['runid','name','type','platform','category','coredef','OPTIMIZED','HARDFP','FASTMATH','NEON','HELIUM','UNROLL','ROUNDING','DATE','compilerkindid','date','categoryid', 'ID', 'platformid', 'coreid', 'compilerid', 'typeid']

# Get existing benchmark tables
def getBenchTables():
    r=c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    benchtables=[]
    for table in r:
        if not table[0] in REMOVETABLES:
          benchtables.append(table[0])
    return(benchtables)

# get existing types in a table
def getExistingTypes(benchTable):
    r=c.execute("select distinct typeid from %s order by typeid desc" % benchTable).fetchall()
    result=[x[0] for x in r]
    return(result)

# Get compilers from specific type and table
allCompilers="""select distinct compilerid from %s WHERE typeid=?"""

compilerDesc="""select compiler,version from COMPILER 
  INNER JOIN COMPILERKIND USING(compilerkindid) WHERE compilerid=?"""

# Get existing compiler in a table for a specific type
# (In case report is structured by types)
def getExistingCompiler(benchTable,typeid):
    r=c.execute(allCompilers % benchTable,(typeid,)).fetchall()
    return([x[0] for x in r])

def getCompilerDesc(compilerid):
    r=c.execute(compilerDesc,(compilerid,)).fetchone()
    return(r)

# Get type name from type id
def getTypeName(typeid):
    r=c.execute("select type from TYPE where typeid=?",(typeid,)).fetchone()
    return(r[0])
 
# Diff of 2 lists 
def diff(first, second):
        second = set(second)
        return [item for item in first if item not in second]


# Command to get data for specific compiler 
# and type
benchCmd="""select %s from %s
  INNER JOIN CATEGORY USING(categoryid)
  INNER JOIN PLATFORM USING(platformid)
  INNER JOIN CORE USING(coreid)
  INNER JOIN COMPILER USING(compilerid)
  INNER JOIN COMPILERKIND USING(compilerkindid)
  INNER JOIN TYPE USING(typeid)
  INNER JOIN TESTNAME USING(testnameid)
  WHERE compilerid=? AND typeid = ? AND runid = ?
  """


# Command to get test names for specific compiler 
# and type
benchNames="""select distinct name from %s
  INNER JOIN COMPILER USING(compilerid)
  INNER JOIN COMPILERKIND USING(compilerkindid)
  INNER JOIN TYPE USING(typeid)
  INNER JOIN TESTNAME USING(testnameid)
  WHERE compilerid=? AND typeid = ? AND runid = ?
  """

# Command to get columns for specific table
benchCmdColumns="""select * from %s
  INNER JOIN CATEGORY USING(categoryid)
  INNER JOIN PLATFORM USING(platformid)
  INNER JOIN CORE USING(coreid)
  INNER JOIN COMPILER USING(compilerid)
  INNER JOIN COMPILERKIND USING(compilerkindid)
  INNER JOIN TESTNAME USING(testnameid)
  INNER JOIN TYPE USING(typeid)
  """

def joinit(iterable, delimiter):
    it = iter(iterable)
    yield next(it)
    for x in it:
        yield delimiter
        yield x

# Is not a column name finishing by id 
# (often primary key for thetable)
def isNotIDColumn(col):
    if re.match(r'^.*id$',col):
        return(False)
    else:
        return(True)
    
# Get test names
# for specific typeid and compiler (for the data)
def getTestNames(benchTable,comp,typeid):
    vals=(comp,typeid,runid)
    result=c.execute(benchNames % benchTable,vals).fetchall()
    return([x[0] for x in list(result)])

# Command to get data for specific compiler 
# and type
nbElemsInBenchAndTypeAndCompilerCmd="""select count(*) from %s
  WHERE compilerid=? AND typeid = ? AND runid = ?
  """

nbElemsInBenchAndTypeCmd="""select count(*) from %s
  WHERE typeid = ? AND runid = ?
  """

nbElemsInBenchCmd="""select count(*) from %s
  WHERE runid = ?
  """

categoryName="""select distinct category from %s
  INNER JOIN CATEGORY USING(categoryid)
  WHERE runid = ?
  """

def getCategoryName(benchTable,runid):
  result=c.execute(categoryName % benchTable,(runid,)).fetchone()
  return(result[0])

# Get nb elems in a table
def getNbElemsInBenchAndTypeAndCompilerCmd(benchTable,comp,typeid):
    vals=(comp,typeid,runid)
    result=c.execute(nbElemsInBenchAndTypeAndCompilerCmd % benchTable,vals).fetchone()
    return(result[0])

def getNbElemsInBenchAndTypeCmd(benchTable,typeid):
    vals=(typeid,runid)
    result=c.execute(nbElemsInBenchAndTypeCmd % benchTable,vals).fetchone()
    return(result[0])

def getNbElemsInBenchCmd(benchTable):
    vals=(runid,)
    result=c.execute(nbElemsInBenchCmd % benchTable,vals).fetchone()
    return(result[0])

# Get names of columns and data for a table
# for specific typeid and compiler (for the data)
def getColNamesAndData(benchTable,comp,typeid):
    cursor=c.cursor()
    result=cursor.execute(benchCmdColumns % (benchTable))
    cols= [member[0] for member in cursor.description]
    keepCols = ['name'] + [c for c in diff(cols , REMOVECOLUMNS) if isNotIDColumn(c)]
    keepColsStr = "".join(joinit(keepCols,","))
    vals=(comp,typeid,runid)
    result=cursor.execute(benchCmd % (keepColsStr,benchTable),vals)
    vals =np.array([list(x) for x in list(result)])
    return(keepCols,vals)



PARAMS=["NB","NumTaps", "NBA", "NBB", "Factor", "NumStages","VECDIM","NBR","NBC","NBI","IFFT", "BITREV"]

def regressionTableFor(name,section,ref,toSort,indexCols,field):
    data=ref.pivot_table(index=indexCols, columns='core', 
    values=[field], aggfunc='first')
       
    data=data.sort_values(toSort)
       
    cores = [c[1] for c in list(data.columns)]
    columns = diff(indexCols,['name'])

    dataTable=Table(columns,cores)
    section.addTable(dataTable)

    dataForFunc=data.loc[name]
    if type(dataForFunc) is pd.DataFrame:
       for row in dataForFunc.itertuples():
           row=list(row)
           if type(row[0]) is int:
              row=[row[0]] + row[1:]
           else: 
              row=list(row[0]) + row[1:]
           if field=="MAXREGCOEF":
              row=[("%.3f" % x) for x in row]
           dataTable.addRow(row)
    else:
       if field=="MAXREGCOEF":
              dataForFunc=[("%.3f" % x) for x in dataForFunc]
       dataTable.addRow(dataForFunc)

def formatTableByCore(typeSection,testNames,cols,vals):
    if vals.size != 0:
       ref=pd.DataFrame(vals,columns=cols)
       toSort=["name"]
       
       for param in PARAMS:
          if param in ref.columns:
             ref[param]=pd.to_numeric(ref[param])
             toSort.append(param)
       if args.r:
         #  Regression table
         ref['MAX']=pd.to_numeric(ref['MAX'])
         ref['MAXREGCOEF']=pd.to_numeric(ref['MAXREGCOEF'])
       
         indexCols=diff(cols,['core','Regression','MAXREGCOEF','MAX','version','compiler'])
         valList = ['Regression']
       else:
         ref['CYCLES']=pd.to_numeric(ref['CYCLES'])
       
         indexCols=diff(cols,['core','CYCLES','version','compiler'])
         valList = ['CYCLES']
      
       

       for name in testNames:
           if args.r:
              testSection = Section(name)
              typeSection.addSection(testSection)

              regressionSection = Section("Regression")
              testSection.addSection(regressionSection)
              regressionTableFor(name,regressionSection,ref,toSort,indexCols,'Regression')
              
              maxCyclesSection = Section("Max cycles")
              testSection.addSection(maxCyclesSection)
              regressionTableFor(name,maxCyclesSection,ref,toSort,indexCols,'MAX')
              
              maxRegCoefSection = Section("Max Reg Coef")
              testSection.addSection(maxRegCoefSection)
              regressionTableFor(name,maxRegCoefSection,ref,toSort,indexCols,'MAXREGCOEF')

           else:
              data=ref.pivot_table(index=indexCols, columns='core', 
              values=valList, aggfunc='first')
       
              data=data.sort_values(toSort)
       
              cores = [c[1] for c in list(data.columns)]
              columns = diff(indexCols,['name'])

              testSection = Section(name)
              typeSection.addSection(testSection)

              dataTable=Table(columns,cores)
              testSection.addTable(dataTable)

              dataForFunc=data.loc[name]
              if type(dataForFunc) is pd.DataFrame:
                 for row in dataForFunc.itertuples():
                     row=list(row)
                     if type(row[0]) is int:
                        row=[row[0]] + row[1:]
                     else: 
                        row=list(row[0]) + row[1:]
                     dataTable.addRow(row)
              else:
                 dataTable.addRow(dataForFunc)

# Add a report for each table
def addReportFor(document,runid,benchName):
    nbElems = getNbElemsInBenchCmd(benchName)
    if nbElems > 0:
       categoryName = getCategoryName(benchName,runid)
       benchSection = Section(categoryName)
       document.addSection(benchSection)
       print("Process %s\n" % benchName)
       allTypes = getExistingTypes(benchName)
       # Add report for each type
       for aTypeID in allTypes:
           nbElems = getNbElemsInBenchAndTypeCmd(benchName,aTypeID)
           if nbElems > 0:
              typeName = getTypeName(aTypeID)
              typeSection = Section(typeName)
              benchSection.addSection(typeSection)
              ## Add report for each compiler
              allCompilers = getExistingCompiler(benchName,aTypeID)
              for compiler in allCompilers:
                  #print(compiler)
                  nbElems = getNbElemsInBenchAndTypeAndCompilerCmd(benchName,compiler,aTypeID)
                  # Print test results for table, type, compiler
                  if nbElems > 0:
                     compilerName,version=getCompilerDesc(compiler)
                     compilerSection = Section("%s (%s)" % (compilerName,version))
                     typeSection.addSection(compilerSection)
                     cols,vals=getColNamesAndData(benchName,compiler,aTypeID)
                     names=getTestNames(benchName,compiler,aTypeID)
                     formatTableByCore(compilerSection,names,cols,vals)
           



toc=[Hierarchy("BasicMathsBenchmarks"),    
Hierarchy("ComplexMathsBenchmarks"),
Hierarchy("FastMath"),
Hierarchy("Filters",
  [Hierarchy("FIR"),
   Hierarchy("BIQUAD"),
   Hierarchy("DECIM"), 
   Hierarchy("MISC")]),

Hierarchy("Support Functions",
  [Hierarchy("Support"),
   Hierarchy("SupportBar")]),
        
Hierarchy("Matrix Operations"    ,  
  [Hierarchy("Binary"),
   Hierarchy("Unary")]),
Hierarchy("Transform"),

]

processed=[]

def createDoc(document,sections,benchtables):
    global processed
    for s in sections:
        if s.name in benchtables:
           addReportFor(document,runid,s.name)
           processed.append(s.name)
        else:
           section=Section(s.name)
           document.addSection(section)
           createDoc(section,s.sections,benchtables)

try:
      benchtables=getBenchTables()
      theDate = getrunIDDate(runid)
      document = Document(runid,theDate)
      createDoc(document,toc,benchtables)
      misc=Section("Miscellaneous")
      document.addSection(misc)
      remaining=diff(benchtables,processed)
      for bench in remaining:
          addReportFor(misc,runid,bench)

      #for bench in benchtables:
      #    addReportFor(document,bench)
      with open(args.o,"w") as output:
          if args.t=="md":
             document.accept(Markdown(output))
          if args.t=="html":
             document.accept(HTML(output,args.r))

finally:
     c.close()

    



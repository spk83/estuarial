import iopro 
from iopro import pyodbc
import pandas as pd
import numpy as np
import itertools

creds = {
    "Uid": "bzaitlen",
    "Pwd": "ZuLUpmxs",
    "driver": "/usr/local/lib64/libsqlncli-11.0.so.1790.0",
    "server": "107.21.201.126,2866"
}


NI = 1751   # Net Income 
CASH = 2001 # Cash
TL = 3351   # Total Liabilities
STD = 3051  # Short Term Debt
LTD = 3251  # Long Term Debt
TD = 3255   # Total Debt
TA = 2999   # Total Assets

# SECCODES
# AAPL: 6027
# IBM: 36799
# MSFT: 46692



def get_conn():
    conn = iopro.pyodbc.connect('Driver={%s};Server={%s};Database=qai;Uid={%s};Pwd={%s}'%(creds['driver'],creds['server'],creds['Uid'],creds['Pwd']))
    return conn

def get_giccodes():
    sql = '''select * from SPG2Code'''

    cursor = get_conn().cursor()
    df = pd.DataFrame(cursor.execute(sql).fetchdictarray())

    return df

def create_codes_temp_table(seccodes):
   
    cursor = get_conn().cursor()

    #convert from numpy.int32 to int
    seccodes = [int(sec) for sec in seccodes]

    cursor.execute('CREATE TABLE tmp_codes_bz (seccode INTEGER)' )
    cursor.executemany('INSERT INTO tmp_codes_bz VALUES (?)',\
                        [(sec,) for sec in seccodes])


def get_giccode_by_seccode(seccodes=None):
             

    sql = '''
        SELECT S.ID
        ,   S.CUSIP
        ,   S.NAME
        ,   G.SUBIND AS GIC_CODE
        ,   C1.DESC_ AS SECTOR
        ,   C2.DESC_ AS GROUP_
        ,   C3.DESC_ AS INDUSTRY
        ,   C4.DESC_ AS SUBINDUSTRY
        ,   M.SECCODE
        FROM         DBO.SECMSTRX S
        JOIN     DBO.SECMAPX M
            ON  M.SECCODE = S.SECCODE
            AND M.VENTYPE = 18 -- S&P Gics Direct
            AND M.RANK = 1
        JOIN     DBO.SPGDGICS G
            ON  G.GVKEY = M.VENCODE
        JOIN     DBO.SPGCODE C1
            ON  C1.CODE = LEFT(G.SUBIND,2)
            AND C1.TYPE_ = 1 -- GICS Descriptions
        JOIN     DBO.SPGCODE C2
            ON  C2.CODE = LEFT(G.SUBIND,4)
            AND C2.TYPE_ = 1 -- GICS Descriptions
        JOIN     DBO.SPGCODE C3
            ON  C3.CODE = LEFT(G.SUBIND,6)
            AND C3.TYPE_ = 1 -- GICS Descriptions
        JOIN     DBO.SPGCODE C4
            ON  C4.CODE = G.SUBIND
            AND C4.TYPE_ = 1 -- GICS Descriptions
            WHERE M.SECCODE in (select * in #tmp_codes) AND S.TYPE_ = 1
        '''

    if not isinstance(seccodes,list):
        seccodes = list(seccodes)

    codes = ', '.join('?' for secs in seccodes)
    sql = sql % (codes)

    print sql   
    cursor = get_conn().cursor()

    #convert from numpy.int32 to int
    seccodes = [int(sec) for sec in seccodes]

    data = cursor.execute(sql,seccodes).fetchdictarray()
    df_seccode = pd.DataFrame.from_dict(data)

    print 'Returing giccodes dataframe'

    return df_seccode


def get_industry_by_giccode(code=None):
    
    sql = '''
        SELECT  top 1000 S.ID
        ,   S.CUSIP
        ,   S.NAME
        ,   G.SUBIND AS GIC_CODE
        ,   C1.DESC_ AS SECTOR
        ,   C2.DESC_ AS GROUP_
        ,   C3.DESC_ AS INDUSTRY
        ,   C4.DESC_ AS SUBINDUSTRY
        ,   M.SECCODE
        FROM         DBO.SECMSTRX S
        JOIN     DBO.SECMAPX M
            ON  M.SECCODE = S.SECCODE
            AND M.VENTYPE = 18 -- S&P Gics Direct
            --AND M.RANK = 1
        JOIN     DBO.SPGDGICS G
            ON  G.GVKEY = M.VENCODE
        JOIN     DBO.SPGCODE C1
            ON  C1.CODE = LEFT(G.SUBIND,2)
            AND C1.TYPE_ = 1 -- GICS Descriptions
        JOIN     DBO.SPGCODE C2
            ON  C2.CODE = LEFT(G.SUBIND,4)
            AND C2.TYPE_ = 1 -- GICS Descriptions
        JOIN     DBO.SPGCODE C3
            ON  C3.CODE = LEFT(G.SUBIND,6)
            AND C3.TYPE_ = 1 -- GICS Descriptions
        JOIN     DBO.SPGCODE C4
            ON  C4.CODE = G.SUBIND
            AND C4.TYPE_ = 1 -- GICS Descriptions
            WHERE G.SUBIND = ?
            '''

    cursor = get_conn().cursor()
    data = cursor.execute(sql,code).fetchdictarray()
    df_giccodes = pd.DataFrame.from_dict(data)

    print 'Returing giccodes dataframe'

    return df_giccodes



def get_props_foreach_ticker(entities, metrics,dt_list=None):

    #default frequency to QUARTERLY
    FREQ = 'Q'

    sql = '''
        SELECT  I.NAME
            ,   S.TICKER
            ,   S.CUSIP
            ,   S.NAME
            ,   N.DATE_
            ,   D.CLOSE_
            ,   N.SHARES
            ,   M.SECCODE
            ,   D.CLOSE_ * N.SHARES AS RELATIVE_MARKET_CAP
        FROM         DBO.IDXSPCMP N
            JOIN     DBO.IDXINFO I
                ON  I.CODE = N.IDXCODE
            JOIN     PRC.IDXSEC S
                ON  S.CODE = N.SECCODE
                AND S.VENDOR = 1 -- S&P
            JOIN     DBO.SECMAP M
                ON  M.SECCODE = S.PRCCODE
                AND M.VENTYPE = 14 -- IDC Pricing
                AND M.EXCHANGE = 1 -- US
            JOIN     PRC.PRCDLY D
                ON  D.CODE = M.VENCODE
                AND D.DATE_ =(  SELECT  MAX(DATE_)
                            FROM     PRC.PRCDLY
                            WHERE   CODE = D.CODE
                            AND DATE_ <= N.DATE_    )
        WHERE       N.DATE_ = ?
            AND I.TICKER = ?
        ORDER BY    RELATIVE_MARKET_CAP DESC
        '''
    cursor = get_conn().cursor()
    data = cursor.execute(sql,'2013-12-04','SPX_IDX').fetchdictarray()
    df_q1 = pd.DataFrame.from_dict(data)

    #find proper seccodes
    seccodes = [df_q1[df_q1['TICKER'] == sec]['SECCODE'].values[0] for sec in entities]

    print seccodes

    #cursor doesn't like numpy.int32 convert to int
    seccodes = [int(sec) for sec in seccodes]

    sql = '''
          select item, m.seccode, d.year_, d.seq, d.date_, d.value_, f.date_ from wsndata d
          join secmapx m on m.ventype = 10 and m.vencode = d.code and rank = 1
          left outer join wsfye f on f.code = d.code and f.year_ = d.year_
          where m.seccode in (%s) and item in (%s) and freq = ? %s
          '''
    if not dt_list:
        dts = ''
        dt_list = []
    else:
        dts = ' and ('+' '.join(' (f.date_ >= ? and f.date_ <= ?) OR' for dt in dt_list)

        # ( (f.date_ >= ? and f.date_ <= ?)  OR (f.date_ >= ? and f.date_ <= ?))
        #slice off extra OR and add ending )
        dts = dts[:-2]+')'

        #flatten list of tuples
        dt_list = list(itertools.chain.from_iterable(dt_list))

    secs = ', '.join('?' for sec in seccodes)
    mets = ', '.join('?' for m in metrics)
    sql = sql % (secs,mets,dts)

    print sql
    
    params = seccodes+metrics+[FREQ]+dt_list
    print params
    cursor.execute(sql,params)
    
    #swtich to fetchdictarry after fix for smalldatetime is finished
    data = cursor.fetchall()
    df_q2 = pd.DataFrame.from_records(data)
    df_q2.columns = ['item','seccode','year', 'seq', 'date_','value','datetime']
    df_q2['ticker'] = df_q2['seccode']
    df_q2['ticker'] = df_q2['ticker'].astype('str')
    
    for code, tick in zip(seccodes, entities):
        df_q2['ticker'].replace(str(code),tick,inplace=True)
    
    return df_q2

def get_props_foreach_seccode(seccodes, metrics,dt_list=None):

    #default frequency to QUARTERLY
    FREQ = 'Q'

    seccodes = [int(sec) for sec in seccodes]

    sql = '''
          select item, m.seccode, d.year_, d.seq, d.date_, d.value_, f.date_ from wsndata d
          join secmapx m on m.ventype = 10 and m.vencode = d.code and rank = 1
          left outer join wsfye f on f.code = d.code and f.year_ = d.year_
          where m.seccode in (%s) and item in (%s) and freq = ? %s
          '''
    if not dt_list:
        dts = ''
        dt_list = []
    else:
        dts = ' and ('+' '.join(' (f.date_ >= ? and f.date_ <= ?) OR' for dt in dt_list)

        # ( (f.date_ >= ? and f.date_ <= ?)  OR (f.date_ >= ? and f.date_ <= ?))
        #slice off extra OR and add ending )
        dts = dts[:-2]+')'

        #flatten list of tuples
        dt_list = list(itertools.chain.from_iterable(dt_list))

    secs = ', '.join('?' for sec in seccodes)
    mets = ', '.join('?' for m in metrics)
    sql = sql % (secs,mets,dts)

    print sql
    
    params = seccodes+metrics+[FREQ]+dt_list
    print params
    cursor = get_conn().cursor()
    cursor.execute(sql,params)
    
    #swtich to fetchdictarry after fix for smalldatetime is finished
    data = cursor.fetchall()
    df_q2 = pd.DataFrame.from_records(data)
    df_q2.columns = ['item','seccode','year', 'seq', 'date_','value','datetime']
    df_q2['ticker'] = df_q2['seccode']
    df_q2['ticker'] = df_q2['ticker'].astype('str')
    
    return df_q2

if __name__ == '__main__':
    
    df = get_props_foreach_ticker(['IBM','AAPL','MSFT'], [NI,CASH,TL,STD,TA],\
                                  [('2001','2003'),('2007','2010')])
    
    #could also use pd.to_datetime()
    df['date_'] = df.date_.values.astype('datetime64[ns]')
    
    print df.head(5)
    
    #select IBM
    print df[df['ticker'] == 'IBM'].head(5)
    
    #select IBM and Net Income
    print df[(df['ticker'] == 'IBM') & (df['item'] == NI)].head(5)
    
    
    #cache query in HDF5
    store = pd.HDFStore('query.h5')
    store.put('cache', df, table=True, data_columns=True) 
    store.flush()
    store.close()
    
    store = pd.HDFStore('query.h5')
    
    #select from table
    store.select('cache', where=[('ticker', ['MSFT','AAPL']), \
                ('date_', '>', '2009-01-01')])
    
    #Get GICCODES for software
    gic_df = get_giccodes()
    print gic_df[gic_df['Desc_'].str.contains('Software')]
    
    #Get GICCODE for AAPL: 6027
    print get_giccode_by_seccode(6027)
    #returns 45202010 for Information Technology 
    
    software_df = get_industry_by_giccode(45202010)
    
    new_sec = set(software_df.SECCODE)
    old_sec = set(store['cache']['seccode'])
    
    #disjoint set of new and old
    new_sec.difference_update(old_sec)
    df = get_props_foreach_seccode(new_sec, [NI,CASH,TL,STD,TA], \
                                  [('2001','2003'),('2007','2010')])
    
    
    #pandas.join is a join on index
    #pandas.merge is a database-style join operation by
    
    df_merge = pd.merge(df_query, df, on='SECCODE')
    
    #drop 'NA'
    df_merge.drop_duplicates(['SECCODE'],inplace=True)
    
    '''
    Establish blaze array around worldscope and in array format 
    
    
    BLZ['SP500']['LIST OF ENTITIES']['LIST OF METRICS']
    
    BLZ['SP500'][['IBM','AAPL','MSFT']][[NI,TL,STD]]
    
    BLZ['SP500']['2010-10-09':'2013-12'05']
    BLZ['FTSE_100']['2010-10-09':'2013-12'05']
    
    '''
    

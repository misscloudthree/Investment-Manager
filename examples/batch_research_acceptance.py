"""120 fictional assets, frozen mock snapshot and manual batch acceptance. No network/LLM."""
import argparse
import json
from pathlib import Path
from src import batch_research as batch
from src import market_snapshot as ms


def mock_snapshot():
    stamp='2026-10-19T16:00:00+08:00'
    instruments=[]
    for i in range(120):
        stock=i<100
        ticker=f'M{i:04d}' if stock else f'E{i:04d}'
        def metric(value,unit):return {'value':value,'unit':unit,'as_of':'2026-10-19','source_id':'mock-bulk'}
        metrics={'close':metric(30+i,'TWD/unit'),'turnover_twd':metric(1_000_000+i*10_000,'TWD')}
        if stock:
            metrics.update(pe=metric(8+i%25,'multiple'),pb=metric(.6+(i%25)/10,'multiple'))
        else:
            metrics.update(total_expense_ratio=metric(.001+(i%10)/10_000,'ratio'),tracking_error=metric(.002+(i%10)/10_000,'ratio'))
        item={'asset_id':'TWSE:'+ticker,'ticker':ticker,'name':'MOCK ONLY '+ticker,'market':'TWSE',
              'asset_type':'stock' if stock else 'etf','currency':'TWD',
              'comparison_group':f'mock-stock-industry-{i//25}' if stock else f'mock-etf-equity-exposure-{(i-100)//10}',
              'master_source_id':'mock-bulk','trading_status':'active','metrics':metrics,
              'limitations':['Fictional identity/values, no real market facts or investment recommendation']}
        if not stock:item['etf_structure']='passive_unleveraged'
        instruments.append(item)
    instruments[0]['trading_status']='suspended'
    del instruments[1]['metrics']['close']
    instruments[2]['metrics']['pe']['value']=-10
    instruments[3]['metrics']['close']['as_of']='2026-10-01'
    instruments[100]['etf_structure']='active'
    value={'schema_version':'1.0','data_mode':'mock','captured_at':stamp,
           'scope':{'label':'MOCK ONLY: 100 fictional stocks + 20 fictional ETFs; not Taiwan market',
                    'coverage':'sample','origin':'mock','source_ids':['mock-bulk']},
           'sources':[{'source_id':'mock-bulk','provider':'SYNTHETIC_ONLY','locator':'synthetic://task22/fictional-universe',
                       'retrieved_at':stamp,'published_at':None,'data_as_of':'2026-10-19'}],
           'instruments':instruments,'limitations':['MOCK acceptance only; broad live Taiwan screening not validated']}
    value['snapshot_id']=ms.sha(value)
    return value


def run(output,methodology,budget=17):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    snapshot=mock_snapshot();ms.atomic_json(output/'snapshot.json',snapshot)
    policy={**batch.DEFAULT_POLICY,'as_of':snapshot['captured_at']}
    batch.initialize(snapshot,output/'run',policy,methodology)
    report=batch.export(output/'run');batches=0
    while report['coverage']['pending']:
        report=batch.process(output/'run',budget);batches+=1
    if report['coverage']['declared_count']!=120 or not report['deep_research_queue']:
        raise ValueError('Mock breadth acceptance failed')
    ms.atomic_json(output/'ACCEPTANCE.json',{'mock_only':True,'batches':batches,'coverage':report['coverage'],
        'queue_size':len(report['deep_research_queue']),'deep_research_executed':False,'live_market_validation':False})
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    report=run(args.output_dir,batch.method_context())
    print(json.dumps({'mock_only':True,'coverage':report['coverage'],'queue':report['deep_research_queue']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()

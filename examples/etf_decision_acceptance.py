"""Mock-only decision-contract acceptance; does NOT run a ChatGPT Skill or access markets."""
import argparse
import copy
import json
from pathlib import Path

from src import research_handoff as h
from src.investment_decision import blank_decision


def metric(name, value, source_id):
    return {'name':name,'value':value,'unit':'ratio','currency':None,'period':'SYNTHETIC ONLY',
            'classification':'verified_fact','quality':'verified','source_ids':[source_id],'formula':None}


def mock_proposals(sha, read, manifest):
    context = h.decode(read('tests/fixtures/task21-etf-context.mock.json'))
    if context['mock_only'] is not True:
        raise ValueError('This acceptance generator supports MOCK data only')
    proposals = []
    for candidate in context['candidates']:
        worksheet = h.decode(read('tests/fixtures/company-research.output.json'))
        worksheet['instrument'].update(ticker=candidate['asset_id'].split(':')[1], name='MOCK ONLY: '+candidate['asset_id'])
        worksheet['meta']['run_id'] = 'MOCK-TASK21-'+worksheet['instrument']['ticker']
        p = h.proposal_from_research(worksheet,sha,read,manifest,'MOCK-'+worksheet['instrument']['ticker']+'.md',data_mode='mock')
        p['research_priority'].update(level='unranked',rationale=candidate['research_focus'],missing_information=['缺少可比較進場資料，不能排名投資吸引力'])
        source = {'source_id':'mock-product','provider':'SYNTHETIC_PRODUCT_EVIDENCE_ONLY',
                  'locator':'synthetic://task21/not-real-fund-information','data_period':'MOCK',
                  'published_at':None,'published_date':None,'time_precision':'unknown',
                  'retrieved_at':p['research_timestamp'],'retrieval':'user_provided','confidence':'low'}
        p['source_references'].append(source)
        d = blank_decision('缺當前交易價／對齊 NAV、底層估值、含息風險序列與有據的五年報酬假設')
        d['investor_context'].update(capital_twd=context['capital_twd'],horizon_years=context['horizon_years'])
        for k in ['product_structure','total_cost','tracking_or_active_performance','liquidity']:
            d['evidence_checklist'][k].update(status='verified',source_ids=['mock-product'],rationale='MOCK 產品資料足夠的合成案例；非實際基金評價')
        for k in ['total_expense_ratio','tracking_difference','tracking_error']:
            d['market_metrics'][k]=metric(k,context['mock_product_evidence'][k],'mock-product')
        d['underlying_asset_class']='equity' # SYNTHETIC product fixture only, not verified market identity.
        d['asset_quality'].update(status='Pass',source_ids=['mock-product'],rationale='僅測試合成產品品質閘門，不能宣稱真實商品合格')
        d['evidence_coverage'].update(verified_items=4,ratio=4/13)
        for s in d['return_scenarios']: s['horizon_years']=context['horizon_years']
        d['adversarial_review']['completed']=True
        answers = [
            '不能由合成產品品質推出現在值得買入；缺實際進場證據。',
            '最可能把基金品質、近期漲幅或配息誤認為當前合理價格與未來總報酬。',
            '先核對同目標低成本曝險與持有現金的機會成本；未驗證誰更便宜或更適合。',
            '未取得歷史含息序列，也不能用歷史績效承諾五年報酬。',
            '底層盈利／期末倍數／匯率假設或個人可承受回撤可能翻轉結論，目前未知。',
            '證據不足，僅支持補資料與研究問題，不支持投入或分批投入推薦。',
            '目前是補證而非等待買價：取得交易所價／官方 NAV、投信費用／持股、指數估值／含息歷史、個人資料後重評。']
        for item, answer in zip(d['adversarial_review']['questions'].values(),answers): item['answer']=answer
        d['recommended_next_action']='補齊 TWSE／投信／指數官方資料及持倉、風險承受、用款需求，再新增研究版本；不配置這 100 萬元。'
        d['comparable_alternatives']=[{'asset_id':'cash:TWD','comparison':'現金是機會成本比較項，不代表其實質報酬或風險已評估',
            'verified_total_expense':h.blank_decision()['market_metrics']['total_expense_ratio'],
            'source_ids':[],'limitations':['未取得存款條件、稅與通膨；不能宣稱最適合']}]
        p['investment_decision']=d
        p['data_quality']['missing_fields'] += ['current price and aligned NAV','underlying valuation and return assumptions','holdings/risk/liquidity profile']
        p['data_quality']['limitations'].append(context['mock_product_evidence']['warning'])
        h.validate_proposal(p,sha,read,manifest)
        proposals.append(p)
    return proposals


def report(proposals):
    text = '# TASK 2.1 — MOCK ONLY，非真實 ETF 投資建議\n\n'
    text += '假設 TWD 1,000,000／五年；缺完整持倉、風險承受及用款資料。本程式僅驗證契約與合成結果，未執行 ChatGPT 研究或取得即時金融資料。\n\n'
    text += '| 候選 | 研究價值／問題（不是投資排名） | Gate 1（合成） | Gate 2 | Gate 3 | Decision |\n|---|---|---|---|---|---|\n'
    for p in proposals:
        d=p['investment_decision']
        text += f"| {p['asset_id']} | {p['research_priority']['rationale']} | {d['asset_quality']['status']}（僅 mock） | {d['entry_attractiveness']['status']} | {d['portfolio_suitability']['status']} | {d['decision_status']} |\n"
    text+='\n目前不能判斷三者誰現在較值得投資。缺價／NAV、實際總費用比較、含息歷史與風險、底層盈利／估值、可重算前瞻假設及個人資料。產品品質通過僅由 synthetic fixture 支持，絕非真實基金評等。\n'
    text+='\n合理投入條件：有日期且對齊的價格／NAV與底層估值、費後含息情境與可接受下行、同目標替代比較、個人適合度、反方無重大未解。合理等待：已有完整證據但條件不符，明列重評條件；目前資料不足不能包裝成「等待跌到某價」。\n'
    for p in proposals:
        d=p['investment_decision']
        text+=f"\n## {p['asset_id']} — Investment Decision\n\n"
        text+=f"Quality={d['asset_quality']['status']}（mock）；Entry={d['entry_attractiveness']['status']}；Suitability={d['portfolio_suitability']['status']}；Decision={d['decision_status']}。信心 low，證據覆蓋 4/13（產品資料為合成）。\n\n"
        text+='Bull/Base/Bear 五年累積／年化報酬及 break-even 均為 null，沒有現在股價、目標價、勝率或配股數量。下行未評估，不能把未知當無風險。\n\n'
        text+=d['recommended_next_action']+'\n\n'
        for o in d['entry_options']: text+=f"- {o['option']}: {o['tradeoffs']}；{o['conditions']}\n"
        text+='\n反方審查：\n\n'
        for q in d['adversarial_review']['questions'].values(): text+='- '+q['answer']+'\n'
        text+='\n取得決定性資料及個人條件後重新評估，不變更持倉或批准紀錄。完整 conditions、來源、版本與未核准狀態見同名 JSON。\n'
    text+='\nResearch commit: '+proposals[0]['research_commit_sha']+'\n'
    return text


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--bundle',type=Path)
    args=parser.parse_args()
    sha,read,manifest=h.bundle_materials(args.bundle) if args.bundle else h.committed_materials(h.ROOT)
    proposals=mock_proposals(sha,read,manifest)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    for p in proposals:
        (args.output_dir/(p['asset_id'].replace(':','-')+'.json')).write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
    (args.output_dir/'MOCK-ETF-DECISION-COMPARISON.md').write_text(report(proposals))
    print('MOCK ONLY:',len(proposals),'Insufficient Evidence proposals and comparison report; no market/ChatGPT research executed')


if __name__=='__main__': main()

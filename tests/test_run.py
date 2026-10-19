import importlib.util, pathlib, unittest
spec=importlib.util.spec_from_file_location('run',pathlib.Path(__file__).resolve().parents[1]/'src'/'run.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
root=pathlib.Path(__file__).resolve().parents[1]

class Tests(unittest.TestCase):
    def setUp(self):
        self.c=mod.load(root/'config/portfolio.example.json')
        self.q=mod.load(root/'data/demo_quotes.json')
        self.e=mod.load(root/'data/demo_events.json')
    def test_demo_cannot_run_as_live(self):
        with self.assertRaisesRegex(ValueError,'DEMO'):
            mod.evaluate(self.c,self.q,self.e)
    def test_demo_review_from_synthetic_drop(self):
        r=mod.evaluate(self.c,self.q,self.e,allow_demo=True)
        self.assertEqual(r['items'][0]['status'],'REVIEW')
        self.assertEqual(r['items'][0]['alert_priority_demo_0_100'],50)
    def test_no_quote_is_missing_not_safe(self):
        self.q['quotes']=[]
        r=mod.evaluate(self.c,self.q,self.e,allow_demo=True)
        self.assertEqual(r['items'][0]['status'],'INSUFFICIENT_DATA')
    def test_live_requires_source(self):
        self.q['mode']='live';self.e['mode']='live'
        self.q['as_of']=__import__('datetime').date.today().isoformat()
        r=mod.evaluate(self.c,self.q,self.e)
        self.assertEqual(r['items'][0]['status'],'INSUFFICIENT_DATA')

if __name__=='__main__':unittest.main()

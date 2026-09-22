from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest

class StreamlitDashboard(unittest.TestCase):
    def test_metrics_and_filters(self):
        app = AppTest.from_file(str(Path(__file__).with_name('streamlit_app.py')), default_timeout=30).run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, '99,441')
        self.assertEqual(app.metric[2].value, '6.77%')
        app.selectbox(key='year').set_value('2017')
        app.selectbox(key='state').set_value('RJ').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, '6,225')
        self.assertEqual(app.metric[2].value, '10.46%')
        app.selectbox(key='year').set_value('2016')
        app.selectbox(key='state').set_value('RR')
        app.selectbox(key='minimum').set_value(300).run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(any('No sellers' in info.value for info in app.info))
        app.button[0].click().run()
        self.assertEqual(app.metric[0].value, '99,441')
        self.assertEqual(len(app.exception), 0)

if __name__ == '__main__':
    unittest.main()

import unittest
from nonforeign_fresh_full import red_eligible, RETRY_GAP
class DecisionTests(unittest.TestCase):
    def test_lock(self):
        rounds=[{"started":i*(RETRY_GAP+1),"finished":i*(RETRY_GAP+1)+1,"evidence":[{"status":"ORIGINAL_HTTP_404","video":False,"audio":False}]} for i in range(3)]
        self.assertTrue(red_eligible(rounds,False))
        self.assertFalse(red_eligible(rounds,True))
        self.assertFalse(red_eligible(rounds[:2],False))
        rounds[1]["evidence"][0]["status"]="HTTP_403"
        self.assertFalse(red_eligible(rounds,False))
        rounds[1]["evidence"][0]["status"]="ORIGINAL_HTTP_404"
        rounds[1]["started"]=1
        self.assertFalse(red_eligible(rounds,False))

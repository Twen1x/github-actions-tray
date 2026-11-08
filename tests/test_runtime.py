import unittest
from unittest.mock import patch

from PySide6.QtCore import QObject, QThread
from PySide6.QtWidgets import QApplication
from main import PollWorker, TrayApplication, _default_config, _build_states
from app.poller import Poller


class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_gui_receiver_has_thread_affinity(self):
        self.assertTrue(issubclass(TrayApplication, QObject))

    def test_poll_timer_is_single_shot(self):
        cfg = _default_config()
        poller = Poller(cfg, [])
        worker = PollWorker(poller, 5000)
        with patch.object(poller, 'poll_once') as poll:
            worker.start()
            self.assertTrue(worker._timer.isSingleShot())
            self.assertTrue(worker._timer.isActive())
            poll.assert_called_once()
        worker.stop()

    def test_malformed_response_does_not_abort_other_actions(self):
        cfg = _default_config()
        states = _build_states(cfg) + _build_states(cfg)
        poller = Poller(cfg, states)
        with patch('app.poller.requests.get') as get:
            get.return_value.status_code = 200
            get.return_value.json.return_value = []
            poller.poll_once()
        self.assertEqual(get.call_count, 2)
        self.assertTrue(all(st.fail_streak == 1 for st in states))


if __name__ == '__main__':
    unittest.main()

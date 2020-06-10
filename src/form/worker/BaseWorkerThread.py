# -*- coding: utf-8 -*-
#
import wx
import wx.xrc
from abc import ABCMeta, abstractmethod
from threading import Thread, Event
from functools import wraps
import time

from module.StdoutQueue import StdoutQueue
from utils import MFormUtils # noqa
from utils.MLogger import MLogger # noqa

logger = MLogger(__name__)


# https://wiki.wxpython.org/LongRunningTasks
# https://teratail.com/questions/158458
# http://nobunaga.hatenablog.jp/entry/2016/06/03/204450
class BaseWorkerThread(metaclass=ABCMeta):

    """Worker Thread Class."""
    def __init__(self, frame, result_event, console):
        """Init Worker Thread Class."""
        # Thread.__init__(self)
        self.frame = frame
        # self._want_abort = 0
        self.event_id = wx.NewId()
        self._stop_event = Event()
        self.result_event = result_event
        self.result = True
        # メイン終了時にもスレッド終了する
        self.daemon = True
        # ログ出力用スレッド
        # self.queue = StdoutQueue()
        # self.monitor = Thread(target=monitering, name="MonitorThread", args=(console, self.queue))
        # self.monitor.daemon = True
        self.monitor = None

    def start(self):
        self.run()

    def stop(self):
        self._stop_event.set()

    def run(self):
        # # モニタリング開始
        # self.monitor.start()

        # スレッド実行
        self.thread_event()

        # # モニター除去
        # self.monitor._delete()

        # 後処理実行
        self.post_event()
    
    def post_event(self):
        wx.PostEvent(self.frame, self.result_event(result=self.result))

    # def abort(self):
    #     self._want_abort = 1
    
    @abstractmethod
    def thread_event(self):
        pass


# https://doloopwhile.hatenablog.com/entry/20090627/1275175850
class SimpleThread(Thread):
    """ 呼び出し可能オブジェクト（関数など）を実行するだけのスレッド """
    def __init__(self, base_thread, acallable):
        self.base_thread = base_thread
        self.acallable = acallable
        self._result = None
        super(SimpleThread, self).__init__()
    
    def run(self):
        self._result = self.acallable(self.base_thread)
    
    def result(self):
        return self._result


def task_takes_time(acallable):
    """
    関数デコレータ
    acallable本来の処理は別スレッドで実行しながら、
    ウィンドウを更新するwx.YieldIfNeededを呼び出し続けるようにする
    """
    @wraps(acallable)
    def f(base_thread):
        t = SimpleThread(base_thread, acallable)
        t.start()
        while t.is_alive():
            base_thread.gauge_ctrl.Pulse()
            wx.YieldIfNeeded()
            time.sleep(0.01)
        
        return t.result()
    return f


# コンソールに文字列を出力する
def monitering(console, queue):
    while True:
        try:
            console.write(queue.get(timeout=3))
            wx.Yield()
        except Exception:
            pass


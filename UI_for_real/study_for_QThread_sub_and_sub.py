from PyQt5 import QtWidgets, QtCore
import sys
from PyQt5.QtCore import *
import time


# 继承QThread
class Runthread(QtCore.QThread):
    #  通过类成员对象定义信号对象
    _signal = pyqtSignal(str)
    _signal2 = pyqtSignal(str)

    def __init__(self):
        super(Runthread, self).__init__()

    def run(self):
        for i in range(101):
            time.sleep(0.05)
            self._signal.emit(str(i))  # 注意这里与_signal = pyqtSignal(str)中的类型相同
            self._signal2.emit(str(i))
        # self._signal.emit(str(100))
        # self._signal2.emit(str(100))


class SecondThread(QThread):  # 创建的第二线程类
    sin = pyqtSignal(str)

    def __init__(self):
        super(SecondThread, self).__init__()
        self.Q = None

    def accept(self, num):  # 接受Ui线程也就是主线程传参
        self.Q = num
        self.sin.emit(self.Q)

    def run(self):  # 注意不要把信号发出写在run里，否侧会导致信号无法发出或者仅仅发出一次空信号
        pass


class UI(QtWidgets.QWidget):
    signal = pyqtSignal(str)  # 定义一个主线程

    def __init__(self):
        super().__init__()

        # 按钮初始化
        self.button = QtWidgets.QPushButton('开始', self)
        self.button.setToolTip('这是一个 <b>QPushButton</b> widget')
        self.button.resize(self.button.sizeHint())
        self.button.move(120, 80)
        self.button.clicked.connect(self.start_login)  # 绑定多线程触发事件

        self.label = QtWidgets.QLabel(self)
        self.label.setGeometry(QtCore.QRect(0, 0, 40, 40))
        self.label.setFrameShape(QtWidgets.QFrame.Box)
        # 进度条设置
        self.pbar = QtWidgets.QProgressBar(self)
        self.pbar.setGeometry(50, 50, 210, 25)
        self.pbar.setValue(0)  # 初始进度条设置
        self.num = None
        # 窗口初始化
        self.setGeometry(300, 300, 300, 200)
        self.setWindowTitle('OmegaXYZ.com')
        self.show()
        self.thread = None  # 初始化线程
        self.thread2 = None

    def changednum(self, num):  # 将线程一的参数传给变量，在由主线程信号传出
        self.num = num
        self.signal.emit(self.num)

    def start_login(self):
        # 创建线程
        self.button.setEnabled(False)
        self.thread = Runthread()
        # 连接信号
        self.thread._signal.connect(self.call_backlog)  # 进程连接回传到GUI的事件
        self.thread._signal2.connect(self.changednum)
        # 开始线程
        self.thread.start()
        self.thread2 = SecondThread()
        self.signal.connect(self.thread2.accept)
        self.thread2.sin.connect(self.labelset)
        self.thread2.start()

    def call_backlog(self, msg):
        self.pbar.setValue(int(msg))  # 将线程的参数传入进度条
        if msg == '100':
            self.thread.terminate()  # 结束线程
            self.thread2.terminate()
            self.button.setEnabled(True)  # 激活按钮

    def labelset(self, num):
        self.label.setText(num)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    myshow = UI()
    myshow.show()
    sys.exit(app.exec_())
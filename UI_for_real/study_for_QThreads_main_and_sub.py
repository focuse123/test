from PyQt5.QtWidgets import *
from PyQt5.QtCore import *


class Main(QWidget):
    def __init__(self, parent=None):
        super(Main, self).__init__(parent)

        self.thread1 = MyThread()  # 创建一个线程实例
        self.thread1.setIdentity("thread1")  # 设置线程名称
        self.thread1.sinOut.connect(self.outText)  # 用线程的信号触发UI窗口中的outText函数
        self.thread1.setVal(6)  # 给线程启动函数传递参数

        self.thread2 = MyThread()  # 创建一个线程实例
        self.thread2.setIdentity("thread1")  # 设置线程名称
        self.thread2.sinOut.connect(self.outText)  # 用线程的信号触发UI窗口中的outText函数
        self.thread2.setVal(2)  # 给线程启动函数传递参数

    def outText(self, text):
        print(text)


class MyThread(QThread):
    sinOut = pyqtSignal(str)

    def __init__(self, parent=None):
        super(MyThread, self).__init__(parent)

        self.identity = None

    def setIdentity(self, text):
        self.identity = text

    def setVal(self, val):
        self.times = int(val)

        # 执行线程的run方法
        self.start()

    def run(self):
        while self.times > 0 and self.identity:
            # 发射信号,一个线程发送了6次信号
            self.sinOut.emit(self.identity + " " + str(self.times))
            self.times -= 1


app = QApplication([])

main = Main()
main.show()

app.exec_()
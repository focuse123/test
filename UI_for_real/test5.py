# 在test3基础上修改的
import sys
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QGridLayout
from realUI_b import *
import cv2
import copy
import time
import matplotlib
from collections import deque  # 用于生成双端队列容器（在序列尾部添加或删除元素）
import numpy as np
import threading
import matplotlib.pylab as plt
import threading
import queue
import udp
from xy_extract import *
from motionflag import *

matplotlib.use("Qt5Agg")  # 声明使用QT5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

TIMEWINDOW = 1000
SLIDEWINDOW = TIMEWINDOW / 2
REFRESH_INTERVAL = 0.001
I = 0
flen, blen, slen = 100, 1000, 500  # 100滤波前摇+1000投影+100滤波后摇 = 1200CSI，每次进入500CSI
thr = 0.45


def IO_udp(csi_queue: queue.Queue):
    # 初始化
    print('task io_udp is starting...')
    try:
        counter = 0
        start_flag = True  # 控制接受1200包（启动时间）还是接受500的包（正常工作）
        tfi = int((2 * flen + blen) / 100)  # 启动时间
        raw_CSI = np.zeros((3, 30, 2 * flen + blen), dtype=complex)  # 一个csi.deque元素，3*30*1200
        store_CSI = np.zeros((3, 30, 2 * flen + blen - slen), dtype=complex)  # 承载队列更新工作, 3*30*700
        s = udp.udp_init(5564)  # create a udp handle 指定端口
        # 不断接受udp包
        while True:
            print('----------------')
            data, _ = udp.recv(s)  # receive a udp socket
            print('receive a udp socket')
            Info = []
            for i in range(1, len(data)):
                Info.append(data[i])  # decode csi from udp
            CSI = read_one(Info)  # print(CSI.shape) (3, 30, 1)

            # 获取raw_csi
            if start_flag:  # 启动时间：填满CSI整个队列
                raw_CSI[:, :, counter] = CSI[:, :, 0]
                counter += 1
                # 填满后
                if counter == 1200:
                    csi_queue.put(raw_CSI)  # 入队
                    counter = 0  # 计数器归零
                    store_CSI = raw_CSI[:, :, slen:]  # 丢弃0:slen所有包
                    start_flag = False  # 启动完毕
                # 启动报时
                if counter % 100 == 0:
                    print('初始启动时间总计{}s: 当前{}s'.format(tfi, counter / 100))
            else:  # 工作时间
                # 更新raw_CSI 后slen个包 之前的所有包
                if counter == 0:
                    raw_CSI[:, :, :-slen] = store_CSI
                # 更新raw_CSI的 最后slen个包
                raw_CSI[:, :, store_CSI.shape[2] + counter] = CSI[:, :, 0]
                counter += 1
                if counter == slen:  # 本轮更新结束
                    print(threading.current_thread().name, ": csi.queue.size=", csi_queue.qsize())
                    csi_queue.put(raw_CSI)  # 入队
                    counter = 0  # 计数器归零
                    store_CSI = raw_CSI[:, :, slen:]  # 丢弃0：slen所有包
    except KeyboardInterrupt:
        udp.close(s)  # close udp


def CPU_extract(csi_queue: queue.Queue, wave_queue: queue.Queue):
    print('task cpu_extract is starting...')
    his = 0
    while True:
        raw_CSI = csi_queue.get()
        print(threading.current_thread().name, ": csi.queue.size=", csi_queue.qsize())
        flag = motion_detect(raw_CSI[:, :, -slen:], thr)
        if flag:
            wave = extract(raw_CSI, his)
        else:  # 如果检测到突发性大动作
            oc = np.random.randn(slen) / 10000
            oc = (oc - (oc[0] - his))
            rpm = 0
            wave = [list(oc), rpm]
        his = wave[0][-1]
        wave_queue.put(wave)


class MyFigure(FigureCanvas):
    def __init__(self, width, height, dpi):
        # 创建一个Figure,该Figure为matplotlib下的Figure，不是matplotlib.pyplot下面的Figure
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        # 在父类中激活Figure窗口，此句必不可少，否则不能显示图形
        super(MyFigure, self).__init__(self.fig)
        # 调用Figure下面的add_subplot方法，类似于matplotlib.pyplot下面的subplot(1,1,1)方法
        self.axes = self.fig.add_subplot(111)


class MainWindow(QMainWindow, Ui_Mwbreath):  # 多重继承QMainWindow和Ui_MainWindow
    def __init__(self):
        super(MainWindow, self).__init__()  # 先调用父类QMainWindow的初始化方法
        self.setupUi(self)  # 再调用setupUi方法
        # cv显示参数
        self.timer_camera = QtCore.QTimer()  # 定义定时器，用于控制显示视频的帧率
        self.cap = cv2.VideoCapture()  # 视频流
        self.CAM_NUM = 0  # 为0时表示视频流来自笔记本内置摄像头
        # wave显示参数
        self.timer_waver = QtCore.QTimer()  # 定义定时器，用于控制显示帧率
        self.count = 0
        self.t = deque()
        self.amp = deque()
        self.rpm = deque()
        self.end = False
        self.threads = []
        self.interval = REFRESH_INTERVAL

    # 显示标题
    def on_ab(self):
        QMessageBox.information(self, 'about us', '北京邮电大学先进网络实验室Wi-Fi感知小组成果。\n感谢深圳信息通信研究所大力支持。')

    # 显示帮助
    def on_hb(self):
        QMessageBox.information(self, 'help', '目前版本仅为演示demo。\n如果遇到bug建议重新启动。')

    def on_cv(self):
        if self.timer_camera.isActive() == False:  # 若定时器未启动
            flag = self.cap.open(self.CAM_NUM)  # 参数是0，表示打开笔记本的内置摄像头，参数是视频文件路径则打开视频
            if flag == False:  # flag表示open()成不成功
                msg = QtWidgets.QMessageBox.warning(self, 'warning', "请检查相机于电脑是否连接正确", buttons=QtWidgets.QMessageBox.Ok)
            else:
                self.timer_camera.start(30)  # 定时器开始计时30ms，结果是每过30ms从摄像头中取一帧显示
                self.onbutton.setText('off')
                self.timer_camera.timeout.connect(self.show_camera)
        else:
            self.timer_camera.stop()  # 关闭定时器
            self.cap.release()  # 释放视频流
            self.cvUI.clear()  # 清空视频显示区域
            self.onbutton.setText('on')

    def F_update(self, wave_queue: queue.Queue):
        # 初始化
        print('task F_update is starting...')
        try:
            self.F = MyFigure(width=5, height=3.5, dpi=100)
            while True:
                wave = wave_queue.get()
                print(threading.current_thread().name, ": wave.queue.size=", wave_queue.qsize())
                for i in range(slen):
                    self.push([wave[0][i], wave[1]])
                    time.sleep(0.005)
        except RuntimeError:
            f = self.stop()
            print('task cpu_plot is starting...')
            self.F = MyFigure(width=5, height=3.5, dpi=100)
            while True:
                wave = wave_queue.get()
                print(threading.current_thread().name, ": wave.queue.size=", wave_queue.qsize())
                for i in range(slen):
                    self.push([wave[0][i], wave[1]])
                    time.sleep(0.005)

    def show_camera(self):
        flag, self.image = self.cap.read()  # 从视频流中读取
        show = cv2.resize(self.image, (500, 380))  # 把读到的帧的大小重新设置
        show = cv2.cvtColor(show, cv2.COLOR_BGR2RGB)  # 视频色彩转换回RGB，这样才是现实的颜色
        showImage = QtGui.QImage(show.data, show.shape[1], show.shape[0],
                                 QtGui.QImage.Format_RGB888)  # 把读取到的视频数据变成QImage形式
        self.cvUI.setPixmap(QtGui.QPixmap.fromImage(showImage))  # 往显示视频的Label里 显示QImage

    def on_wave(self):
        if self.timer_waver.isActive() == False:  # 若定时器未启动
            self.timer_waver.start(5)  # 定时器开始计时，结果是每100ms从摄像头中取一帧显示
            self.F = MyFigure(width=5, height=3.5, dpi=100)
            # 画图
            # self.timer_waver.timeout.connect(self.data_update)
            self.timer_waver.timeout.connect(self._plot)
            # 其他显示设置
            self.on2button.setText('off')
        else:
            self.waveUI.clear()

    def data_update(self):
        # 导入数据更新
        # while True:
        global I, wave_queue, data
        if I == 0:
            data = wave_queue.get()
        if data:
            self.push([data[0][I], data[1]])
            I += 1
            if I == 200:
                I = 0

    def push(self, data):
        if self.count > TIMEWINDOW - 1:
            self.t.popleft()  # t中抛出多余参数
            self.amp.popleft()  # amp中抛出多余参数
            self.rpm.popleft()

        self.t.append(self.count)
        self.amp.append(data[0])
        self.rpm.append(data[1])

        self.count += 1
        # print(self.count)

    def _plot(self):
        print("进入了_plot函数")
        t = copy.deepcopy(self.t)
        amp = copy.deepcopy(self.amp)

        if len(t) == 0:
            print(1)
            time.sleep(self.interval)
            self.gridlayout = QGridLayout(self.waveUI)
            self.gridlayout.addWidget(self.F)
        else:
            print(2)
            max_t = t[-1] + 100
            min_t = max_t - TIMEWINDOW if max_t - TIMEWINDOW > 0 else 0
            rpm = self.rpm[-1]

            self.F.axes.cla()
            if rpm == 0:
                self.F.axes.set_title("sorry no person detected !")
                self.F.axes.set_ylim(-0.3, 0.3)
            else:
                if rpm < 11 or rpm > 37:
                    self.F.axes.set_title("big motion or breath stop")
                    self.F.axes.set_ylim(-0.3, 0.3)
                else:
                    self.F.axes.set_title("breath wave with a speed {}rpm".format(rpm))
            self.F.axes.set_xlabel("time/ms")
            # wave1.set_ylim(-2, 2)
            self.F.axes.set_xlim(min_t, max_t)
            self.F.axes.grid()
            self.F.axes.plot(t, np.array(amp))

            self.F.draw_idle()
            # 设置布局
            self.gridlayout = QGridLayout(self.waveUI)
            self.gridlayout.addWidget(self.F)

        # print('update_plot')

        # pause函数功能运行GUI事件循环若干秒。
        # 如果当前有活动的图形，在pause函数运行前，图形将会更新并显示，在等待期间事件循环会一直运行，直到暂停时间interval秒后结束。
        # 如果没有当前有活动的图形，将会调用time.sleep函数，休眠interval秒


if __name__ == '__main__':
    # 多线程
    csi_queue = queue.Queue()
    global wave_queue
    wave_queue = queue.Queue()
    t_io = threading.Thread(target=IO_udp, args=(csi_queue,), name="IO_udp")
    t_extract = threading.Thread(target=CPU_extract, args=(csi_queue, wave_queue), name="CPU_extract")
    t_io.start()
    t_extract.start()
    # UI线程
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('image/favicon.ico'))  # 加载 icon
    ui = MainWindow()
    ui.show()
    t_thread = threading.Thread(target=ui.F_update, args=(wave_queue,), name="t_thread")
    t_thread.start()
    # 结束
    sys.exit(app.exec_())

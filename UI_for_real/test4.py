import sys
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QGridLayout
from PyQt5.QtCore import *
from realUI_b import *
import cv2
import copy
import time
import matplotlib
from collections import deque  # 用于生成双端队列容器（在序列尾部添加或删除元素）
import threading
import queue
import udp
from xy_extract import *
from motionflag import *

matplotlib.use("Qt5Agg")  # 声明使用QT5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


flen, blen, slen = 100, 1000, 500  # 100滤波前摇+1000投影+100滤波后摇 = 1200CSI，每次进入500CSI
thr = 0.45

TIMEWINDOW = 1000
SLIDEWINDOW = TIMEWINDOW / 2
REFRESH_INTERVAL = 0.001
I = 0

class Worker1(QThread):
    sinOut = pyqtSignal(str)

    def __init__(self, parent=None):
        super(Worker1, self).__init__(parent)
        #设置工作状态与初始num数值
        self.working = True
        self.num = 0

    def __del__(self):
        #线程状态改变与线程终止
        self.working = False
        self.wait()

    def run(self):
        while self.working == True:
            #获取文本
            file_str = 'worker1 File index{0}'.format(self.num)
            self.num += 1
            # 发射信号
            self.sinOut.emit(file_str)
            # 线程休眠2秒
            self.sleep(1)


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
        # wave plot显示参数
        self.timer_waver = QtCore.QTimer()  # 定义定时器，用于控制显示帧率
        self.count = 0
        self.t = deque()
        self.amp = deque()
        self.rpm = deque()
        self.end = False
        self.interval = REFRESH_INTERVAL
        # 启动收数据和处理数据的线程
        global csi_queue
        global wave_queue

        self.t_io = threading.Thread(target=self.IO_udp(csi_queue), args=(csi_queue,), name="IO_udp")
        self.t_extract = threading.Thread(target=self.CPU_extract(csi_queue, wave_queue), args=(csi_queue, wave_queue),
                                     name="CPU_extract")
        self.t_plot = threading.Thread(target=self.F_update(wave_queue), args=(wave_queue,), name="CPU_plot")

        self.t_io.start()
        self.t_extract.start()
        self.t_plot.start()

    def on_ab(self):
        QMessageBox.information(self, 'about us', '北京邮电大学先进网络实验室Wi-Fi感知小组成果。\n感谢深圳信息通信研究所大力支持。')

    def on_hb(self):
        QMessageBox.information(self, 'help', '目前版本仅为演示demo。\n如果遇到bug建议重新启动。')

    def on_cv(self):  # 实时摄像头模块槽函数，点击操作+画面更新
        if self.timer_camera.isActive() == False:  # 若定时器未启动
            flag = self.cap.open(self.CAM_NUM)  # 参数是0，表示打开笔记本的内置摄像头，参数是视频文件路径则打开视频
            if flag == False:  # flag表示open()成不成功
                QtWidgets.QMessageBox.warning(self, 'warning', "请检查相机于电脑是否连接正确", buttons=QtWidgets.QMessageBox.Ok)
            else:
                self.timer_camera.start(30)  # 定时器开始计时30ms，结果是每过30ms从摄像头中取一帧显示
                self.onbutton.setText('off')
                self.timer_camera.timeout.connect(self.show_camera)
        else:
            self.timer_camera.stop()  # 关闭定时器
            self.cap.release()  # 释放视频流
            self.cvUI.clear()  # 清空视频显示区域
            self.onbutton.setText('on')

    def show_camera(self):  # 摄像头显示
        flag, self.image = self.cap.read()  # 从视频流中读取
        show = cv2.resize(self.image, (500, 380))  # 把读到的帧的大小重新设置
        show = cv2.cvtColor(show, cv2.COLOR_BGR2RGB)  # 视频色彩转换回RGB，这样才是现实的颜色
        showImage = QtGui.QImage(show.data, show.shape[1], show.shape[0],
                                 QtGui.QImage.Format_RGB888)  # 把读取到的视频数据变成QImage形式
        self.cvUI.setPixmap(QtGui.QPixmap.fromImage(showImage))  # 往显示视频的Label里 显示QImage

    def on_wave(self):
        if self.timer_waver.isActive() == False:  # 若定时器未启动
            self.timer_waver.start(100)  # 定时器开始计时，结果是每100ms从wavefigure中取一帧显示
            self.F = MyFigure(width=5, height=3.5, dpi=100)
            # 画图
            self.timer_waver.timeout.connect(self._plot)
            # 其他显示设置
            self.on2button.setText('off')
        else:
            self.waveUI.clear()

    def IO_udp(self, csi_queue: queue.Queue):
        # 初始化
        print('task io_udp is starting...')
        try:
            counter = 0
            start_flag = True  # 控制接受1200包（启动时间）还是接受500的包（正常工作）
            tfi = int((2 * flen + blen) / 100)  # 启动时间
            raw_CSI = np.zeros((3, 30, 2 * flen + blen), dtype=complex)  # 一个csi.deque元素，3*30*1200
            store_CSI = np.zeros((3, 30, 2 * flen + blen - slen), dtype=complex)  # 承载队列更新工作, 3*30*700
            s = udp.udp_init(5563)  # create a udp handle 指定端口
            # 不断接受udp包
            while True:
                data, _ = udp.recv(s)  # receive a udp socket
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

    def CPU_extract(self, csi_queue: queue.Queue, wave_queue: queue.Queue):
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

    def _plot(self):
        t = copy.deepcopy(self.t)
        amp = copy.deepcopy(self.amp)

        if len(t) == 0:
            time.sleep(self.interval)
            self.gridlayout = QGridLayout(self.waveUI)
            self.gridlayout.addWidget(self.F)
        else:
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

    def push(self, data):  # data = [[300*1] [1*1]]

        if self.count > TIMEWINDOW - 1:
            self.t.popleft()  # t中抛出多余参数
            self.amp.popleft()  # amp中抛出多余参数
            self.rpm.popleft()

        self.t.append(self.count)
        self.amp.append(data[0])
        self.rpm.append(data[1])

        self.count += 1

    def stop(self):
        print('stop realview****')
        self.t_io.join()
        self.t_extract.join()
        self.t_plot.join()

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


if __name__ == '__main__':
    # 多线程pipeline队列
    csi_queue = queue.Queue()
    wave_queue = queue.Queue()
    # UI线程
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('image/favicon.ico'))  # 加载 icon
    ui = MainWindow()
    ui.show()
    # 结束
    sys.exit(app.exec_())

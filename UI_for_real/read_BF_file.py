# ver-for-向扬
# 使用方法
# antennaPair_One, antennaPair_Two, antennaPair_Three = readFile(filepath)
# 其中filepath为CSI数据包所在的路径
import os
import struct
import numpy as np


class WifiCsi:
    def __init__(self, args, csi):  # 定义WiFi CSI类，其中会用上的只有csi复数数据，视频和CSI对应的视频时间戳另外保存
        self.timestamp_low = args[0]
        self.bfee_count = args[1]
        self.Nrx = args[2]
        self.Ntx = args[3]
        self.rssi_a = args[4]
        self.rssi_b = args[5]
        self.rssi_c = args[6]
        self.noise = args[7]
        self.agc = args[8]
        self.perm = args[9]
        self.rate = args[10]
        self.csi = csi
        pass


def read_file(file_path):
    # 得到WiFi CSI实例，一共Tx*Rx*F*T个
    length = os.path.getsize(file_path)
    cur = 0
    csi_data = []
    with open(file_path, 'rb') as f:
        while cur < (length - 3):
            filed_length = struct.unpack("!H", f.read(2))[0]
            code = struct.unpack("!B", f.read(1))[0]  # code=187
            cur += 3
            if code == 187:
                global data
                data = []
                for _ in range(filed_length - 1):
                    data.append(struct.unpack("!B", f.read(1))[0])
                cur += filed_length - 1
                if len(data) != filed_length - 1:
                    break
            else:
                f.seek(filed_length - 1, 1)
                cur = cur + filed_length - 1
            csi_data.append(read_bfee(data))
        return csi_data


def read_bfee(in_bytes):
    """
    从数据包中获取csi数据
    :param in_bytes: 
    :return: 
    """
    # 时间戳
    timestamp_low = in_bytes[0] + (in_bytes[1] << 8) + \
                    (in_bytes[2] << 16) + (in_bytes[3] << 24)
    # 波束测量值的总数
    bfee_count = in_bytes[4] + (in_bytes[5] << 24)
    # 接收端使用的天线数量
    Nrx = in_bytes[8]
    # 发送端使用的天线数量
    Ntx = in_bytes[9]
    # 由接收端NIC测量出的RSSI值。
    rssi_a = in_bytes[10]
    rssi_b = in_bytes[11]
    rssi_c = in_bytes[12]
    # 噪声
    noise = get_bit_num(in_bytes[13], 8)
    agc = in_bytes[14]
    antenna_sel = in_bytes[15]
    length = in_bytes[16] + (in_bytes[17] << 8)
    fake_rate_n_flags = in_bytes[18] + (in_bytes[19] << 8)
    calc_len = (30 * (Nrx * Ntx * 8 * 2 + 3) + 7) / 8
    payload = in_bytes[20:]

    # if(length != calc_len)

    perm_size = 3
    perm = np.zeros(perm_size, dtype=int)
    # print(perm.shape)
    # perm展示NIC如何将3个接收天线的信号排列到3个RF链上
    perm[0] = (antenna_sel & 0x3) + 1
    perm[1] = ((antenna_sel >> 2) & 0x3) + 1
    perm[2] = ((antenna_sel >> 4) & 0x3) + 1

    index = 0

    csi_size = (30, Ntx, Nrx)
    row_csi = np.ndarray(csi_size, dtype=complex)
    perm_csi = np.ndarray(csi_size, dtype=complex)

    for i in range(30):
        index += 3
        remainder = index % 8
        for j in range(Nrx):
            for k in range(Ntx):
                # 实部
                pr = get_bit_num((payload[index // 8] >> remainder), 8) | get_bit_num(
                    (payload[index // 8 + 1] << (8 - remainder)), 8)
                # 虚部
                pi = get_bit_num((payload[(index // 8) + 1] >> remainder), 8) | get_bit_num(
                    (payload[(index // 8) + 2] << (8 - remainder)), 8)
                # perm_csi是csi数据
                perm_csi[i][k][perm[j] - 1] = complex(pr, pi)
                # print("输出的csi为: ",perm_csi)
                index += 16
                pass
            pass
        pass
    pass
    # args(arguments)参数
    args = [timestamp_low, bfee_count, Nrx, Ntx, rssi_a,
            rssi_b, rssi_c, noise, agc, perm, fake_rate_n_flags]
    # 实例化WifiCsi类，命名为temp_wifi_csi
    temp_wifi_csi = WifiCsi(args, perm_csi)
    return temp_wifi_csi


def get_bit_num(in_num, data_length):
    max_value = (1 << data_length - 1) - 1
    if not -max_value - 1 <= in_num <= max_value:
        out_num = (in_num + (max_value + 1)) % (2 * (max_value + 1)) - max_value - 1
    else:
        out_num = in_num
    return out_num
    pass


def read_file(file_path):
    csi_data = []
    csi_data.append(read_bfee(file_path))
    return csi_data


def mkdir(path):
    folder = os.path.exists(path)
    if not folder:  # 判断是否存在文件夹如果不存在则创建为文件夹
        os.makedirs(path)  # makedirs 创建文件时如果路径不存在会创建这个路径


def read_one(filepath):
    # 每次处理1个包
    file = read_file(filepath)
    antennaPair_One, antennaPair_Two, antennaPair_Three = [], [], []
    for item in file:
        for eachcsi in range(0, 30):
            ''''
            acquire csi complex value for each antenna pair with shape ( len(file) * 30), 
            i.e.,packet number * subcarrier number
            '''
            antennaPair_One.append(item.csi[eachcsi][0][0])
            antennaPair_Two.append(item.csi[eachcsi][0][1])
            antennaPair_Three.append(item.csi[eachcsi][0][2])
    antennaPair_One = np.reshape(antennaPair_One, (len(file), 30)).transpose()
    antennaPair_Two = np.reshape(antennaPair_Two, (len(file), 30)).transpose()
    antennaPair_Three = np.reshape(antennaPair_Three, (len(file), 30)).transpose()
    raw_CSI = np.array([antennaPair_One, antennaPair_Two, antennaPair_Three])
    return raw_CSI

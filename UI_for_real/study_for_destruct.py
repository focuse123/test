class Test(object):
    name = '小雷'
    address = '上海市'

    def __init__(self, name, age):
        self.name = name
        self.age = age
        print('这里是构造方法')

    def test1(self):
        print(self.name, self.age)

    def __del__(self):
        print('这里是析构函数，清理了')

    def test2(self):
        print(self.name, Test.address)

    def test3(self):
        print('准备被清理的')


# Test1 = Test('小张', 22)
# Test1.test1()
# Test1.test2()
# Test1.test3()

Test2 = Test('王大大', 33)
Test2.test1()
Test2.test2()
# del Test2  # 显示调用了析构函数
Test2.__del__()  # 一般不这样,而是利用python的
# Test2.test3()

# 试验证明
# 1、析构函数__del__等所有程序执行完才会执行
# 2、被del的方法，无法再被调用
# 3、析构函数会自动被调用
# 4、del 方法，会调用析构函数

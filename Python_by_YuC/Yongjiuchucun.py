Python 3.9.13 (tags/v3.9.13:6de2ca5, May 17 2022, 16:36:42) [MSC v.1929 64 bit (AMD64)] on win32
Type "help", "copyright", "credits" or "license()" for more information.
>>> open("FishC.txt","w")
<_io.TextIOWrapper name='FishC.txt' mode='w' encoding='cp936'>
>>> f = open("FishC.txt","w")
>>> f.write("I love Zach")
11
>>> f.close()
>>> with open("FishC.txt"."w")as f:
	
SyntaxError: invalid syntax
>>> with open("FishC.txt","w")as f:
	f.write("I love Zach.")

	
12
>>> # 用with 上下文管理器不需要手动关闭代码
>>> 
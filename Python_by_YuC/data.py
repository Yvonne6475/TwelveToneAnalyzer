import pickle

x,y,z = 1,2,3
s = "FishC"
t = ["小甲鱼",520, 3.14]
d = {"one": 1, "two":2}


with open("data.pkl","wb")as f:
     pickle.dump(x,f)
     pickle.dump(y,f)
     pickle.dump(z,f)
     pickle.dump(s,f)
     pickle.dump(t,f)
     pickle.dump(d,f)

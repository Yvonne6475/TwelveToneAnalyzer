import pickle

with open("data.pkl","rb")as f:
    x = pickle.load(f)
    y = pickle.load(f)
    z = pickle.load(f)
    s = pickle.load(f)
    t = pickle.load(f)
    d = pickle.load(f)
print(x,y,z,s,t,d, sep="\n")
     

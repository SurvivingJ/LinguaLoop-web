import numpy as np
def info(theta,a,b,c):
    s=1/(1+np.exp(-a*(theta-b))); P=c+(1-c)*s
    return a**2*((P-c)**2/((1-c)**2))*((1-P)/P)
th=np.linspace(-6,6,24001)
print("a, c, Imax, theta_at_max-b, P_at_max, items_for_SE(0.5,0.4,0.3) at perfect targeting")
for a in (1.0,1.5,2.0):
    for c in (0.0,0.25):
        I=info(th,a,0,c); i=I.argmax(); P=c+(1-c)/(1+np.exp(-a*th[i]))
        print(a,c,round(I.max(),4),round(th[i],3),round(P,3),[int(np.ceil(1/(se**2*I.max()))) for se in (0.5,0.4,0.3)])
# off-target: item 1 logit too easy/hard
for a in (1.0,1.5):
  for d in (0.5,1.0,1.5):
    for c in (0.0,0.25):
        print("a",a,"offset",d,"c",c,"info rel to max", round(info(np.array([d]),a,0,c)[0]/info(th,a,0,c).max(),3), round(info(np.array([-d]),a,0,c)[0]/info(th,a,0,c).max(),3))

import time, numpy as np
from lib import cargar, resumen, CORTE
from sim import Velas, p11, p05b, a_tabla, netos
t0=time.time(); V=Velas(cargar())
t=a_tabla(p11(V)); print(resumen(t.bruto,"P11 bruto"), resumen(netos(t),"P11 neto"), resumen(netos(t,0.10),"P11 doble"), sep="\n")
t=a_tabla(p05b(V)); print(resumen(t.bruto,"P05b bruto"), resumen(netos(t),"P05b neto 0,02+0,05"), resumen(netos(t,0.10,0.04),"P05b doble"), sep="\n")
print(time.time()-t0)

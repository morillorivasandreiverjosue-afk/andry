import json
def load(S):
    T=json.load(open(f"{S}/build/timeline.json"))
    def to(fi,t):
        for f,a,b,o in T["pieces"]:
            if f==fi and a-0.05<=t<=b+0.05: return o+max(0,t-a)
        # dentro de un corte: devuelve inicio de la siguiente pieza
        for f,a,b,o in T["pieces"]:
            if f==fi and a>=t: return o
        return None
    return T,to

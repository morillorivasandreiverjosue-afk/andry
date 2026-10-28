"""Real-ESRGAN x4plus sin PyTorch: lee los pesos .pth y ejecuta la red con numpy.

Uso como módulo:  esrgan.ampliar(imagen_rgb_uint8, ruta_pth) -> imagen 4 veces más grande
"""
import pickle
import zipfile

import numpy as np


# ------------------------------------------------------------------ lectura del .pth
class Diccionario(dict):
    """dict que admite los metadatos que PyTorch guarda junto a los pesos."""


def cargar_pesos(ruta):
    z = zipfile.ZipFile(ruta)
    raiz = z.namelist()[0].split("/")[0]
    tipos = {"FloatStorage": np.float32, "HalfStorage": np.float16}

    def reconstruir(storage, offset, tam, pasos, *_):
        datos, dtype = storage
        arr = np.frombuffer(datos, dtype=dtype)
        return np.lib.stride_tricks.as_strided(arr[offset:], tam, [p * arr.itemsize for p in pasos]).copy()

    class Lector(pickle.Unpickler):
        # solo se admiten tensores y diccionarios: cualquier otra cosa del archivo se rechaza
        def find_class(self, mod, nombre):
            if (mod, nombre) == ("torch._utils", "_rebuild_tensor_v2"):
                return reconstruir
            if (mod, nombre) == ("collections", "OrderedDict"):
                return Diccionario
            if mod == "torch" and nombre in tipos:
                return nombre
            raise pickle.UnpicklingError(f"objeto no permitido en el modelo: {mod}.{nombre}")

        def persistent_load(self, pid):
            _, tipo, clave, *_ = pid
            return z.read(f"{raiz}/data/{clave}"), tipos[tipo]

    d = Lector(z.open(f"{raiz}/data.pkl")).load()
    d = d.get("params_ema", d.get("params", d))
    return {k: v.astype(np.float32) for k, v in d.items()}


# ------------------------------------------------------------------ red RRDBNet
def conv(x, w, b):
    """Convolución 3x3 (padding 1) sobre x[H, W, C] como 9 multiplicaciones de matrices."""
    h, ww, _ = x.shape
    p = np.pad(x, ((1, 1), (1, 1), (0, 0)), mode="constant")
    salida = np.broadcast_to(b, (h, ww, len(b))).copy()
    for dy in range(3):
        for dx in range(3):
            salida += p[dy:dy + h, dx:dx + ww] @ w[:, :, dy, dx].T
    return salida


def lrelu(x):
    return np.maximum(x, 0.2 * x)


def red(P, x):
    c = lambda nombre, t: conv(t, P[nombre + ".weight"], P[nombre + ".bias"])
    feat = c("conv_first", x)
    cuerpo = feat
    for i in range(23):
        entrada_rrdb = cuerpo
        for j in (1, 2, 3):
            pre = f"body.{i}.rdb{j}."
            partes = [cuerpo]
            for k in range(1, 5):
                partes.append(lrelu(c(pre + f"conv{k}", np.concatenate(partes, axis=2))))
            cuerpo = c(pre + "conv5", np.concatenate(partes, axis=2)) * 0.2 + cuerpo
        cuerpo = cuerpo * 0.2 + entrada_rrdb
    feat = feat + c("conv_body", cuerpo)
    feat = lrelu(c("conv_up1", feat.repeat(2, 0).repeat(2, 1)))
    feat = lrelu(c("conv_up2", feat.repeat(2, 0).repeat(2, 1)))
    return c("conv_last", lrelu(c("conv_hr", feat)))


def ampliar(img, ruta_pth, tile=160, margen=12, aviso=None):
    """img: uint8 RGB [H, W, 3]. Procesa por trozos para no gastar demasiada memoria."""
    P = cargar_pesos(ruta_pth)
    x = img.astype(np.float32) / 255.0
    h, w, _ = x.shape
    salida = np.zeros((h * 4, w * 4, 3), np.float32)
    trozos = [(y, xx) for y in range(0, h, tile) for xx in range(0, w, tile)]
    for n, (y, xx) in enumerate(trozos):
        y0, x0 = max(0, y - margen), max(0, xx - margen)
        y1, x1 = min(h, y + tile + margen), min(w, xx + tile + margen)
        r = red(P, x[y0:y1, x0:x1])
        ty1, tx1 = min(h, y + tile), min(w, xx + tile)
        salida[y * 4:ty1 * 4, xx * 4:tx1 * 4] = r[(y - y0) * 4:(ty1 - y0) * 4, (xx - x0) * 4:(tx1 - x0) * 4]
        if aviso:
            aviso(n + 1, len(trozos))
    return (np.clip(salida, 0, 1) * 255).round().astype(np.uint8)

"""UTM no SIRGAS 2000 (elipsoide GRS80), sem bibliotecas de fora.

Projeção transversa de Mercator pelas séries de Krüger em *n* (6ª ordem, como em Karney,
2011, "Transverse Mercator with an accuracy of a few nanometers"): erro de nanômetros dentro
do fuso — muito abaixo de qualquer coisa que importe aqui. Os testes conferem com o pyproj.

O SIRGAS 2000 é o datum oficial do Brasil (e o dos arquivos da ANP); para fins práticos,
coincide com o WGS 84 (diferença de centímetros).
"""

from __future__ import annotations

import math

import numpy as np

A = 6378137.0                    # GRS80
F = 1 / 298.257222101
K0 = 0.9996
FALSO_LESTE = 500000.0
FALSO_NORTE_SUL = 10000000.0

_n = F / (2 - F)
_A1 = A / (1 + _n) * (1 + _n ** 2 / 4 + _n ** 4 / 64 + _n ** 6 / 256)
_ALFA = [None,
         _n / 2 - 2 * _n ** 2 / 3 + 5 * _n ** 3 / 16 + 41 * _n ** 4 / 180 - 127 * _n ** 5 / 288 + 7891 * _n ** 6 / 37800,
         13 * _n ** 2 / 48 - 3 * _n ** 3 / 5 + 557 * _n ** 4 / 1440 + 281 * _n ** 5 / 630 - 1983433 * _n ** 6 / 1935360,
         61 * _n ** 3 / 240 - 103 * _n ** 4 / 140 + 15061 * _n ** 5 / 26880 + 167603 * _n ** 6 / 181440,
         49561 * _n ** 4 / 161280 - 179 * _n ** 5 / 168 + 6601661 * _n ** 6 / 7257600,
         34729 * _n ** 5 / 80640 - 3418889 * _n ** 6 / 1995840,
         212378941 * _n ** 6 / 319334400]
_BETA = [None,
         _n / 2 - 2 * _n ** 2 / 3 + 37 * _n ** 3 / 96 - _n ** 4 / 360 - 81 * _n ** 5 / 512 + 96199 * _n ** 6 / 604800,
         _n ** 2 / 48 + _n ** 3 / 15 - 437 * _n ** 4 / 1440 + 46 * _n ** 5 / 105 - 1118711 * _n ** 6 / 3870720,
         17 * _n ** 3 / 480 - 37 * _n ** 4 / 840 - 209 * _n ** 5 / 4480 + 5569 * _n ** 6 / 90720,
         4397 * _n ** 4 / 161280 - 11 * _n ** 5 / 504 - 830251 * _n ** 6 / 7257600,
         4583 * _n ** 5 / 161280 - 108847 * _n ** 6 / 3991680,
         20648693 * _n ** 6 / 638668800]
_E = math.sqrt(F * (2 - F))


def fuso(lon: float) -> int:
    """Fuso UTM da longitude (graus)."""
    return int(math.floor((lon + 180.0) / 6.0)) + 1


def meridiano_central(z: int) -> float:
    return -183.0 + 6.0 * z


def epsg(z: int, sul: bool = True) -> int:
    """Código EPSG do SIRGAS 2000 / UTM (17S–25S: 31977–31985; 18N–22N: 31972–31976)."""
    return (31960 if sul else 31954) + z


def para_utm(lat, lon, z: int | None = None, sul: bool | None = None):
    """(leste, norte) em metros. Sem `z`, o fuso da primeira longitude; sem `sul`, pelo sinal
    da primeira latitude. Pontos fora do fuso escolhido também funcionam (até ~3° além)."""
    lat = np.asarray(lat, float)
    lon = np.asarray(lon, float)
    if z is None:
        z = fuso(float(np.ravel(lon)[0]))
    if sul is None:
        sul = float(np.ravel(lat)[0]) < 0
    phi = np.radians(lat)
    lam = np.radians(lon - meridiano_central(z))
    t = np.sinh(np.arctanh(np.sin(phi)) - _E * np.arctanh(_E * np.sin(phi)))
    xi_l = np.arctan2(t, np.cos(lam))
    eta_l = np.arctanh(np.sin(lam) / np.sqrt(1 + t ** 2))
    xi, eta = xi_l.copy(), eta_l.copy()
    for j in range(1, 7):
        xi = xi + _ALFA[j] * np.sin(2 * j * xi_l) * np.cosh(2 * j * eta_l)
        eta = eta + _ALFA[j] * np.cos(2 * j * xi_l) * np.sinh(2 * j * eta_l)
    leste = FALSO_LESTE + K0 * _A1 * eta
    norte = K0 * _A1 * xi + (FALSO_NORTE_SUL if sul else 0.0)
    return leste, norte


def de_utm(leste, norte, z: int, sul: bool = True):
    """(lat, lon) em graus."""
    leste = np.asarray(leste, float)
    norte = np.asarray(norte, float)
    xi = (norte - (FALSO_NORTE_SUL if sul else 0.0)) / (K0 * _A1)
    eta = (leste - FALSO_LESTE) / (K0 * _A1)
    xi_l, eta_l = xi.copy(), eta.copy()
    for j in range(1, 7):
        xi_l = xi_l - _BETA[j] * np.sin(2 * j * xi) * np.cosh(2 * j * eta)
        eta_l = eta_l - _BETA[j] * np.cos(2 * j * xi) * np.sinh(2 * j * eta)
    tau_l = np.sin(xi_l) / np.sqrt(np.sinh(eta_l) ** 2 + np.cos(xi_l) ** 2)
    lam = np.arctan2(np.sinh(eta_l), np.cos(xi_l))
    tau = tau_l.copy()                                   # Newton para a latitude conforme
    for _ in range(6):
        sigma = np.sinh(_E * np.arctanh(_E * tau / np.sqrt(1 + tau ** 2)))
        tau_i = tau * np.sqrt(1 + sigma ** 2) - sigma * np.sqrt(1 + tau ** 2)
        d = (tau_l - tau_i) / np.sqrt(1 + tau_i ** 2) * (1 + (1 - _E ** 2) * tau ** 2) / \
            ((1 - _E ** 2) * np.sqrt(1 + tau ** 2))
        tau = tau + d
        if np.all(np.abs(d) < 1e-14):
            break
    return np.degrees(np.arctan(tau)), np.degrees(lam) + meridiano_central(z)


def wkt(z: int, sul: bool = True) -> str:
    """WKT (ESRI, para o .prj) do SIRGAS 2000 / UTM."""
    return ('PROJCS["SIRGAS_2000_UTM_Zone_%d%s",GEOGCS["GCS_SIRGAS_2000",DATUM["D_SIRGAS_2000",'
            'SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],'
            'UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],'
            'PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",%.1f],'
            'PARAMETER["Central_Meridian",%.1f],PARAMETER["Scale_Factor",0.9996],'
            'PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'
            % (z, "S" if sul else "N", FALSO_NORTE_SUL if sul else 0.0, meridiano_central(z)))

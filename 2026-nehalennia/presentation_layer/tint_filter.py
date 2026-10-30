"""Fit a CSS `filter` chain that recolours black line art to a target colour.

`assets/title.gif` is black strokes on transparency. CSS cannot tint an image to
a custom property, so the `.clipart` rule in `scss/main.scss` carries a fitted
filter chain instead. Run this when the accent changes and paste the result in.

    python3 -I tint_filter.py '#ff5533'

Caveat: the fit is done against the spec's sRGB maths, and browsers do not match
it exactly. The last fit for #ff5533 rendered as about #ff672b in Chromium —
close, but not the same colour. Check the result rather than trusting it.
"""

import math
import random
import sys

DEFAULT = '#ff5533'


def clamp(v):
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def mat(c, m):
    r, g, b = c
    return tuple(clamp(m[i][0] * r + m[i][1] * g + m[i][2] * b) for i in range(3))


def invert(c, a):
    return tuple(clamp(v + a * (1 - 2 * v)) for v in c)


def sepia(c, s):
    base = [[0.393, 0.769, 0.189], [0.349, 0.686, 0.168], [0.272, 0.534, 0.131]]
    ident = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    m = [[ident[i][j] + s * (base[i][j] - ident[i][j]) for j in range(3)] for i in range(3)]
    return mat(c, m)


def saturate(c, s):
    lr, lg, lb = 0.213, 0.715, 0.072
    m = [
        [lr + s * (1 - lr), lg * (1 - s), lb * (1 - s)],
        [lr * (1 - s), lg + s * (1 - lg), lb * (1 - s)],
        [lr * (1 - s), lg * (1 - s), lb + s * (1 - lb)],
    ]
    return mat(c, m)


def hue_rotate(c, deg):
    a = math.radians(deg)
    cs, sn = math.cos(a), math.sin(a)
    m = [
        [0.213 + cs * 0.787 - sn * 0.213, 0.715 - cs * 0.715 - sn * 0.715,
         0.072 - cs * 0.072 + sn * 0.928],
        [0.213 - cs * 0.213 + sn * 0.143, 0.715 + cs * 0.285 + sn * 0.140,
         0.072 - cs * 0.072 - sn * 0.283],
        [0.213 - cs * 0.213 - sn * 0.787, 0.715 - cs * 0.715 + sn * 0.715,
         0.072 + cs * 0.928 + sn * 0.072],
    ]
    return mat(c, m)


def apply(p):
    """Run the chain on black, which is what the strokes are."""
    inv, sep, sat, hue, bri, con = p
    c = (0.0, 0.0, 0.0)
    c = invert(c, inv)
    c = sepia(c, sep)
    c = saturate(c, sat)
    c = hue_rotate(c, hue)
    c = tuple(clamp(v * bri) for v in c)
    c = tuple(clamp(v * con + (0.5 - 0.5 * con)) for v in c)
    return c


def fit(target):
    def err(p):
        c = apply(p)
        return sum((c[i] - target[i]) ** 2 for i in range(3))

    rng = random.Random(0)
    best, best_e = None, float('inf')
    for _ in range(60000):
        p = (rng.uniform(0.2, 0.9), 1.0, rng.uniform(1, 30), rng.uniform(-80, 80),
             rng.uniform(0.5, 2.5), rng.uniform(0.5, 2.5))
        e = err(p)
        if e < best_e:
            best, best_e = p, e

    step = [0.05, 0.0, 1.0, 4.0, 0.08, 0.08]
    for _ in range(14):
        improved = True
        while improved:
            improved = False
            for i in range(6):
                for d in (+1, -1):
                    q = list(best)
                    q[i] += d * step[i]
                    e = err(tuple(q))
                    if e < best_e:
                        best, best_e = tuple(q), e
                        improved = True
        step = [s / 2 for s in step]
    return best


def main():
    hex_colour = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT).lstrip('#')
    target = tuple(int(hex_colour[i:i + 2], 16) / 255 for i in (0, 2, 4))

    inv, sep, sat, hue, bri, con = fit(target)
    got = apply((inv, sep, sat, hue, bri, con))

    print('filter: invert(%.1f%%) sepia(%.0f%%) saturate(%.0f%%) hue-rotate(%.0fdeg)'
          ' brightness(%.0f%%) contrast(%.0f%%);'
          % (inv * 100, sep * 100, sat * 100, hue % 360, bri * 100, con * 100))
    print('modelled #%02x%02x%02x, wanted #%s'
          % (round(got[0] * 255), round(got[1] * 255), round(got[2] * 255), hex_colour))


if __name__ == '__main__':
    main()

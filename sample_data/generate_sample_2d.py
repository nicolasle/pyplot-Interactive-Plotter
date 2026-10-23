import numpy as np
import os

x = np.linspace(-3, 3, 30)
y = np.linspace(-3, 3, 30)
X, Y = np.meshgrid(x, y)
Z = np.exp(-(X**2 + Y**2)/2.0) + 0.1 * np.sin(3*X) * np.cos(3*Y)

np.savetxt("sample_data/surface_map_2d.txt", Z, fmt="%.5f")
print("Saved 2D surface map matrix (30x30).")

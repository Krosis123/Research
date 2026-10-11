import numpy as np

psi = np.array([
    0.5,
    0,
    0.5,
    0,
    0.5,
    0,
    0.5,
    0
],dtype=complex)

norm = np.linalg.norm(psi)
print(norm)

R = np.diag([1,-1,1,-1,1,-1,1,-1])
print(R)



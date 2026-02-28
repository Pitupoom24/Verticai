import numpy as np

def calculate_angle(a, b, c):
    """
    a, b, c are (x, y) tuples
    Angle is calculated at point b
    """

    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    ba = a - b
    bc = c - b

    dot_product = np.dot(ba, bc)
    magnitude = np.linalg.norm(ba) * np.linalg.norm(bc)

    angle_rad = np.arccos(dot_product / magnitude)
    angle_deg = np.degrees(angle_rad)

    return angle_deg
from math import sqrt, pi

class Vector2():
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y
    
    def __str__(self):
        return f"X: {self.x}, Y: {self.y}"
    
    def __eq__(self, value):
        return (
            isinstance(value, Vector2)
            and self.x == value.x
            and self.y == value.y
        )

    def __add__(self, value):
        return Vector2(self.x + value.x, self.y + value.y)

    def __sub__(self, value):
        return Vector2(self.x - value.x, self.y - value.y)
    
    def __mul__(self, value):
        if isinstance(value, Vector2):
            return Vector2(self.x * value.x, self.y * value.y)
        return Vector2(self.x * value, self.y * value)
    
    __rmul__ = __mul__

    def __truediv__(self, value):
        if isinstance(value, Vector2):
            return Vector2(self.x / value.x, self.y / value.y)
        return Vector2(self.x / value, self.y / value)
    
    def __neg__(self):
        return Vector2(-self.x, -self.y)

class Vector3():
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z
    
    def __str__(self):
        return f"X: {self.x}, Y: {self.y}, Z: {self.z}"
    
    def __eq__(self, value):
        eps = 1e-9

        return (
            isinstance(value, Vector3)
            and abs(value.x - self.x) < eps
            and abs(value.y - self.y) < eps
            and abs(value.z - self.z) < eps
        )
    
    def __add__(self, value):
        return Vector3(self.x + value.x, self.y + value.y, self.z + value.z)

    def __sub__(self, value):
        return Vector3(self.x - value.x, self.y - value.y, self.z - value.z)
    
    def __mul__(self, value):
        if isinstance(value, Vector3):
            return Vector3(self.x * value.x, self.y * value.y, self.z * value.z)
        return Vector3(self.x * value, self.y * value, self.z * value)
    
    __rmul__ = __mul__

    def __truediv__(self, value):
        if isinstance(value, Vector3):
            return Vector3(self.x / value.x, self.y / value.y, self.z / value.z)
        return Vector3(self.x / value, self.y / value, self.z / value)
    
    def __neg__(self):
        return Vector3(-self.x, -self.y, -self.z)

    def dot(self, value):
        return self.x * value.x + self.y * value.y + self.z * value.z

    def cross(self, value):
        return Vector3(
            self.y * value.z - self.z * value.y,
            self.z * value.x - self.x * value.z,
            self.x * value.y - self.y * value.x
        )
    
    def magnitude(self):
        return sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)
    
    def unit(self):
        m = self.magnitude()

        return Vector3(self.x / m, self.y / m, self.z / m) if m != 0 else Vector3()

    def lerp(self, value, rel):
        return self + (value - self) * rel

class CFrame():
    def __init__(self, position=None, right=None, up=None, look=None):
        self.position = position or Vector3(0, 0, 0)

        if right is None and up is None and look is None:
            self.rightvector = Vector3(1, 0, 0)
            self.upvector = Vector3(0, 1, 0)
            self.lookvector = Vector3(0, 0, -1)
        else:
            r, u, l = self._orthonormal_basis(right, up, look)
            self.rightvector, self.upvector, self.lookvector = r, u, l

    @classmethod
    def new(cls, x=0, y=0, z=0):
        return cls(position=Vector3(x, y, z))

    def __str__(self):
        return f"P: {str(self.position)}, R: {str(self.rightvector)}, U: {str(self.upvector)}, L: {str(self.lookvector)}"

    def _rotate_vector(self, v):
        return (
            self.rightvector * v.X +
            self.upvector * v.Y +
            self.lookvector * v.Z
        )

    def _inverse_rotate_vector(self, v):
        return Vector3(
            v.dot(self.rightvector),
            v.dot(self.upvector),
            v.dot(self.lookvector)
        )

    @staticmethod
    def _orthonormal_basis(right=None, up=None, look=None):
        def unit(v):
            return v.unit() if isinstance(v, Vector3) else None

        def nearly_parallel(a, b):
            ma, mb = a.magnitude(), b.magnitude()
            if ma == 0 or mb == 0:
                return True
            return abs(a.dot(b) / (ma * mb)) > 0.9999

        def orthogonal_to(v):
            fallback = Vector3(0, 1, 0)
            if nearly_parallel(v, fallback):
                fallback = Vector3(1, 0, 0)
            return (fallback - v * fallback.dot(v)).unit()

        r = unit(right)
        u = unit(up)
        l = unit(look)

        if r is not None and u is not None:
            u = (u - r * u.dot(r)).unit()
            l = -r.cross(u).unit()
            return r, u, l
        
        if r is not None and l is not None:
            l = (l - r * l.dot(r)).unit()
            u = l.cross(r).unit()
            return r, u, l
        
        if u is not None and l is not None:
            l = (l - u * l.dot(l)).unit()
            r = l.cross(u).unit()
            return r, u, l
        
        if r is not None:
            u = orthogonal_to(r)
            l = -r.cross(u).unit()
            return r, u, l
        
        if u is not None:
            r = orthogonal_to(u)
            l = -r.cross(u).unit()
            return r, u, l
        
        if l is not None:
            u = orthogonal_to(l)
            r = l.cross(u).unit()
            return r, u, l

        return Vector3(1, 0, 0), Vector3(0, 1, 0), Vector3(0, 0, -1)

    def __mul__(self, other):
        if isinstance(other, CFrame):
            rotated_pos = self._rotate_vector(other.position)
            new_pos = self.position + rotated_pos

            r = self._rotate_vector(other.rightvector)
            u = self._rotate_vector(other.upvector)
            l = self._rotate_vector(other.lookvector)

            return CFrame(new_pos, r, u, l)

        if isinstance(other, Vector3):
            return self.position + self._rotate_vector(other)

    def __add__(self, other):
        if isinstance(other, Vector3):
            return CFrame(self.position + other,
                          self.rightvector, self.upvector, self.lookvector)

    def __sub__(self, other):
        if isinstance(other, Vector3):
            return CFrame(self.position - other,
                          self.rightvector, self.upvector, self.lookvector)
        
    def inverse(self):
        r = Vector3(self.rightvector.X, self.upvector.X, self.lookvector.X)
        u = Vector3(self.rightvector.Y, self.upvector.Y, self.lookvector.Y)
        l = Vector3(self.rightvector.Z, self.upvector.Z, self.lookvector.Z)

        inv_pos = Vector3(
            -self.position.dot(r),
            -self.position.dot(u),
            -self.position.dot(l),
        )

        return CFrame(inv_pos, r, u, l)

    def to_worldspace(self, cf):
        return self * cf

    def to_objectspace(self, cf):
        return self.Inverse() * cf

    def get_components(self):
        return tuple([
            self.rightvector.X, self.upvector.X, self.lookvector.X,
            self.rightvector.Y, self.upvector.Y, self.lookvector.Y,
            self.rightvector.Z, self.upvector.Z, self.lookvector.Z,
            self.position.X, self.position.Y, self.position.Z
        ])

class Udim2():
    def __init__(self, sx=0.0, ox=0.0, sy=0.0, oy=0.0):
        self.scalex = sx
        self.offsetx = ox
        self.scaley = sy
        self.offsety = oy
    
    def __str__(self):
        return f"X Scale: {self.scalex}, X Offset: {self.offsetx}, Y Scale: {self.scaley}, Y Offset: {self.offsety}"
    
    def __eq__(self, value):
        return (
            isinstance(value, Udim2)
            and self.scalex == value.scalex
            and self.offsetx == value.offsetx
            and self.scaley == value.scaley
            and self.offsety == value.offsety
        )

    def __add__(self, value):
        return Udim2(self.scalex + value.scalex, self.offsetx + value.offsetx, self.scaley + value.scaley, self.offsety + value.offsety)

    def __sub__(self, value):
        return Udim2(self.scalex - value.scalex, self.offsetx - value.offsetx, self.scaley - value.scaley, self.offsety - value.offsety)
    
    def __mul__(self, value):
        if isinstance(value, Udim2):
            return Udim2(self.scalex * value.scalex, self.offsetx * value.offsetx, self.scaley * value.scaley, self.offsety * value.offsety)
        return Udim2(self.scalex * value, self.offsetx * value, self.scaley * value, self.offsety * value)
    
    __rmul__ = __mul__

    def __truediv__(self, value):
        if isinstance(value, Udim2):
            return Udim2(self.scalex / value.scalex, self.offsetx / value.offsetx, self.scaley / value.scaley, self.offsety / value.offsety)
        return Udim2(self.scalex / value, self.offsetx / value, self.scaley / value, self.offsety / value)
    
    def __neg__(self):
        return Udim2(-self.scalex, -self.offsetx, -self.scaley, -self.offsety)

class Quat():
    def __init__(self, x=0.0, y=0.0, z=0.0, w=0.0):
        self.x = x
        self.y = y
        self.z = z
        self.w = w

class Matrix():
    def __init__(self, data=None):
        self.data = data if data else [0.0] * 16

def get_flat_matrix_column(matrix, column, invert=False):
    stride = 3

    return [matrix[column + i * stride] * (-1 if invert else 1) for i in range(3)]
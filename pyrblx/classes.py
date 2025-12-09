from pymem.ressources import structure
from PyQt5.QtWidgets import QApplication

from datatypes import *
from subclasses import *

class TaskScheduler():
    def __init__(self, memory):
        self.memory = memory
    
    def get_address(self):
        try:
            offset = self.memory.get_offset("JobsPointer")
            return self.memory.readptr(self.memory.base + offset)
        except Exception as e:
            return 0

    def get_size(self):
        try:
            offset = self.memory.get_offset("JobsPointer")
            return self.memory.readptr(self.memory.base + offset + 0x8)
        except Exception as e:
            return 0

    def get_jobname(self, addr):
        try:
            offset = self.memory.get_offset("Job_Name")
            ptr = addr + offset

            length = self.memory.readint(ptr + 0x18)
            if length >= 16:
                ptr = self.memory.readptr(ptr)

            bytes = self.memory.process.read_bytes(ptr, min(length, 100))
            return bytes.decode('utf-8', errors='ignore').rstrip('\x00')
        except Exception as e:
            return ""

    def get_jobs(self):
        jobs = []

        try:
            base = self.get_address()
            end = self.get_size()
            i = 0

            while (base + i) < end:
                job = self.memory.readptr(base + i)

                if job and self.get_jobname(job):
                    jobs.append(job)

                i += 0x10
        except Exception as e:
            pass

        return jobs

    def get_job(self, name):
        for job in self.get_jobs():
            if name in self.get_jobname(job):
                return job
            
        return 0

    def get_renderview(self):
        job = self.get_job("RenderJob")
        offset = self.memory.get_offset("RenderJobToRenderView")

        return RenderView(self.memory, self.memory.readptr(job + offset))

    def get_visualengine(self):
        rv = self.get_renderview()
        ve = rv.get_visualengine()

        return ve

    def get_datamodel(self):
        fakedmoffset = self.memory.get_offset("FakeDataModelPointer")
        fakedmaddr = self.memory.readptr(self.memory.base + fakedmoffset)

        dmoffset = self.memory.get_offset("FakeDataModelToDataModel")

        return DataModel(self.memory, self.memory.readptr(fakedmaddr + dmoffset))
    
class Instance():
    def __init__(self, memory, address):
        self.memory = memory
        self.address = address
    
    def __bool__(self):
        return self.address > 0
    
    def __str__(self):
        return f"{self.get_name()} ({self.get_class()} object at {hex(self.address)})"
    
    def __getattr__(self, name):
        return self.find_first_child(name)
    
    @classmethod
    def new(cls, memory, address):
        if address == 0:
            return Instance(memory, address)
        return memory.get_instance(cls, address)

    def get_address(self):
        return hex(self.address)
    
    def get_class_descriptor(self):
        try:
            offset = self.memory.get_offset("ClassDescriptor")
            return self.memory.readptr(self.address + offset)
        except Exception as e:
            return 0
    
    def get_class(self):
        try:
            offset = self.memory.get_offset("ClassDescriptorToClassName")
            desc = self.get_class_descriptor()
            ptr = self.memory.readptr(desc + offset)

            if ptr:
                return self.memory.readstring2(ptr)
        except Exception as e:
            pass
        return "unknown"

    def get_name(self):
        try:
            offset = self.memory.get_offset("Name")
            ptr = self.memory.readptr(self.address + offset)

            return self.memory.readstring2(ptr)
        except Exception as e:
            return ""
    
    def set_name(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("Name")
            ptr = self.memory.readptr(self.address + offset)

            return self.memory.writestring2(ptr, value)
        except Exception:
            return False

    def get_parent(self):
        offset = self.memory.get_offset("Parent")
        addr = self.memory.readptr(self.address + offset)

        return Instance.new(self.memory, addr)
    
    def set_parent(self, parent):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("Parent")
            return self.memory.writeptr(self.address + offset, parent.address)
        except Exception:
            return False
        
    def get_fullname(self):
        parent = self.get_parent()
        name = self.get_name()

        if parent and parent.address:
            name = parent.get_fullname() + "." + name

        return name
    
    def get_children(self):
        children = []
        
        try:
            offset = self.memory.get_offset("Children")
            endoffset = self.memory.get_offset("ChildrenEnd")

            list = self.memory.readptr(self.address + offset)
            start = self.memory.readptr(list)
            end = self.memory.readptr(list + endoffset)

            i = start
            while i < end:
                addr = self.memory.readptr(i)
                if addr:
                    children.append(Instance.new(self.memory, addr))
                i += 0x10
        except Exception as e:
            pass

        return children
    
    def get_descendants(self):
        descendants = []

        for child in self.get_children():
            descendants.append(child)
            descendants += child.get_descendants()

        return descendants

    def find_first_child(self, name, recursive=False):
        children = self.get_descendants() if recursive else self.get_children()

        for child in children:
            if child.get_name() == name:
                return child
            
        return Instance.new(self.memory, 0)

    def find_first_child_of_class(self, classname, recursive=False):
        children = self.get_descendants() if recursive else self.get_children()

        for child in children:
            if child.get_class() == classname:
                return child
            
        return Instance.new(self.memory, 0)
    
    def spoofwith(self, value):
        return self.memory.writeptr(self.address + 0x8, value.address)

class RenderView(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_visualengine(self):
        try:
            offset = self.memory.get_offset("VisualEnginePointer")
            veptr = self.memory.readptr(self.memory.base + offset)

            if veptr == 0:
                veoffset = self.memory.get_offset("VisualEngine")
                veptr = self.memory.readptr(self.address + veoffset)

            return VisualEngine(self.memory, veptr)
        except Exception as e:
            return VisualEngine(self.memory, 0)

class VisualEngine(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)

    def get_matrix(self):
        try:
            offset = self.memory.get_offset("viewmatrix")
            floats = self.memory.readfloats(self.address + offset, 16)

            return Matrix(floats)
        except Exception as e:
            return Matrix()

    def get_dims(self):
        try:
            offset = self.memory.get_offset("Dimensions")
            x, y = self.memory.readfloats(self.address + offset, 2)

            return Vector2(x, y)
        except Exception as e:
            return Vector2(800, 600)
    
    def world_to_screen(self, pos, matrix=None):
        if not matrix:
            matrix = self.get_matrix()

        q = Quat(
            (pos.x * matrix.data[0]) + (pos.y * matrix.data[1]) + (pos.z * matrix.data[2]) + matrix.data[3],
            (pos.x * matrix.data[4]) + (pos.y * matrix.data[5]) + (pos.z * matrix.data[6]) + matrix.data[7],
            (pos.x * matrix.data[8]) + (pos.y * matrix.data[9]) + (pos.z * matrix.data[10]) + matrix.data[11],
            (pos.x * matrix.data[12]) + (pos.y * matrix.data[13]) + (pos.z * matrix.data[14]) + matrix.data[15],
        )
        
        if q.w < 0.1:
            return Vector2(-1, -1)
        
        ndc = Vector3()
        ndc.x = q.x / q.w
        ndc.y = q.y / q.w
        ndc.z = q.z / q.w
        
        screen = QApplication.primaryScreen().geometry()
        width = screen.width()
        height = screen.height()
        
        x = (width / 2.0) * (1.0 + ndc.x)
        y = (height / 2.0) * (1.0 - ndc.y)
        
        return Vector2(x, y)

class DataModel(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_service(self, service):
        return self.find_first_child_of_class(service)
    
    def get_creatorid(self):
        try:
            offset = self.memory.get_offset("CreatorId")
            return self.memory.readnumber(self.address + offset)
        except Exception as e:
            return 0
    
    def get_gameid(self):
        try:
            offset = self.memory.get_offset("GameId")
            return self.memory.readnumber(self.address + offset)
        except Exception as e:
            return 0
    
    def get_placeid(self):
        try:
            offset = self.memory.get_offset("PlaceId")
            return self.memory.readnumber(self.address + offset)
        except Exception as e:
            return 0
    
    def get_gameloaded(self):
        try:
            offset = self.memory.get_offset("GameLoaded")
            return self.memory.readbool(self.address + offset)
        except Exception as e:
            return False

class ScriptContext(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)

    def requirebypass(self):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("RequireBypass")

            return self.memory.writebool(self.address + offset, True)
        except Exception as e:
            return False

class Workspace(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_gravity(self):
        try:
            offset = self.memory.get_offset("Gravity")
            return self.memory.readfloat(self.address + offset)
        except Exception as e:
            return 0.0

    def set_gravity(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("Gravity")

            return self.memory.writefloat(self.address + offset, float(value))
        except Exception as e:
            return False
    
    def get_currentcamera(self):
        try:
            offset = self.memory.get_offset("Camera")
            addr = self.memory.readptr(self.address + offset)

            return Instance.new(self.memory, addr)
        except Exception as e:
            return Instance.new(self.memory, 0)

class Players(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_localplayer(self):
        try:
            offset = self.memory.get_offset("LocalPlayer")
            addr = self.memory.readptr(self.address + offset)

            return Instance.new(self.memory, addr)
        except Exception as e:
            return Instance.new(self.memory, 0)

class Player(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)

    def get_character(self):
        try:
            offset = self.memory.get_offset("ModelInstance")
            character = self.memory.readptr(self.address + offset)

            if character:
                return Instance.new(self.memory, character)
        except Exception as e:
            pass
        
        return Instance.new(self.memory, 0)
    
    def get_userid(self):
        try:
            offset = self.memory.get_offset("UserId")
            return self.memory.readnumber(self.address + offset)
        except Exception as e:
            return 0
        
    def get_team(self):
        try:
            offset = self.memory.get_offset("Team")
            return Instance.new(self.memory, self.memory.readptr(self.address + offset))
        except Exception as e:
            return Instance.new(self.memory, 0)
    
    def get_mouse(self):
        try:
            offset = self.memory.get_offset("PlayerMouse")
            return Instance.new(self.memory, self.memory.readptr(self.address + offset))
        except Exception as e:
            return Instance.new(self.memory, 0)

class Humanoid(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_health(self):
        try:
            offset = self.memory.get_offset("Health")
            one = self.memory.readptr(self.address + offset)
            if not one:
                return 0.0
            two = self.memory.readptr(one)

            conv = one ^ two if two else one
            conv32 = conv & 0xFFFFFFFF

            return self.memory.struct.unpack('<f', self.memory.struct.pack('<I', conv32))[0]
        except Exception as e:
            return 0.0
    
    def set_health(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("Health")
            addr = self.address + offset

            one = self.memory.readptr(addr)
            if not one:
                return False
            packed32 = self.memory.struct.unpack('<I', self.memory.struct.pack('<f', float(value)))[0]
            two = 0

            try:
                two = self.memory.readptr(one)
            except Exception:
                two = 0
            if two:
                conv64 = (one ^ packed32) & 0xFFFFFFFFFFFFFFFF
                data = self.memory.struct.pack('<Q', conv64)

                return self.memory.writebytes(one, data)
            else:
                new_one = ((one & 0xFFFFFFFF00000000) | packed32) & 0xFFFFFFFFFFFFFFFF
                data = self.memory.struct.pack('<Q', new_one)

                return self.memory.writebytes(addr, data)
        except Exception:
            return False

    def get_maxhealth(self):
        try:
            offset = self.memory.get_offset("Health")
            one = self.memory.readptr(self.address + offset)
            if not one:
                return 0.0
            two = self.memory.readptr(one)

            conv = one ^ two if two else one
            conv32 = conv & 0xFFFFFFFF

            return self.memory.struct.unpack('<f', self.memory.struct.pack('<I', conv32))[0]
        except Exception as e:
            return 0.0
    
    def set_maxhealth(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("MaxHealth")
            addr = self.address + offset

            one = self.memory.readptr(addr)
            if not one:
                return False
            packed = self.memory.struct.unpack('<I', self.memory.struct.pack('<f', value))[0]

            conv = one ^ packed
            target = self.memory.readptr(addr)

            if not target:
                return False
            return self.memory.writeptr(target, conv)
        except Exception:
            return False
    
    def get_walkspeed(self):
        try:
            offset = self.memory.get_offset("WalkSpeed")
            return self.memory.readfloat(self.address + offset)
        except Exception as e:
            return 0.0

    def set_walkspeed(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("WalkSpeed")
            offsetcheck = self.memory.get_offset("WalkSpeedCheck")

            self.memory.writefloat(self.address + offset, float(value))
            self.memory.writefloat(self.address + offsetcheck, float(value))

            return True
        except Exception as e:
            return False
    
    def get_jumppower(self):
        try:
            offset = self.memory.get_offset("JumpPower")
            return self.memory.readfloat(self.address + offset)
        except Exception as e:
            return 0.0

    def set_jumppower(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("JumpPower")
            self.memory.writefloat(self.address + offset, float(value))

            return True
        except Exception as e:
            return False
    
    def get_movedirection(self):
        try:
            movoffset = self.memory.get_offset("MoveDirection")
            x, y, z = self.memory.readfloats(self.address + movoffset, 3)

            return Vector3(x, y, z)
        except Exception as e:
            pass

        return Vector3()

class PlayerMouse(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_position(self):
        try:
            offset = self.memory.get_offset("MousePosition")
            x = self.memory.readint(self.address + offset)
            y = self.memory.readint(self.address + offset + 0x4)

            return Vector2(x, y)
        except Exception as e:
            pass

        return Vector2()

class Camera(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_position(self):
        try:
            posoffset = self.memory.get_offset("CameraPos")
            x, y, z = self.memory.readfloats(self.address + posoffset, 3)

            return Vector3(x, y, z)
        except Exception as e:
            pass

        return Vector3()

    def get_rotation(self):
        try:
            rotoffset = self.memory.get_offset("CameraRotation")
            x, y, z = self.memory.readfloats(self.address + rotoffset, 3)

            return Vector3(x, y, z)
        except Exception as e:
            pass

        return Vector3()
    
    def get_subject(self):
        try:
            offset = self.memory.get_offset("CameraSubject")
            addr = self.memory.readptr(self.address + offset)

            return Instance.new(self.memory, addr)
        except Exception as e:
            return Instance.new(self.memory, 0)
    
    def get_fov(self):
        try:
            offset = self.memory.get_offset("FOV")

            return (self.memory.readfloat(self.address + offset) / pi) * 180
        except Exception as e:
            return 0.0

class BasePart(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_primitive(self):
        try:
            primoffset = self.memory.get_offset("Primitive")
            return self.memory.readptr(self.address + primoffset)
        except Exception as e:
            return 0
    
    def get_position(self):
        try:
            posoffset = self.memory.get_offset("Position")

            prim = self.get_primitive()
            if prim:
                x, y, z = self.memory.readfloats(prim + posoffset, 3)

                return Vector3(x, y, z)
        except Exception as e:
            pass

        return Vector3()

    def set_position(self, vec):
        if not self.memory or not self.address:
            return False
        try:
            posoffset = self.memory.get_offset("Position")

            prim = self.get_primitive()
            if prim:
                return self.memory.writefloats(prim + posoffset, (float(vec.x), float(vec.y), float(vec.z)))
        except Exception:
            return False
        
        return False

    def get_size(self):
        try:
            sizeoffset = self.memory.get_offset("PartSize")

            prim = self.get_primitive()
            if prim:
                x, y, z = self.memory.readfloats(prim + sizeoffset, 3)

                return Vector3(x, y, z)
        except Exception as e:
            pass

        return Vector3()

    def set_size(self, vec):
        if not self.memory or not self.address:
            return False
        try:
            sizeoffset = self.memory.get_offset("PartSize")

            prim = self.get_primitive()
            if prim:
                return self.memory.writefloats(prim + sizeoffset, (float(vec.x), float(vec.y), float(vec.z)))
        except Exception:
            return False
        
        return False
    
    def get_rotation(self):
        try:
            rotoffset = self.memory.get_offset("Rotation")

            prim = self.get_primitive()
            if prim:
                x, y, z = self.memory.readfloats(prim + rotoffset, 3)

                return Vector3(x, y, z)
        except Exception as e:
            pass

        return Vector3()

    def set_rotation(self, vec):
        if not self.memory or not self.address:
            return False
        try:
            rotoffset = self.memory.get_offset("Rotation")

            prim = self.get_primitive()
            if prim:
                return self.memory.writefloats(prim + rotoffset, (float(vec.x), float(vec.y), float(vec.z)))
        except Exception:
            return False
        
        return False
    
    def get_cframe(self):
        try:
            cframeoffset = self.memory.get_offset("CFrame")

            prim = self.get_primitive()
            if prim:
                cframedata = self.memory.readfloats(prim + cframeoffset, 3 * 4)
                
                rvector = get_flat_matrix_column(cframedata, 0)
                uvector = get_flat_matrix_column(cframedata, 1)
                lvector = get_flat_matrix_column(cframedata, 2, invert=True)
                position = cframedata[9:12]

                return CFrame(
                    Vector3(*position),
                    Vector3(*rvector),
                    Vector3(*uvector),
                    Vector3(*lvector)
                )

        except Exception:
            return 
        
        return CFrame()
    
    def set_cframe(self, cframe):
        if not self.memory or not self.address:
            return False
        try:
            cframeoffset = self.memory.get_offset("CFrame")

            prim = self.get_primitive()
            if prim:
                r = cframe.rightvector
                u = cframe.upvector
                l = cframe.lookvector
                p = cframe.position

                data = [
                    r.x, u.x, -l.x,
                    r.y, u.y, -l.y,
                    r.z, u.z, -l.z,
                    p.x, p.y, p.z
                ]

                return self.memory.writefloats(prim + cframeoffset, data)
        except Exception:
            return False
        
        return False
    
    def get_velocity(self):
        try:
            veloffset = self.memory.get_offset("Velocity")

            prim = self.get_primitive()
            if prim:
                vx, vy, vz = self.memory.readfloats(prim + veloffset, 3)

                return Vector3(vx, vy, vz)
        except Exception as e:
            pass

        return Vector3()
    
    def set_velocity(self, vec):
        if not self.memory or not self.address:
            return False
        try:
            veloffset = self.memory.get_offset("Velocity")

            prim = self.get_primitive()
            if prim:
                return self.memory.writefloats(prim + veloffset, (float(vec.x), float(vec.y), float(vec.z)))
        except Exception:
            return False
        
        return False
    
    def get_anchored(self):
        try:
            offset = self.memory.get_offset("Anchored")
            mask = self.memory.get_offset("AnchoredMask")

            return self.memory.readboolmask(self.get_primitive() + offset, mask)
        except Exception as e:
            return False
    
    def set_anchored(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("Anchored")
            mask = self.memory.get_offset("AnchoredMask")

            return self.memory.writeboolmask(self.get_primitive() + offset, mask, value)
        except Exception as e:
            return False
    
    def get_cancollide(self):
        try:
            offset = self.memory.get_offset("CanCollide")
            mask = self.memory.get_offset("CanCollideMask")

            return self.memory.readboolmask(self.get_primitive() + offset, mask)
        except Exception as e:
            return False
    
    def set_cancollide(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("CanCollide")
            mask = self.memory.get_offset("CanCollideMask")

            return self.memory.writeboolmask(self.get_primitive() + offset, mask, value)
        except Exception as e:
            return False

    def get_cantouch(self):
        try:
            offset = self.memory.get_offset("CanTouch")
            mask = self.memory.get_offset("CanTouchMask")

            return self.memory.readboolmask(self.get_primitive() + offset, mask)
        except Exception as e:
            return False
    
    def set_cantouch(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("CanTouch")
            mask = self.memory.get_offset("CanTouchMask")

            return self.memory.writeboolmask(self.get_primitive() + offset, mask, value)
        except Exception as e:
            return False
    
    def get_transparency(self):
        try:
            offset = self.memory.get_offset("Transparency")

            return self.memory.readfloat(self.address + offset)
        except Exception as e:
            return 0.0
        
    def set_transparency(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("Transparency")

            return self.memory.writefloat(self.address + offset, value)
        except Exception as e:
            return False

    def get_bounds(self):
        minx = float('inf')
        maxx = float('-inf')
        miny = float('inf')
        maxy = float('-inf')
        minz = float('inf')
        maxz = float('-inf')

        for child in self.get_descendants():
            if isinstance(child, BasePart):
                pos = child.get_position()
                size = child.get_size()

                partminx = pos.x - size.x / 2
                partmaxx = pos.x + size.x / 2
                partminy = pos.y - size.y / 2
                partmaxy = pos.y + size.y / 2
                partminz = pos.z - size.z / 2
                partmaxz = pos.z + size.z / 2

                minx = min(minx, partminx)
                maxx = max(maxx, partmaxx)
                miny = min(miny, partminy)
                maxy = max(maxy, partmaxy)
                minz = min(minz, partminz)
                maxz = max(maxz, partmaxz)

        return minx, maxx, miny, maxy, minz, maxz

class MeshPart(BasePart):
    def __init__(self, memory, address):
        super().__init__(memory, address)

class Model(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)

class IntValue(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_value(self):
        try:
            offset = self.memory.get_offset("Value")
            return self.memory.readint(self.address + offset)
        except Exception as e:
            return 0

    def set_value(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("ValueGetSetToValue")
            return self.memory.writeint(self.address + offset, value)
        except Exception as e:
            return False

class NumberValue(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_value(self):
        try:
            offset = self.memory.get_offset("Value")
            return self.memory.readdouble(self.address + offset)
        except Exception as e:
            return 0.0

    def set_value(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("ValueGetSetToValue")
            return self.memory.writedouble(self.address + offset, value)
        except Exception as e:
            return False

class BoolValue(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_value(self):
        try:
            offset = self.memory.get_offset("Value")
            return self.memory.readbool(self.address + offset)
        except Exception as e:
            return False

    def set_value(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("ValueGetSetToValue")
            return self.memory.writebool(self.address + offset, value)
        except Exception as e:
            return False

class StringValue(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_value(self):
        try:
            offset = self.memory.get_offset("Value")
            return self.memory.readstring2(self.address + offset)
        except Exception as e:
            return ""

    def set_value(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("ValueGetSetToValue")
            return self.memory.writestring2(self.address + offset, value)
        except Exception as e:
            return False

class ObjectValue(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_value(self):
        try:
            offset = self.memory.get_offset("Value")
            return Instance.new(self.memory, self.memory.readptr(self.address + offset))
        except Exception as e:
            return Instance.new(self.memory, 0)

    def set_value(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("ValueGetSetToValue")
            return self.memory.writeptr(self.address + offset, value.address)
        except Exception as e:
            return False

class BaseScript(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)

class Script(BaseScript):
    def __init__(self, memory, address):
        super().__init__(memory, address)

class LocalScript(BaseScript):
    def __init__(self, memory, address):
        super().__init__(memory, address)

        self.worker = ScriptBytecode()
    
    def get_data(self):
        try:
            offset = self.memory.get_offset("LocalScriptByteCode")
            boffset = self.memory.get_offset("LocalScriptBytecodePointer")

            addr = self.memory.readptr(self.address + offset)

            daddr = self.memory.readptr(addr + boffset)
            dsize = self.memory.readint(addr + boffset + 0x10)

            return self.memory.readbytes(daddr, dsize)
        except Exception as e:
            return b""
    
    def set_data(self, bytecode):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("LocalScriptByteCode")
            boffset = self.memory.get_offset("LocalScriptBytecodePointer")

            success = True
            dsize = len(bytecode)

            addr = self.memory.readptr(self.address + offset)

            daddr = self.memory.readptr(addr + boffset)
            self.memory.free(daddr)
            daddr = self.memory.allocate(dsize)
            self.memory.writebytes(daddr, bytecode)

            success = success and self.memory.writeptr(addr + boffset, daddr)
            success = success and self.memory.writeint(addr + boffset + 0x10, dsize)
            
            return success
        except Exception as e:
            return False

    def get_bytecode(self):
        data = self.get_data()
        if not data:
            return b""
        
        return self.worker.decode(data)

    def set_bytecode(self, bytecode):
        data = self.worker.encode(bytecode)
        if not data:
            return False

        return self.set_data(data)

class ModuleScript(BaseScript):
    def __init__(self, memory, address):
        super().__init__(memory, address)

        self.worker = ScriptBytecode()
    
    def get_data(self):
        try:
            offset = self.memory.get_offset("ModuleScriptByteCode")
            boffset = self.memory.get_offset("ModuleScriptBytecodePointer")

            addr = self.memory.readptr(self.address + offset)

            daddr = self.memory.readptr(addr + boffset)
            dsize = self.memory.readint(addr + boffset + 0x10)

            return self.memory.readbytes(daddr, dsize)
        except Exception as e:
            return b""
    
    def set_data(self, bytecode):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("ModuleScriptByteCode")
            boffset = self.memory.get_offset("ModuleScriptBytecodePointer")

            success = True
            dsize = len(bytecode)

            addr = self.memory.readptr(self.address + offset)

            daddr = self.memory.readptr(addr + boffset)
            self.memory.free(daddr)
            daddr = self.memory.allocate(dsize)
            self.memory.writebytes(daddr, bytecode)

            success = success and self.memory.writeptr(addr + boffset, daddr)
            success = success and self.memory.writeint(addr + boffset + 0x10, dsize)
            
            return success
        except Exception as e:
            return False

    def get_bytecode(self):
        data = self.get_data()
        if not data:
            return b""
        
        return self.worker.decode(data)

    def set_bytecode(self, bytecode):
        data = self.worker.encode(bytecode)
        if not data:
            return False

        return self.set_data(data)

    def unlockmodule(self):
        mfoffset = self.memory.get_offset("ModuleFlags")
        icpoffset = self.memory.get_offset("IsCoreScript")

        success = True

        success = success and self.memory.writeptr(self.address + mfoffset, 0x100000000)
        success = success and self.memory.writeptr(self.address + icpoffset, 0x1)

        return success

class Sound(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_soundid(self):
        try:
            offset = self.memory.get_offset("SoundId")
            return self.memory.readnumber(self.address + offset)
        except Exception as e:
            return 0

    def set_soundid(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("SoundId")
            return self.memory.writenumber(self.address + offset, value)
        except Exception as e:
            return False

class Animation(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_animationid(self):
        try:
            offset = self.memory.get_offset("AnimationId")
            return self.memory.readnumber(self.address + offset)
        except Exception as e:
            return 0
    
    def set_animationid(self, value):
        if not self.memory or not self.address:
            return False
        try:
            offset = self.memory.get_offset("AnimationId")
            return self.memory.writenumber(self.address + offset, value)
        except Exception as e:
            return False

class Frame(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_visible(self):
        try:
            voffset = self.memory.get_offset("FrameVisible")
            return self.memory.readbool(self.address + voffset)
        except Exception as e:
            return False
    
    def get_position(self):
        try:
            sxoffset = self.memory.get_offset("FramePositionX")
            oxoffset = self.memory.get_offset("FramePositionOffsetX")
            syoffset = self.memory.get_offset("FramePositionY")
            oyoffset = self.memory.get_offset("FramePositionOffsetY")

            sx = self.memory.readfloat(self.address + sxoffset)
            ox = self.memory.readfloat(self.address + oxoffset)
            sy = self.memory.readfloat(self.address + syoffset)
            oy = self.memory.readfloat(self.address + oyoffset)

            return Udim2(sx, ox, sy, oy)
        except Exception as e:
            return Udim2()
    
    def get_size(self):
        try:
            sxoffset = self.memory.get_offset("FrameSizeX")
            oxoffset = self.memory.get_offset("FrameSizeOffsetX")
            syoffset = self.memory.get_offset("FrameSizeY")
            oyoffset = self.memory.get_offset("FrameSizeOffsetY")

            sx = self.memory.readfloat(self.address + sxoffset)
            ox = self.memory.readfloat(self.address + oxoffset)
            sy = self.memory.readfloat(self.address + syoffset)
            oy = self.memory.readfloat(self.address + oyoffset)

            return Udim2(sx, ox, sy, oy)
        except Exception as e:
            return Udim2()
    
    def get_rotation(self):
        try:
            roffset = self.memory.get_offset("FrameRotation")
            return self.memory.readfloat(self.address + roffset)
        except Exception as e:
            return 0.0

class TextLabel(Instance):
    def __init__(self, memory, address):
        super().__init__(memory, address)
    
    def get_visible(self):
        try:
            voffset = self.memory.get_offset("TextLabelVisible")
            return self.memory.readbool(self.address + voffset)
        except Exception as e:
            return False
    
    def get_text(self):
        try:
            offset = self.memory.get_offset("TextLabelText")
            return self.memory.readstring2(self.address + offset)
        except Exception as e:
            return ""
    
CLASSTYPES = {
    "ScriptContext": ScriptContext,
    "Workspace": Workspace,
    "Players": Players,
    "Player": Player,
    "Humanoid": Humanoid,
    "PlayerMouse": PlayerMouse,
    "Camera": Camera,
    "Part": BasePart,
    "MeshPart": MeshPart,
    "Model": Model,
    "IntValue": IntValue,
    "NumberValue": NumberValue,
    "BoolValue": BoolValue,
    "StringValue": StringValue,
    "ObjectValue": ObjectValue,
    "Script": Script,
    "LocalScript": LocalScript,
    "ModuleScript": ModuleScript,
    "Sound": Sound,
    "Animation": Animation,
    "Frame": Frame,
    "TextLabel": TextLabel
}
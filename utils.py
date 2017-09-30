import bpy
import os
import time
from mathutils import Vector

# path utils

p = os.path
j = p.join

def project_root():
	return p.abspath(j(bpy.path.abspath('//'), p.pardir))
	
def assets_root():
	return p.join(project_root(), "android", "assets", "bdx")
	
def src_root(project="core", target_file="BdxApp.java"):
	for root, dirs, files in os.walk(j(project_root(), project, "src")):
		if target_file in files:
			return root
			
def android_launcher(target_file="AndroidLauncher.java"):
	return j(src_root("android", target_file), target_file)
	
def android_manifest(target_file="AndroidManifest.xml"):
	return j(project_root(), "android", target_file)
	
# string utils

def id(n, prefix=".", length=4):
	s = prefix
	d = str(n)
	for i in range(length - len(d)):
		s += "0"
	s += d
	return s
	
# text utils

def lines(file_path):
	with open(file_path, 'r') as f:
		return f.readlines()
	return
	
def enum_line_containing(lines, pattern):
	for index, line in enumerate(lines):
		if pattern in line:
			return [index, line]
	return
	
def replace_line(index, lines, new_line):
	lines[index] = new_line + "\n";
	
def insert_line(index, lines, new_line):
	lines.insert(index, new_line + "\n")
	lines = "".join(lines)
	
def write_lines(lines, file_path):
	with open(file_path, 'w') as f:
		f.writelines(lines)
		
# java utils

def java_texts():
	return [t for t in bpy.data.texts.values() if t.name.endswith(".java")]
	
def java_pack_name():
	with open(j(src_root(), "BdxApp.java"), 'r') as f:
		_, package = f.readline().split()
	return package[:-1]
	
def java_pack_error():
	pack_name = java_pack_name();
	for t in java_texts():
		if t.lines[0].body != "package " + pack_name + ";":
			return True
	return False
	
def java_pack_sync():
	pack_name = java_pack_name();
	for t in java_texts():
		t.lines[0].body = "package " + pack_name + ";"
		
# profiling utils

class Profiler:
	
	def __init__(self):
		self.start = time.clock()
		
	def timed(self, *args):
		s = ""
		for arg in args:
			s += str(arg)
		for i in range(60 - len(s)):
			s += "."
		s += str(round(time.clock() - self.start, 1)) + " s"
		return s
		
# object utils

def copy(sc, ob, link=True, suffix="", apply_modifiers=False, modifier_settings="RENDER"):
	me_copy = ob.to_mesh(sc, apply_modifiers, modifier_settings)
	me_copy.name = ob.data.name + suffix
	ob_copy = bpy.data.objects.new(ob.name + suffix, me_copy)
	ob_copy.matrix_world = ob.matrix_world
	if link:
		sc.objects.link(ob_copy)
	return ob_copy
	
def dimensions_transformed(*objects):
	bb_crns = []
	for ob in objects:
		bb_crns += [ob.matrix_world * Vector(corner) for corner in ob.bound_box]
	n = len(bb_crns)
	dim_x = max(bb_crns[i][0] for i in range(n)) - min(bb_crns[i][0] for i in range(n))
	dim_y = max(bb_crns[i][1] for i in range(n)) - min(bb_crns[i][1] for i in range(n))
	dim_z = max(bb_crns[i][2] for i in range(n)) - min(bb_crns[i][2] for i in range(n))
	return Vector((dim_x, dim_y, dim_z))
	
# math utils

def point_inside_rectangle(pnt, rect):
	cen, dim = rect
	crn = Vector((cen.x - dim.x * 0.5, cen.y - dim.y * 0.5))
	return (crn.x <= pnt.x <= crn.x + dim.x and crn.y <= pnt.y <= crn.y + dim.y)
	

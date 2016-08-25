import os
import bpy


# path utils

p = os.path
j = p.join

def project_root():
	return p.abspath(j(bpy.path.abspath('//'), p.pardir))

def src_root(project="core", target_file="BdxApp.java"):
	for root, dirs, files in os.walk(j(project_root(), project, "src")):
		if target_file in files:
			return root
			
def android_launcher(target_file="AndroidLauncher.java"):
	return j(src_root("android", target_file), target_file)

def android_manifest(target_file="AndroidManifest.xml"):
	return j(project_root(), "android", target_file)
	

# text utils

def lines(file_path):
	with open(file_path, 'r') as f:
		return f.readlines()
	return
	
def enum_line_containing(lines, pattern):
	for index, line in enumerate(lines):
		if pattern in line:
			return index, line
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

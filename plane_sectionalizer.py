import bpy
import bmesh
import math
import os
import json
import numpy
from mathutils import Vector
from collections import OrderedDict
from . import utils as ut

ERROR_NO_ACTIVE_OBJECT = "No active object"
ERROR_WRONG_OBJECT = "Active object has no mesh data"
ERROR_WRONG_LAYER = "Active object not in active layer"
ERROR_BDX_NOT_INSTALLED = "BDX add-on not installed!"
ERROR_BDX_PROJECT_MISSING = "BDX project missing!"
WARNING_BDX_SAVE = "Saving to blend folder."

TEMP_SUFFIX = "_TEMP"
PART_SUFFIX = "_PART"
SECT_SUFFIX = "_SECT"

class PlaneSectionalizer(bpy.types.Operator):
	
	bl_description = "Sectionalizes a plane with options for your BDX project."
	bl_idname = "bdx.plane_sectionalizer"
	bl_label = "BDX-Tools: Plane Sectionalizer"
	bl_options = {"REGISTER", "UNDO"}
	
	error = ""
	
	plane_dimensions = Vector().to_2d()
	sect_number = Vector().to_2d()
	sect_size = Vector().to_2d()
	
	def invoke(self, context, event):
		plane = context.scene.objects.active
		if plane:
			if plane.data:
				if plane not in context.editable_objects:
					self.error = ERROR_WRONG_LAYER
				else:
					dim = ut.dimensions_transformed(plane)
					self.plane_dimensions.x = dim.x
					self.plane_dimensions.y = dim.y
			else:
				self.error = ERROR_WRONG_OBJECT
		else:
			self.error = ERROR_NO_ACTIVE_OBJECT
			
		system_dpi = bpy.context.user_preferences.system.dpi
		
		return context.window_manager.invoke_props_dialog(self, width=system_dpi*5)
		
	def draw(self, context):
		layout = self.layout
		box = layout.box
		row = box().row
		
		if self.error:
			row().label(self.error, icon="CANCEL")
			return
			
		row().prop(context.scene.bdx_tools, "plane_sect_number_or_size")
		
		col = row().column
		col_number = col()
		col_number.prop(context.scene.bdx_tools, "plane_sect_number")
		col_size = col()
		col_size.prop(context.scene.bdx_tools, "plane_sect_size")
		col_size.prop(context.scene.bdx_tools, "plane_sect_number_mode")
		
		if context.scene.bdx_tools.plane_sect_number_or_size == "generate_by_number":
			self.sect_number.x = context.scene.bdx_tools.plane_sect_number[0]
			self.sect_number.y = context.scene.bdx_tools.plane_sect_number[1]
			self.sect_size.x = self.plane_dimensions.x / self.sect_number.x
			self.sect_size.y = self.plane_dimensions.y / self.sect_number.y
			col_size.active = False
		else:
			self.sect_size.x = context.scene.bdx_tools.plane_sect_size[0]
			self.sect_size.y = context.scene.bdx_tools.plane_sect_size[1]
			n_x = math.ceil(self.plane_dimensions.x / self.sect_size.x)
			n_y = math.ceil(self.plane_dimensions.y / self.sect_size.y)
			number_mode = context.scene.bdx_tools.plane_sect_number_mode
			if number_mode == "use_automatic_numbering":
				self.sect_number.x = n_x
				self.sect_number.y = n_y
			else:
				i = 0 if number_mode == "use_even_numbers" else 1
				self.sect_number.x = n_x + 1 - i if n_x % 2 else n_x + i
				self.sect_number.y = n_y + 1 - i if n_y % 2 else n_y + i
			col_number.active = False
			
		col = row().column
		col().prop(context.scene.bdx_tools, "plane_sect_apply_modifiers")
		col_settings = col()
		col_settings.prop(context.scene.bdx_tools, "plane_sect_modifiers_settings")
		if not context.scene.bdx_tools.plane_sect_apply_modifiers:
			col_settings.active = False
			
		col = row().column
		col().prop(context.scene.bdx_tools, "plane_sect_decimate")
		col_decimate = col()
		col_decimate.prop(context.scene.bdx_tools, "plane_sect_decimate_dissolve_angle_limit")
		col_decimate.prop(context.scene.bdx_tools, "plane_sect_decimate_collapse_ratio")
		if not context.scene.bdx_tools.plane_sect_decimate:
			col_decimate.active = False
			
		row().prop(context.scene.bdx_tools, "plane_sect_gen_options")
		
		col = row().column
		col_approximate = col()
		col_approximate.prop(context.scene.bdx_tools, "plane_sect_approximate")
		col_approx_ndigits = col()
		col_approx_ndigits.prop(context.scene.bdx_tools, "plane_sect_approx_ndigits")
		
		if context.scene.bdx_tools.plane_sect_gen_options == "generate_sections":
			col_approximate.active = False
			col_approx_ndigits.active = False
		else:
			if not context.scene.bdx_tools.plane_sect_approximate:
				col_approx_ndigits.active = False
			if not hasattr(context.scene, "bdx"):
				row().label(ERROR_BDX_NOT_INSTALLED + " " + WARNING_BDX_SAVE, icon="ERROR")
			elif not ut.src_root():
				row().label(ERROR_BDX_PROJECT_MISSING + " " + WARNING_BDX_SAVE, icon="ERROR")
				
	def check(self, context):
		return True
		
	def execute(self, context):
		
		def mat_tris(mesh):
			m_ps = {}
			idx_tri = 0
			for p in mesh.polygons:
				mat = mesh.materials[p.material_index] if mesh.materials else None
				mat_name = mat.name if mat else "__BDX_DEFAULT"
				if not mat_name in m_ps:
					m_ps[mat_name] = []
					
				m_ps[mat_name].append(idx_tri)
				idx_tri += 1
				
				if len(p.loop_indices) > 3:
					m_ps[mat_name].append(idx_tri)
					idx_tri += 1
					
			return m_ps
			
		def vertices(mesh):
			
			class EmptyUV:
				uv = (0.0, 0.0)
				def __getitem__(self, index):
					return self
			
			def flip_uv(uv):
				uv[1] = 1 - uv[1]
				
			def triform(loop_indices):
				indices = list(loop_indices)
				if len(indices) < 4:
					return indices
				return [indices[i] for i in (0, 1, 2, 2, 3, 0)]
				
			clnors = [0.0] * 3 * len(mesh.loops)
			mesh.loops.foreach_get("normal", clnors)
			uv_act = mesh.uv_layers.active
			uv_layer = uv_act.data if uv_act is not None else EmptyUV()
			loop_vert = {l.index: l.vertex_index for l in mesh.loops}
			verts = []
			for poly in mesh.polygons:
				for li in triform(poly.loop_indices):
					vert = mesh.vertices[loop_vert[li]]
					vert_co = list(vert.co)
					vert_normal = [clnors[li*3], clnors[li*3+1], clnors[li*3+2]]
					vert_uv = list(uv_layer[li].uv)
					flip_uv(vert_uv)
					verts += vert_co + vert_normal + vert_uv
					
			return verts
			
		if self.error:
			return {"CANCELLED"}
			
		print("\nSectionalizing Plane\n--------------------\n")
		
		ob_base = context.scene.objects.active
		prof = ut.Profiler()
		
		print(prof.timed("Creating temp data"))
		
		me_temp = ob_base.to_mesh(context.scene, context.scene.bdx_tools.plane_sect_apply_modifiers, context.scene.bdx_tools.plane_sect_modifiers_settings.upper())
		me_temp.name = me_temp.name + TEMP_SUFFIX
		ob_temp = bpy.data.objects.new(ob_base.name + TEMP_SUFFIX, me_temp)
		context.scene.objects.link(ob_temp)
		ob_temp.matrix_world = ob_base.matrix_world
		context.scene.objects.active = ob_temp
		ob_base.select = False
		ob_temp.select = True
		ob_base.hide = True
		
		bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
		bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")
		off = ob_temp.location.copy()
		off.x = int(off.x / self.sect_size.x) * self.sect_size.x
		off.y = int(off.y / self.sect_size.y) * self.sect_size.y
		off.z = 0
		loc = ob_temp.location = ob_temp.location - off
		
		bpy.ops.object.mode_set(mode="OBJECT")
		
		if context.scene.bdx_tools.plane_sect_decimate:
			
			print(prof.timed("Decimating - collapse"))
			
			dc = ob_temp.modifiers.new(name="Decimate Collapse", type="DECIMATE")
			dc.decimate_type = "COLLAPSE"
			dc.ratio = context.scene.bdx_tools.plane_sect_decimate_collapse_ratio
			dc.use_collapse_triangulate = True
			bpy.ops.object.modifier_apply(modifier=dc.name)
			
			print(prof.timed("Decimating - dissolve"))
			
			dd = ob_temp.modifiers.new(name="Decimate Dissolve", type="DECIMATE")
			dd.decimate_type = "DISSOLVE"
			dd.angle_limit = context.scene.bdx_tools.plane_sect_decimate_dissolve_angle_limit
			dd.delimit = {"NORMAL", "MATERIAL", "SEAM", "SHARP", "UV"}
			bpy.ops.object.modifier_apply(modifier=dd.name)
			
			print(prof.timed("Beautifying"))
			
			bpy.ops.object.editmode_toggle()
			bpy.ops.mesh.select_mode(type="FACE")
			bpy.ops.mesh.select_all(action="SELECT")
			bpy.ops.mesh.quads_convert_to_tris()
			bpy.ops.mesh.beautify_fill()
			bpy.ops.object.editmode_toggle()
			
		print(prof.timed("Separating loose parts"))
		
		me_part = ob_temp.to_mesh(context.scene, False, context.scene.bdx_tools.plane_sect_modifiers_settings.upper())
		me_part.name = ob_base.data.name + TEMP_SUFFIX + ".000"
		ob_part = bpy.data.objects.new(ob_base.name + TEMP_SUFFIX + ".000", me_part)
		context.scene.objects.link(ob_part)
		ob_part.matrix_world = ob_temp.matrix_world
		context.scene.objects.active = ob_part
		bpy.ops.object.select_all(action="DESELECT")
		ob_part.select = True
		
		bpy.ops.mesh.separate(type="LOOSE")
		parts = {o : [] for o in context.scene.objects if o.select}
		bpy.ops.object.select_all(action="DESELECT")
		
		print(prof.timed("Multisecting"))
		
		dir_x = numpy.sign(int(loc.x))
		dir_y = numpy.sign(int(loc.y))
		start_x = 0 if dir_x < 0 else 1
		start_y = 0 if dir_y < 0 else 1
		end_x = int(self.sect_number.x) + abs(dir_x) + 1
		end_y = int(self.sect_number.y) + abs(dir_y) + 1
		
		for part in parts.keys():
			me_sect = part.to_mesh(context.scene, False, context.scene.bdx_tools.plane_sect_modifiers_settings.upper())
			me_sect.name = ob_base.data.name + PART_SUFFIX + ".000"
			ob_sect = bpy.data.objects.new(ob_base.name + PART_SUFFIX + ".000", me_sect)
			context.scene.objects.link(ob_sect)
			ob_sect.matrix_world = part.matrix_world
			context.scene.objects.active = ob_sect
			parts[part].append(ob_sect)
			
			bpy.ops.object.editmode_toggle()
			
			bm = bmesh.from_edit_mesh(ob_sect.data)
			
			for i in range(start_x, end_x):
				try:
					l = bm.verts[:] + bm.edges[:] + bm.faces[:]
					co = ((i - 0.5 * self.sect_number.x) * self.sect_size.x - loc.x, 0, 0)
					no = (1, 0, 0)
					dict = bmesh.ops.bisect_plane(bm, geom=l, plane_co=co, plane_no=no)
					bmesh.ops.split_edges(bm, edges=[e for e in dict["geom_cut"] if isinstance(e, bmesh.types.BMEdge)])
				except RuntimeError:
					continue
					
			for i in range(start_y, end_y):
				try:
					l = bm.verts[:] + bm.edges[:] + bm.faces[:]
					co = (0, (i - 0.5 * self.sect_number.y) * self.sect_size.y - loc.y, 0)
					no = (0, 1, 0)
					dict = bmesh.ops.bisect_plane(bm, geom=l, plane_co=co, plane_no=no)
					bmesh.ops.split_edges(bm, edges=[e for e in dict["geom_cut"] if isinstance(e, bmesh.types.BMEdge)])
				except RuntimeError:
					continue
					
			bmesh.update_edit_mesh(ob_sect.data)
			
			bpy.ops.object.editmode_toggle()
			
		bm.free()
		del bm
		
		print(prof.timed("Separating sections"))
		
		for part, objects in parts.items():
			ob = objects[0]
			context.scene.objects.active = ob
			ob.select = True
			bpy.ops.mesh.separate(type="LOOSE")
			objects[:] = [o for o in context.scene.objects if o.select]
			bpy.ops.object.select_all(action="DESELECT")
			
		print(prof.timed("Transferring normals"))
		
		n = 1
		n_total = 0
		for objects in parts.values():
			n_total += len(objects)
			
		for part, objects in parts.items():
			for i, ob in enumerate(objects):
				
				print(prof.timed("~ processing part ", n , " of ", n_total, "."))
				
				n += 1
				
				context.scene.objects.active = ob
				bpy.ops.object.editmode_toggle()
				bpy.ops.mesh.select_all()
				bpy.ops.mesh.remove_doubles()
				bpy.ops.mesh.quads_convert_to_tris()
				bpy.ops.object.editmode_toggle()
				
				ob.data.use_auto_smooth = True
				bpy.ops.mesh.customdata_custom_splitnormals_add()
				ob.data.normals_split_custom_set_from_vertices([v.normal for v in ob.data.vertices])
				
				cn = ob.modifiers.new(name="Copy Custom Normals", type="DATA_TRANSFER")
				cn.object = part
				cn.use_loop_data = True
				cn.data_types_loops = {"CUSTOM_NORMAL"}
				cn.mix_factor = 1
				bpy.ops.object.modifier_apply(modifier=cn.name)
				
		print(prof.timed("Finalizing sections"))
		
		sections = []
		
		sect_offset = self.sect_size * 0.5
		sect_locations = []
		for j in range(start_y, end_y):
			y = (j - 0.5 * self.sect_number.y) * self.sect_size.y - sect_offset.y
			for i in range(start_x, end_x):
				x = (i - 0.5 * self.sect_number.x) * self.sect_size.x - sect_offset.x
				sect_locations.append(Vector((x, y, 0)))
				
		cursor_location = context.scene.cursor_location.copy()
		
		id_length = len(str(len(sect_locations)))
		sect_parts = {ut.id(i, "", id_length) : [] for i in range(len(sect_locations))}
		for part, objects in parts.items():
			for ob in objects:
				context.scene.objects.active = ob
				ob.select = True
				
				bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")
				for i, v in enumerate(sect_locations):
					if abs(v.y - ob.location.y) <= sect_offset.y:
						if abs(v.x - ob.location.x) <= sect_offset.x:
							sect_parts[ut.id(i, "", id_length)].append(ob)
							context.scene.cursor_location = v
							bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
							break
				ob.select = False
			
		i = 0
		id_length = max(len(str(len(sect_parts))), 3)
		for parts in sect_parts.values():
			num_parts = len(parts)
			if num_parts:
				ob = context.scene.objects.active = parts[0]
				if num_parts > 1:
					for p in parts:
						p.select = True
					bpy.ops.object.join()
					ob.select = False
				me = ob.data
				if not me or not me.polygons:
					bpy.data.objects.remove(ob, do_unlink=True)
					bpy.data.meshes.remove(me, do_unlink=True)
				else:
					id = ut.id(i, ".", id_length)
					ob.name = ob.name.split(PART_SUFFIX)[0] + SECT_SUFFIX + id
					sections.append(ob)
					i += 1
					
		context.scene.cursor_location = cursor_location
		
		print(prof.timed("Calculating custom normals"))
		
		for sect in sections:
			context.scene.objects.active = sect
			sect.select = True
			sect.data.calc_normals_split()
			
		if off.length:
			
			print(prof.timed("Repositioning sections"))
			
			for sect in sections:
				sect.location += off
				
		print(prof.timed("Removing temp data"))
		
		for ob in context.scene.objects:
			if ob_temp.name in ob.name:
				me = ob.data
				bpy.data.objects.remove(ob, do_unlink=True)
				bpy.data.meshes.remove(me, do_unlink=True)
				
		if not context.scene.bdx_tools.plane_sect_gen_options == "generate_sections":
			
			print(prof.timed("Extracting BDX data"))
			
			num_vertices_max = 0
			
			tfs = 3 * 8
			data = {}
			for sect in sections:
				section = {}
				mesh = sect.data
				m_tris = mat_tris(mesh)
				verts = vertices(mesh)
				m_verts = OrderedDict()
				materials = []
				for m in mesh.materials:
					if m is not None:
						materials.append(m.name)
				if len(materials) == 0:
					materials.append("__BDX_DEFAULT")
				
				approximate = context.scene.bdx_tools.plane_sect_approximate
				approx_ndigits = context.scene.bdx_tools.plane_sect_approx_ndigits
				
				for mat in materials:
					if mat in m_tris.keys():
						m, tris = mat, m_tris[mat]
						l = numpy.concatenate([verts[i * tfs : i * tfs + tfs] for i in tris]).tolist()
						if approximate:
							l = [round(f, approx_ndigits) for f in l]
						m_verts[m] = l
						num_vertices = len(l) // 8
						num_vertices_max = max(num_vertices, num_vertices_max)
						print(prof.timed("\"" + m + "\" of " + sect.name, " has ", num_vertices, " vertices."))
						
				section["models"] = m_verts
				section["position"] = list(sect.location)
				data[sect.name] = section
				
			if (num_vertices_max > 4095):
				print("WARNING: Meshes with more than 4095 vertices (1365 triangles) per material are not supported in BDX.\nAt least one section has", num_vertices_max, "vertices, or", num_vertices_max // 3, "triangles. Exporting json file aborted.")
				
			else:
				print(prof.timed("Exporting json file"))
				
				root = ut.assets_root() if ut.project_root() else bpy.path.abspath("//")
				file_path = os.path.join(root, ob_base.name + ".sctx")
				with open(file_path, 'w') as f:
					json.dump(data, f)
					
		ob_base.select = True	
		context.scene.objects.active = ob_base
		
		if context.scene.bdx_tools.plane_sect_gen_options == "save_json_file":
			
			print(prof.timed("Removing sections"))
			
			for sect in sections:
				me = sect.data
				bpy.data.objects.remove(sect, do_unlink=True)
				bpy.data.meshes.remove(me, do_unlink=True)
				
			ob_base.hide = False
			
		print(prof.timed("Finished generating ", len(sections), " (", round(self.sect_size.x, 1), " X ", round(self.sect_size.y, 1), ") sections in"))
		print("\n")
		
		return {"FINISHED"}
		
def register():
	bpy.utils.register_class(PlaneSectionalizer)
	
def unregister():
	bpy.utils.unregister_class(PlaneSectionalizer)
	
if __name__ == "__main__":
	register()

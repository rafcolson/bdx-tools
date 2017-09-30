import bpy
import bmesh
import math
import os
import json
import numpy
from mathutils import Vector
from collections import OrderedDict
from . import utils as ut

ERROR_SELECTED_NO_MESH_DATA = "Selected object(s) not containing mesh data"
ERROR_SELECTED_INACTIVE_LAYER = "Selected object(s) not in active layer"
ERROR_ACTIVE_NO_MESH_DATA = "Active object not containing mesh data"
ERROR_ACTIVE_INACTIVE_LAYER = "Active object not in active layer"
ERROR_NO_ACTIVE_OR_SELECTED = "No active or selected object"

WARN_BDX_NOT_INSTALLED = "BDX add-on not installed!"
WARN_BDX_PROJECT_MISSING = "BDX project missing!"
WARN_BDX_SAVE_DIR = "Saving to blend folder."

TEMP_SUFFIX = "__TEMP"
PART_SUFFIX = "__PART"
SECT_SUFFIX = "_SECT"

class PlaneSectionalizer(bpy.types.Operator):
	
	bl_description = "Sectionalizes a plane with options for your BDX project."
	bl_idname = "bdx.plane_sectionalizer"
	bl_label = "BDX-Tools: Plane Sectionalizer"
	bl_options = {"REGISTER", "UNDO"}
	
	error = ""
	
	dimensions = Vector().to_2d()
	sect_numb = Vector().to_2d()
	sect_size = Vector().to_2d()
	originals = []
	
	def invoke(self, context, event):
		objects = []
		for ob in context.selected_editable_objects:
			if ob.data:
				objects.append(ob)
		if objects:
			if context.scene.objects.active in objects:
				for ob in objects:
					if ob != context.scene.objects.active:
						self.originals.append(ob)
				self.originals.append(context.scene.objects.active)
			else:
				self.originals = originals
			dim = ut.dimensions_transformed(*self.originals)
			self.dimensions.x = dim.x
			self.dimensions.y = dim.y
		elif context.selected_editable_objects:
			self.error = ERROR_SELECTED_NO_MESH_DATA
		elif context.selected_objects:
			self.error = ERROR_SELECTED_INACTIVE_LAYER
		else:
			ob = context.scene.objects.active
			if ob:
				if ob.data:
					if ob not in context.editable_objects:
						self.error = ERROR_ACTIVE_INACTIVE_LAYER
					else:
						dim = ut.dimensions_transformed(ob)
						self.dimensions.x = dim.x
						self.dimensions.y = dim.y
						self.originals.append(ob)
				else:
					self.error = ERROR_ACTIVE_NO_MESH_DATA
			else:
				self.error = ERROR_NO_ACTIVE_OR_SELECTED
				
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
		col_numb = col()
		col_numb.prop(context.scene.bdx_tools, "plane_sect_number")
		col_size = col()
		col_size.prop(context.scene.bdx_tools, "plane_sect_size")
		col_size.prop(context.scene.bdx_tools, "plane_sect_number_mode")
		
		if context.scene.bdx_tools.plane_sect_number_or_size == "generate_by_number":
			col_size.active = False
		else:
			col_numb.active = False
			
		col = row().column
		col().prop(context.scene.bdx_tools, "plane_sect_apply_modifiers")
		col_sett = col()
		col_sett.prop(context.scene.bdx_tools, "plane_sect_modifiers_settings")
		if not context.scene.bdx_tools.plane_sect_apply_modifiers:
			col_sett.active = False
			
		col = row().column
		col().prop(context.scene.bdx_tools, "plane_sect_decimate")
		col_deci = col()
		col_deci.prop(context.scene.bdx_tools, "plane_sect_decimate_dissolve_angle_limit")
		col_deci.prop(context.scene.bdx_tools, "plane_sect_decimate_collapse_ratio")
		if not context.scene.bdx_tools.plane_sect_decimate:
			col_deci.active = False
			
		row().prop(context.scene.bdx_tools, "plane_sect_gen_options")
		
		col = row().column
		col_appr = col()
		col_appr.prop(context.scene.bdx_tools, "plane_sect_approximate")
		col_ndig = col()
		col_ndig.prop(context.scene.bdx_tools, "plane_sect_approx_ndigits")
		
		if context.scene.bdx_tools.plane_sect_gen_options == "generate_sections":
			col_appr.active = False
			col_ndig.active = False
		else:
			if not context.scene.bdx_tools.plane_sect_approximate:
				col_ndig.active = False
			if not hasattr(context.scene, "bdx"):
				row().label(WARN_BDX_NOT_INSTALLED + " " + WARN_BDX_SAVE_DIR, icon="ERROR")
			elif not ut.src_root():
				row().label(WARN_BDX_PROJECT_MISSING + " " + WARN_BDX_SAVE_DIR, icon="ERROR")
				
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
			
		if context.scene.bdx_tools.plane_sect_number_or_size == "generate_by_number":
			self.sect_numb.x = context.scene.bdx_tools.plane_sect_number[0]
			self.sect_numb.y = context.scene.bdx_tools.plane_sect_number[1]
			self.sect_size.x = self.dimensions.x / self.sect_numb.x
			self.sect_size.y = self.dimensions.y / self.sect_numb.y
		else:
			self.sect_size.x = context.scene.bdx_tools.plane_sect_size[0]
			self.sect_size.y = context.scene.bdx_tools.plane_sect_size[1]
			n_x = math.ceil(self.dimensions.x / self.sect_size.x)
			n_y = math.ceil(self.dimensions.y / self.sect_size.y)
			numb_mode = context.scene.bdx_tools.plane_sect_number_mode
			if numb_mode == "use_automatic_numbering":
				self.sect_numb.x = n_x
				self.sect_numb.y = n_y
			else:
				i = 0 if numb_mode == "use_even_numbers" else 1
				self.sect_numb.x = n_x + 1 - i if n_x % 2 else n_x + i
				self.sect_numb.y = n_y + 1 - i if n_y % 2 else n_y + i
				
		prof = ut.Profiler()
		
		print("\nSectionalizing Plane\n--------------------\n")
		
		bpy.ops.object.mode_set(mode="OBJECT")
		bpy.ops.object.select_all(action="DESELECT")
		
		tmps = []
		tmps_particles = []
		
		ob_base = self.originals[-1]
		
		objects = list(self.originals)
		for original in self.originals:
			for modifier in original.modifiers:
				if modifier.type == "PARTICLE_SYSTEM":
					
					show = context.scene.bdx_tools.plane_sect_modifiers_settings.upper()
					if modifier.show_viewport and show == "PREVIEW" or modifier.show_render and show == "RENDER":
						
						print(prof.timed("Creating temp data particles"))
						
						settings = modifier.particle_system.settings
						
						dupli_object = None
						if settings.dupli_object:
							dupli_object = context.scene.objects[settings.dupli_object.name]
							tmp = ut.copy(context.scene, dupli_object, False, TEMP_SUFFIX)
							settings.dupli_object = tmp
							tmps.append(tmp)
							
						context.scene.objects.active = original
						original.select = True
						bpy.ops.object.duplicates_make_real()
						settings.dupli_object = dupli_object
						original.select = False
						
						selected_objects = list(context.selected_objects)
						context.scene.objects.active = selected_objects[0]
						bpy.ops.object.select_all(action="DESELECT")
						context.scene.objects.active.select = True
						for ob in selected_objects:
							tmps_particles.append(ob)
							ob.select = True
							
						bpy.ops.object.join()
						particles = context.selected_objects[0]
						tmps_particles.append(particles)
						objects.append(particles)
						particles.select = False
					
		print(prof.timed("Creating temp data"))
		
		if len(objects) == 1:
			ob_tmp = ut.copy(context.scene, ob_base, True, TEMP_SUFFIX + ".000", context.scene.bdx_tools.plane_sect_apply_modifiers, context.scene.bdx_tools.plane_sect_modifiers_settings.upper())
			context.scene.objects.active = ob_tmp
			ob_tmp.select = True
			ob_base.select = False
			ob_base.hide = True
		else:
			tmp_objects = []
			for ob in objects:
				ob_tmp = ut.copy(context.scene, ob, True, TEMP_SUFFIX + ".000", context.scene.bdx_tools.plane_sect_apply_modifiers, context.scene.bdx_tools.plane_sect_modifiers_settings.upper())
				tmp_objects.append(ob_tmp)
				ob.select = False
				ob.hide = True
				
			ob_tmp = tmp_objects[0]
			for ob in tmp_objects:
				if ob != ob_tmp:
					context.scene.objects.active = ob
					ob.select = True
					bpy.ops.object.duplicate(linked=True, mode="INIT")
					tmp = context.scene.objects.active
					tmps.append(tmp)
					tmp.select = False
					ob.select = False
			for ob in tmp_objects:
				ob.select = True
			context.scene.objects.active = ob_tmp
			
			bpy.ops.object.join()
			
		bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
		bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")
		off = ob_tmp.location.copy()
		off.x = int(off.x / self.sect_size.x) * self.sect_size.x
		off.y = int(off.y / self.sect_size.y) * self.sect_size.y
		off.z = 0
		loc = ob_tmp.location = ob_tmp.location - off
		
		bpy.ops.object.mode_set(mode="OBJECT")
		bpy.ops.object.editmode_toggle()
		bpy.ops.mesh.select_mode(type="FACE")
		bpy.ops.mesh.select_all(action="SELECT")
		
		print(prof.timed("Beautifying"))
		
		bpy.ops.mesh.quads_convert_to_tris()
		bpy.ops.mesh.beautify_fill()
		
		if context.scene.bdx_tools.plane_sect_decimate:
			
			if context.scene.bdx_tools.plane_sect_decimate_dissolve_angle_limit:
				
				print(prof.timed("Decimating - dissolve"))
				
				bpy.ops.mesh.beautify_fill()
				bpy.ops.mesh.dissolve_limited(angle_limit=context.scene.bdx_tools.plane_sect_decimate_dissolve_angle_limit, delimit={"NORMAL", "MATERIAL", "SEAM", "SHARP", "UV"})
				bpy.ops.mesh.quads_convert_to_tris()
				bpy.ops.mesh.beautify_fill()
				
			if context.scene.bdx_tools.plane_sect_decimate_collapse_ratio < 1:
				
				print(prof.timed("Decimating - collapse"))
				
				bpy.ops.mesh.decimate(ratio=context.scene.bdx_tools.plane_sect_decimate_collapse_ratio)
				bpy.ops.mesh.quads_convert_to_tris()
				bpy.ops.mesh.beautify_fill()
				
		bpy.ops.object.editmode_toggle()
		
		print(prof.timed("Separating loose parts"))
		
		bpy.ops.mesh.separate(type="LOOSE")
		parts = {ob : [] for ob in context.selected_objects}
		bpy.ops.object.select_all(action="DESELECT")
		
		print(prof.timed("Multisecting"))
		
		dir_x = numpy.sign(int(loc.x))
		dir_y = numpy.sign(int(loc.y))
		start_x = 0 if dir_x < 0 else 1
		start_y = 0 if dir_y < 0 else 1
		end_x = int(self.sect_numb.x) + abs(dir_x) + 1
		end_y = int(self.sect_numb.y) + abs(dir_y) + 1
		
		for part_base in parts.keys():
			
			tmps.append(part_base)
			
			ob_sect = ut.copy(context.scene, part_base)
			ob_sect.name = ob_base.name + PART_SUFFIX + ".000"
			ob_sect.data.name = ob_base.data.name + PART_SUFFIX + ".000"
			context.scene.objects.active = ob_sect
			parts[part_base].append(ob_sect)
			
			bpy.ops.object.editmode_toggle()
			
			bm = bmesh.from_edit_mesh(ob_sect.data)
			
			for i in range(start_x, end_x):
				try:
					l = bm.verts[:] + bm.edges[:] + bm.faces[:]
					co = ((i - 0.5 * self.sect_numb.x) * self.sect_size.x - loc.x, 0, 0)
					no = (1, 0, 0)
					dict = bmesh.ops.bisect_plane(bm, geom=l, plane_co=co, plane_no=no)
					bmesh.ops.split_edges(bm, edges=[e for e in dict["geom_cut"] if isinstance(e, bmesh.types.BMEdge)])
				except RuntimeError:
					continue
					
			for i in range(start_y, end_y):
				try:
					l = bm.verts[:] + bm.edges[:] + bm.faces[:]
					co = (0, (i - 0.5 * self.sect_numb.y) * self.sect_size.y - loc.y, 0)
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
		
		for objects in parts.values():
			ob = objects[0]
			context.scene.objects.active = ob
			ob.select = True
			bpy.ops.mesh.separate(type="LOOSE")
			objects[:] = context.selected_objects
			bpy.ops.object.select_all(action="DESELECT")
			
		print(prof.timed("Transferring normals"))
		
		n = 1
		n_total = 0
		for objects in parts.values():
			n_total += len(objects)
			
		for part_base, objects in parts.items():
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
				cn.object = part_base
				cn.use_loop_data = True
				cn.data_types_loops = {"CUSTOM_NORMAL"}
				cn.mix_factor = 1
				bpy.ops.object.modifier_apply(modifier=cn.name)
				
		print(prof.timed("Finalizing sections"))
		
		sections = []
		
		sect_offset = self.sect_size * 0.5
		sect_locations = []
		for j in range(start_y, end_y):
			y = (j - 0.5 * self.sect_numb.y) * self.sect_size.y - sect_offset.y
			for i in range(start_x, end_x):
				x = (i - 0.5 * self.sect_numb.x) * self.sect_size.x - sect_offset.x
				sect_locations.append(Vector((x, y, 0)))
				
		cursor_location = context.scene.cursor_location.copy()
		
		id_length = len(str(len(sect_locations)))
		sect_parts = OrderedDict()
		for i in range(len(sect_locations)):
			sect_parts[ut.id(i, "", id_length)] = []
			
		for objects in parts.values():
			for ob in objects:
				context.scene.objects.active = ob
				ob.select = True
				
				inside = False
				bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY")
				for i, v in enumerate(sect_locations):
					if ut.point_inside_rectangle(ob.location, (v, self.sect_size)):
						sect_parts[ut.id(i, "", id_length)].append(ob)
						context.scene.cursor_location = v
						bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
						inside = True
						break
						
				if not inside:
					tmps.append(ob)
					
				ob.select = False
				
		i = 0
		id_length = max(len(str(len(sect_parts))), 3)
		for parts in sect_parts.values():
			if len(parts):
				relevant_parts = []
				for p in parts:
					if not p.data.polygons:
						tmps.append(p)
					else:
						relevant_parts.append(p)
						
				if relevant_parts:
					sect = relevant_parts[0]
					
					if len(relevant_parts) > 1:
						bpy.ops.object.select_all(action="DESELECT")
						for ob in relevant_parts:
							if ob != sect:
								context.scene.objects.active = ob
								ob.select = True
								bpy.ops.object.duplicate(linked=True, mode="INIT")
								tmp = context.scene.objects.active
								tmps.append(tmp)
								tmp.select = False
								ob.select = False
						for ob in relevant_parts:
							ob.select = True
						context.scene.objects.active = sect
						bpy.ops.object.join()
						
					sect.select = False
					id = ut.id(i, ".", id_length)
					sect.name = sect.name.split(PART_SUFFIX)[0] + SECT_SUFFIX + id
					sect.data.name = sect.data.name.split(PART_SUFFIX)[0] + SECT_SUFFIX + id
					sections.append(sect)
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
		
		for ob in tmps:
			me = ob.data
			bpy.data.objects.remove(ob, do_unlink=True)
			bpy.data.meshes.remove(me, do_unlink=True)
			
		for ob in tmps_particles:
			bpy.data.objects.remove(ob, do_unlink=True)
			
		if not context.scene.bdx_tools.plane_sect_gen_options == "generate_sections":
			
			print(prof.timed("Extracting BDX data"))
			
			num_vertices_max = 0
			
			tfs = 3 * 8
			data = {}
			data_objects = OrderedDict()
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
						
				section["model"] = m_verts
				section["position"] = list(sect.location)
				data_objects[sect.name] = section
				data["objects"] = data_objects
				offset = []
				for i, n in enumerate(self.sect_numb):
					offset.append(0 if n % 2 else self.sect_size[i] * 0.5)
				data["offset"] = offset + [0]
				data["size"] = list(self.sect_size) + [0]
				
			if (num_vertices_max > 4095):
				print("WARNING: Meshes with more than 4095 vertices (1365 triangles) per material are not supported in BDX.\nAt least one section has", num_vertices_max, "vertices, or", num_vertices_max // 3, "triangles. Exporting json file aborted.")
				
			else:
				print(prof.timed("Exporting json file"))
				
				root = ut.assets_root() if ut.project_root() else bpy.path.abspath("//")
				file_path = os.path.join(root, ob_base.name + ".sctx")
				with open(file_path, 'w') as f:
					json.dump(data, f)
					
			for original in self.originals:
				original.select = True	
				context.scene.objects.active = original
				
		del self.originals[:]
		
		if context.scene.bdx_tools.plane_sect_gen_options == "save_json_file":
			
			print(prof.timed("Removing sections"))
			
			for ob in sections:
				me = ob.data
				bpy.data.objects.remove(ob, do_unlink=True)
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

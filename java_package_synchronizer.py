import bpy
from . import utils as ut

error_bdx_not_installed = "BDX add-on not installed!"
error_bdx_project_missing = "BDX project missing!"
error_bdx_java_pack = "Java packages are not in sync with BDX project!"

class JavaPackageSynchronizer(bpy.types.Operator):
	
	bl_description = "Sychronizes package names of java classes with BDX project"
	bl_idname = "bdx.java_package_synchronizer"
	bl_label = "BDX-Tools: Java Package Synchronizer"
	bl_options = {"REGISTER", "UNDO"}
	
	error = ""
	
	def invoke(self, context, event):
		
		if not hasattr(context.scene, "bdx"):
			self.error = error_bdx_not_installed
			
		elif not ut.src_root():
			self.error = error_bdx_project_missing
			
		system_dpi = bpy.context.user_preferences.system.dpi
		
		return context.window_manager.invoke_props_dialog(self, width=system_dpi*5)
		
	def draw(self, context):
		layout = self.layout
		box = layout.box()
		row = box.row
		
		if self.error:
			row().label(self.error, icon="ERROR")
			return
			
		sc_bdx_tools = context.scene.bdx_tools
		
		if ut.java_pack_error():
			row().label(error_bdx_java_pack, icon="ERROR")
			row().prop(context.scene.bdx_tools, "java_pack_sync")
		else:
			row().label("Java packages synced with BDX project: " + ut.java_pack_name())
			
	def execute(self, context):
		if self.error:
			return {"CANCELLED"}
			
		if context.scene.bdx_tools.java_pack_sync:
			ut.java_pack_sync();
			
		return {"PASS_THROUGH"}
		
def register():
	bpy.utils.register_class(JavaPackageSynchronizer)
	
def unregister():
	bpy.utils.unregister_class(JavaPackageSynchronizer)
	
if __name__ == "__main__":
	register()
	
import bpy
from . import utils as ut

error_bdx_not_installed = "BDX add-on not installed!"
error_bdx_project_missing = "BDX project missing!"

class AndroidProjectManager(bpy.types.Operator):
	
	bl_description = ""
	bl_idname = ".001"
	bl_label = "BDX-Tools: Android Project Manager"
	bl_options = {"REGISTER", "UNDO"}
	bl_info = "Enables/disables Vibrator, Accelerometer, Gyroscope, Compass and Rotation for a BDX Android Project"
	
	error = ""
	
	sc_bdx_tools = None
	
	gdx_al = ""
	gdx_am = ""
	
	gdx_am_lines = None
	gdx_al_lines = None
	
	enum_line_rotation = None
	enum_line_vibrator = None
	enum_line_accelerometer = None
	enum_line_gyroscope = None
	enum_line_compass = None
	
	android_screen_orientation = False
	android_use_vibrator = False
	android_use_accelerometer = False
	android_use_gyroscope = False
	android_use_compass = False
	
	def invoke(self, context, event):
		
		if not hasattr(context.scene, "bdx"):
			self.error = error_bdx_not_installed
			
		elif not ut.src_root():
			self.error = error_bdx_project_missing
			
		else:
			self.gdx_al = ut.android_launcher()
			self.gdx_am = ut.android_manifest()
			self.gdx_am_lines = ut.lines(self.gdx_am)
			self.gdx_al_lines = ut.lines(self.gdx_al)
			
			self.sc_bdx_tools = context.scene.bdx_tools;
			
			# rotation
			
			self.enum_line_rotation = ut.enum_line_containing(self.gdx_am_lines, "android:screenOrientation")
			self.sc_bdx_tools.android_screen_orientation = self.enum_line_rotation[1].split("=")[1].strip("\"\n")
			self.android_screen_orientation = self.sc_bdx_tools.android_screen_orientation
			
			# vibrator
			
			self.enum_line_vibrator = ut.enum_line_containing(self.gdx_am_lines, "android.permission.VIBRATE")
			self.sc_bdx_tools.android_use_vibrator = self.android_use_vibrator = self.enum_line_vibrator is not None
			
			# accelerometer
			
			self.enum_line_accelerometer = ut.enum_line_containing(self.gdx_al_lines, "config.useAccelerometer")
			self.sc_bdx_tools.android_use_accelerometer = self.android_use_accelerometer = self.enum_line_accelerometer is not None
			
			# gyroscope
			
			self.enum_line_gyroscope = ut.enum_line_containing(self.gdx_al_lines, "config.useGyroscope")
			self.sc_bdx_tools.android_use_gyroscope = self.android_use_gyroscope = self.enum_line_gyroscope is not None
			
			# compass
			
			self.enum_line_compass = ut.enum_line_containing(self.gdx_al_lines, "config.useCompass")
			self.sc_bdx_tools.android_use_compass = self.android_use_compass = self.enum_line_compass is not None
			
		system_dpi = bpy.context.user_preferences.system.dpi
		
		return context.window_manager.invoke_props_dialog(self, width=system_dpi*5)
		
	def draw(self, context):
		layout = self.layout
		box = layout.box()
		row = box.row
		
		if self.error:
			row().label(self.error, icon="ERROR")
			return
			
		row().prop(self.sc_bdx_tools, "android_screen_orientation")
		col = row().column
		col().prop(self.sc_bdx_tools, "android_use_accelerometer")
		col().prop(self.sc_bdx_tools, "android_use_vibrator")
		col = row().column
		col().prop(self.sc_bdx_tools, "android_use_gyroscope")
		col().prop(self.sc_bdx_tools, "android_use_compass")
		
	def execute(self, context):
		if self.error:
			return {"CANCELLED"}
			
		# rotation
		
		if self.android_screen_orientation != self.sc_bdx_tools.android_screen_orientation:
			new_line = "\t\t\tandroid:screenOrientation=\"" + self.sc_bdx_tools.android_screen_orientation + "\""
			index, _ = self.enum_line_rotation
			if index:
				ut.replace_line(index, self.gdx_am_lines, new_line)
			else:
				index, _ = ut.enum_line_containing(self.gdx_am_lines, "<activity")
				ut.insert_line(index + 1, self.gdx_am_lines, "\n" + new_line)
				
		# vibrator
		
		if self.android_use_vibrator != self.sc_bdx_tools.android_use_vibrator:
			if self.sc_bdx_tools.android_use_vibrator:
				new_line = "\t<uses-permission android:name=\"android.permission.VIBRATE\" />"
				index, _ = ut.enum_line_containing(self.gdx_am_lines, "<application")
				ut.insert_line(index, self.gdx_am_lines, new_line + "\n")
			else:
				self.gdx_am_lines.remove(self.enum_line_vibrator[1])
				
		# accelerometer
		
		if self.android_use_accelerometer != self.sc_bdx_tools.android_use_accelerometer:
			if self.sc_bdx_tools.android_use_accelerometer:
				new_line = "\t\tconfig.useAccelerometer = true;"
				index, _ = ut.enum_line_containing(self.gdx_al_lines, "AndroidApplicationConfiguration()")
				ut.insert_line(index + 1, self.gdx_al_lines, new_line)
			else:
				self.gdx_al_lines.remove(self.enum_line_accelerometer[1])
				
		# gyroscope
		
		if self.android_use_gyroscope != self.sc_bdx_tools.android_use_gyroscope:
			if self.sc_bdx_tools.android_use_gyroscope:
				new_line = "\t\tconfig.useGyroscope = true;"
				index, _ = ut.enum_line_containing(self.gdx_al_lines, "AndroidApplicationConfiguration()")
				ut.insert_line(index + 1, self.gdx_al_lines, new_line)
			else:
				self.gdx_al_lines.remove(self.enum_line_gyroscope[1])
				
		# compass
		
		if self.android_use_compass != self.sc_bdx_tools.android_use_compass:
			if self.sc_bdx_tools.android_use_compass:
				new_line = "\t\tconfig.useCompass = true;"
				index, _ = ut.enum_line_containing(self.gdx_al_lines, "AndroidApplicationConfiguration()")
				ut.insert_line(index + 1, self.gdx_al_lines, new_line)
			else:
				self.gdx_al_lines.remove(self.enum_line_compass[1])
				
		ut.write_lines(self.gdx_am_lines, self.gdx_am)
		ut.write_lines(self.gdx_al_lines, self.gdx_al)
		
		return {"PASS_THROUGH"}
		
def register():
	bpy.utils.register_class(AndroidProjectManager)
	
def unregister():
	bpy.utils.unregister_class(AndroidProjectManager)
	
if __name__ == "__main__":
	register()
	
import bpy
from . import utils as ut

error_bdx_not_installed = "BDX add-on not installed!"
error_bdx_project_missing = "BDX project missing!"

class AndroidProjectManager(bpy.types.Operator):
	
	bl_description = "Configures a BDX Android Project: enables/disables Vibrator, Accelerometer, Gyroscope, Compass and Rotation; specifies Screen Orientation and Resolution Strategy"
	bl_idname = "bdx.android_project_manager"
	bl_label = "BDX-Tools: Android Project Manager"
	bl_options = {"REGISTER", "UNDO"}
	
	error = ""
	
	sc_bdx_tools = None
	
	gdx_al = ""
	gdx_am = ""
	
	gdx_am_lines = None
	gdx_al_lines = None
	
	android_screen_orientation = ""
	android_resolution_strategy = ""
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
			
			enum_line = ut.enum_line_containing(self.gdx_am_lines, "screenOrientation")
			self.sc_bdx_tools.android_screen_orientation = enum_line[1].split("=")[1].strip("\"\n")
			self.android_screen_orientation = self.sc_bdx_tools.android_screen_orientation
			
			# resolution strategy
			
			enum_line = ut.enum_line_containing(self.gdx_al_lines, "resolutionStrategy")
			enum_line_import = ut.enum_line_containing(self.gdx_al_lines, "import com.badlogic.gdx.backends.android.surfaceview.RatioResolutionStrategy;")
			if enum_line_import:
				ut.replace_line(enum_line_import[0], self.gdx_al_lines, "");
				new_line = "\t\tconfig.resolutionStrategy = new com.badlogic.gdx.backends.android.surfaceview.RatioResolutionStrategy(width, height);"
				ut.replace_line(enum_line[0], self.gdx_al_lines, new_line)
				enum_line[1] = new_line
			self.sc_bdx_tools.android_resolution_strategy = enum_line[1].split("= new com.badlogic.gdx.backends.android.surfaceview.")[1].strip(";\n")
			self.android_resolution_strategy = self.sc_bdx_tools.android_resolution_strategy
			
			# vibrator
			
			enum_line = ut.enum_line_containing(self.gdx_am_lines, "VIBRATE")
			self.sc_bdx_tools.android_use_vibrator = self.android_use_vibrator = enum_line is not None
			
			# accelerometer
			
			enum_line = ut.enum_line_containing(self.gdx_al_lines, "useAccelerometer")
			android_use_accelerometer = True
			if not enum_line:
				index = ut.enum_line_containing(self.gdx_al_lines, "AndroidApplicationConfiguration()")[0] + 1
				new_line = "\t\tconfig.useAccelerometer = true;"
				ut.insert_line(index, self.gdx_al_lines, new_line)
			elif "false" in enum_line[1]:
				android_use_accelerometer = False
			self.sc_bdx_tools.android_use_accelerometer = self.android_use_accelerometer = android_use_accelerometer
			
			# gyroscope
			
			enum_line = ut.enum_line_containing(self.gdx_al_lines, "useGyroscope")
			android_use_gyroscope = False
			if not enum_line:
				index = ut.enum_line_containing(self.gdx_al_lines, "AndroidApplicationConfiguration()")[0] + 1
				new_line = "\t\tconfig.useGyroscope = false;"
				ut.insert_line(index, self.gdx_al_lines, new_line)
			elif "true" in enum_line[1]:
				android_use_gyroscope = True
			self.sc_bdx_tools.android_use_gyroscope = self.android_use_gyroscope = android_use_gyroscope
			
			# compass
			
			enum_line = ut.enum_line_containing(self.gdx_al_lines, "useCompass")
			android_use_compass = True
			if not enum_line:
				index = ut.enum_line_containing(self.gdx_al_lines, "AndroidApplicationConfiguration()")[0] + 1
				new_line = "\t\tconfig.useCompass = true;"
				ut.insert_line(index, self.gdx_al_lines, new_line)
			elif "false" in enum_line[1]:
				android_use_compass = False
			self.sc_bdx_tools.android_use_compass = self.android_use_compass = android_use_compass
			
		system_dpi = bpy.context.user_preferences.system.dpi
		
		return context.window_manager.invoke_props_dialog(self, width=system_dpi*5)
		
	def draw(self, context):
		layout = self.layout
		box = layout.box()
		row = box.row
		
		if self.error:
			row().label(self.error, icon="ERROR")
			return
			
		row(align=True).prop(self.sc_bdx_tools, "android_screen_orientation")
		row(align=True).prop(self.sc_bdx_tools, "android_resolution_strategy")
		col = row(align=True).column
		col().prop(self.sc_bdx_tools, "android_use_accelerometer")
		col().prop(self.sc_bdx_tools, "android_use_vibrator")
		col = row(align=True).column
		col().prop(self.sc_bdx_tools, "android_use_compass")
		col().prop(self.sc_bdx_tools, "android_use_gyroscope")
		
	def execute(self, context):
		if self.error:
			return {"CANCELLED"}
			
		# vibrator
		
		if self.android_use_vibrator != self.sc_bdx_tools.android_use_vibrator:
			index = ut.enum_line_containing(self.gdx_am_lines, "</application>")[0] + 1
			if self.sc_bdx_tools.android_use_vibrator:
				new_line = "\t<uses-permission android:name=\"android.permission.VIBRATE\" />"
				ut.insert_line(index, self.gdx_am_lines, new_line)
			else:
				self.gdx_am_lines.remove(self.gdx_am_lines[index])
				
		# rotation
		
		if self.android_screen_orientation != self.sc_bdx_tools.android_screen_orientation:
			index = ut.enum_line_containing(self.gdx_am_lines, "screenOrientation")[0]
			new_line = "\t\t\tandroid:screenOrientation=\"" + self.sc_bdx_tools.android_screen_orientation + "\""
			ut.replace_line(index, self.gdx_am_lines, new_line)
			
		# resolution strategy
		
		if self.android_resolution_strategy != self.sc_bdx_tools.android_resolution_strategy:
			index = ut.enum_line_containing(self.gdx_al_lines, "resolutionStrategy")[0]
			new_line = "\t\tconfig.resolutionStrategy = new com.badlogic.gdx.backends.android.surfaceview." + self.sc_bdx_tools.android_resolution_strategy + ";"
			ut.replace_line(index, self.gdx_al_lines, new_line)
			
		# accelerometer
		
		if self.android_use_accelerometer != self.sc_bdx_tools.android_use_accelerometer:
			index = ut.enum_line_containing(self.gdx_al_lines, "useAccelerometer")[0]
			new_line = "\t\tconfig.useAccelerometer = " + str(self.sc_bdx_tools.android_use_compass).lower() + ";"
			ut.replace_line(index, self.gdx_al_lines, new_line)
			
		# gyroscope
		
		if self.android_use_gyroscope != self.sc_bdx_tools.android_use_gyroscope:
			index = ut.enum_line_containing(self.gdx_al_lines, "useGyroscope")[0]
			new_line = "\t\tconfig.useGyroscope = " + str(self.sc_bdx_tools.android_use_compass).lower() + ";"
			ut.replace_line(index, self.gdx_al_lines, new_line)
			
		# compass
		
		if self.android_use_compass != self.sc_bdx_tools.android_use_compass:
			index = ut.enum_line_containing(self.gdx_al_lines, "useCompass")[0]
			new_line = "\t\tconfig.useCompass = " + str(self.sc_bdx_tools.android_use_compass).lower() + ";"
			ut.replace_line(index, self.gdx_al_lines, new_line)
			
		ut.write_lines(self.gdx_am_lines, self.gdx_am)
		ut.write_lines(self.gdx_al_lines, self.gdx_al)
		
		return {"PASS_THROUGH"}
		
def register():
	bpy.utils.register_class(AndroidProjectManager)
	
def unregister():
	bpy.utils.unregister_class(AndroidProjectManager)
	
if __name__ == "__main__":
	register()
	
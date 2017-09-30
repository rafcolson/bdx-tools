bl_info = {
	"name": "Raco's BDX Tools",
	"author": "Raf Colson",
	"version": (0, 0, 1),
	"blender": (2, 77, 0),
	"location": "SpaceBar Search -> BDX-Tools: Java Package Synchronizer / BDX-Tools: Android Project Manager",
	"description": "Tools for the BDX 3D game engine -> https://github.com/GoranM/bdx",
	"warning": "Requires the BDX add-on -> https://github.com/GoranM/bdx/releases",
	"wiki_url": "https://github.com/rafcolson/bdx-tools/wiki",
	"tracker_url": "https://github.com/rafcolson/bdx-tools/issues",
	"category": "BDX"
}

import bpy
import math

from . import (
	java_package_synchronizer,
	android_project_manager,
	plane_sectionalizer
)

class BdxToolsProps(bpy.types.PropertyGroup):
	
	java_pack_sync = bpy.props.BoolProperty(name="Sync java packages")
	
	android_screen_orientation_items = [
		("unspecified", "Unspecified", ""),
		("behind", "Behind", ""),
		("landscape", "Landscape", ""),
		("portrait", "Portrait", ""),
		("reverseLandscape", "Reverse Landscape", ""),
		("reversePortrait", "Reverse Portrait", ""),
		("sensorLandscape", "Sensor Landscape", ""),
		("sensorPortrait", "Sensor Portrait", ""),
		("userLandscape", "User Landscape", ""),
		("userPortrait", "User Portrait", ""),
		("sensor", "Sensor", ""),
		("fullSensor", "Full Sensor", ""),
		("nosensor", "No Sensor", ""),
		("user", "User", ""),
		("fullUser", "Full User", ""),
		("locked", "Locked", ""),
	]
	android_resolution_strategy_items = [
		("FillResolutionStrategy()", "Fill", ""),
		("RatioResolutionStrategy(width, height)", "Ratio", ""),
		("FixedResolutionStrategy(width, height)", "Fixed", "")
	]
	android_screen_orientation = bpy.props.EnumProperty(items=android_screen_orientation_items, name="Screen Orientation", default="landscape")
	android_resolution_strategy = bpy.props.EnumProperty(items=android_resolution_strategy_items, name="Resolution Strategy", default="RatioResolutionStrategy(width, height)")
	android_use_vibrator = bpy.props.BoolProperty(name="Use Vibrator")
	android_use_accelerometer = bpy.props.BoolProperty(name="Use Accelerometer")
	android_use_gyroscope = bpy.props.BoolProperty(name="Use Gyroscope")
	android_use_compass = bpy.props.BoolProperty(name="Use Compass")
	
	plane_sect_number_or_size = bpy.props.EnumProperty(items=[("generate_by_number", "Number", ""), ("generate_by_size", "Size", "")], name="Generate by", default="generate_by_size")
	plane_sect_number = bpy.props.IntVectorProperty(name="", description="Number of sections", min=1, soft_max=100, default=(4, 4), size=2)
	plane_sect_size = bpy.props.FloatVectorProperty(name="", description="Section size", min=1, soft_max=128, default=(16, 16), size=2)
	plane_sect_number_mode = bpy.props.EnumProperty(items=[("use_automatic_numbering", "Use Automatic Numbering", ""), ("use_even_numbers", "Use Even Numbers", ""), ("use_odd_numbers", "Use Odd Numbers", "")], name="", default="use_even_numbers")
	plane_sect_apply_modifiers = bpy.props.BoolProperty(name="Apply Modifiers", default=True)
	plane_sect_modifiers_settings = bpy.props.EnumProperty(items=[("preview", "Preview", ""), ("render", "Render", "")], name="", default="preview")
	plane_sect_decimate = bpy.props.BoolProperty(name="Decimate", default=False)
	plane_sect_decimate_dissolve_angle_limit = bpy.props.FloatProperty(name="", min=0, max=math.pi, default=math.radians(1), subtype="ANGLE")
	plane_sect_decimate_collapse_ratio = bpy.props.FloatProperty(name="", min=0, max=1, default=0.9, subtype="FACTOR")
	plane_sect_gen_options = bpy.props.EnumProperty(items=[("save_json_file", "Save Json File", ""), ("generate_sections", "Generate Sections", ""), ("generate_sections_and_save_json_file", "Generate Sections and Save Json File", "")], name="", default="generate_sections_and_save_json_file")
	plane_sect_approximate = bpy.props.BoolProperty(name="Approximate")
	plane_sect_approx_ndigits = bpy.props.IntProperty(name="", min=0, max=15, default=4)
	
bpy.utils.register_class(BdxToolsProps)
bpy.types.Scene.bdx_tools = bpy.props.PointerProperty(type=BdxToolsProps)

modules = [java_package_synchronizer, android_project_manager, plane_sectionalizer]

def register():
	for m in modules:
		m.register()

def unregister():
	for m in modules:
		m.unregister()

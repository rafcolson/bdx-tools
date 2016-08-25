bl_info = {
	"name": "Raco's BDX Tools",
	"author": "Raf Colson",
	"version": (0, 0, 1),
	"blender": (2, 77, 0),
	"location": "SpaceBar Search -> BDX-Tools Java Package Synchronizer / BDX-Tools Android Project Manager",
	"description": "Tools for the BDX 3D game engine -> https://github.com/GoranM/bdx",
	"warning": "Requires the BDX add-on -> https://github.com/GoranM/bdx/releases",
	"wiki_url": "https://github.com/rafcolson/bdx-tools/wiki",
	"tracker_url": "https://github.com/rafcolson/bdx-tools/issues",
	"category": "BDX"
}

import bpy
from . import (
	java_package_synchronizer,
	android_project_manager
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
	android_screen_orientation = bpy.props.EnumProperty(items=android_screen_orientation_items, name="Screen Orientation", default="landscape")
	android_use_vibrator = bpy.props.BoolProperty(name="Use Vibrator")
	android_use_accelerometer = bpy.props.BoolProperty(name="Use Accelerometer")
	android_use_gyroscope = bpy.props.BoolProperty(name="Use Gyroscope")
	android_use_compass = bpy.props.BoolProperty(name="Use Compass")
	
bpy.utils.register_class(BdxToolsProps)
bpy.types.Scene.bdx_tools = bpy.props.PointerProperty(type=BdxToolsProps)

modules = [java_package_synchronizer, android_project_manager]

def register():
	for m in modules:
		m.register()

def unregister():
	for m in modules:
		m.unregister()

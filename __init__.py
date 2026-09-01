"""
视图警示 HUD (重构增强版)
版本：2.6.2
快捷键：Shift + F2 开关
说明：
- 显示核心视图警示与物体信息
- 支持中英文
- 支持显示模式：始终显示 / 仅警示时显示 / 关闭
- 支持 HUD 锚点与外观设置
"""

bl_info = {
    "name": "视图警示",
    "author": "一枫",
    "version": (2, 6, 2),
    "blender": (3, 0, 0),
    "location": "3D View > N-Panel > 视图警示",
    "description": "显示核心视图警示与物体信息，支持 UIList 警示状态与折叠分组",
    "category": "3D View",
}

import bpy
import blf
import math
import time

from bpy.types import (
    AddonPreferences,
    Panel,
    Operator,
    PropertyGroup,
    UIList,
)
from bpy.props import (
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    StringProperty,
    EnumProperty,
    CollectionProperty,
)

# 全局绘制句柄 & 快捷键列表
_viewstatus_handle = None
addon_keymaps = []

# HUD 状态采集缓存：draw handler 每帧都会调用，缓存只包住状态采集，绘制仍每帧执行。
# key 按 3D View 区域/Region/Space 区分，避免多视图显示串线。
_HUD_CACHE_DEFAULT_INTERVAL = 0.15
_hud_status_cache = {}
_hud_cache_generation = 0
_HUD_CACHE_MAX_ENTRIES = 32
_HUD_CACHE_PRUNE_AGE = 30.0

# 翻译缓存：语言切换时由 update_hud / register 同步，避免每帧每次 T() 都查 addon prefs。
_cached_trans = None

# ------------------------------------------------------------------------
# 翻译字典
# ------------------------------------------------------------------------

TRANS_DATA = {
    "CN": {
        "label_cam": "当前相机：",
        "label_cam_none": "当前相机：无",
        "label_coord": "坐标系：",
        "label_pivot": "轴心：",
        "label_color": "物体颜色：",
        "label_xray": "X-Ray：",
        "label_face_orientation": "面朝向：",
        "label_m3_focus": "M3 焦点：",
        "label_view": "视图：",
        "label_nav": "相机导航：",
        "label_scale": "缩放：",
        "label_rot": "旋转：",
        "label_play": "播放动画：",
        "label_sc_count": "场景总数：",
        "label_mod_vis": "修改器显示：",
        "label_pack": "自动打包资源：",
        "label_frame": "当前帧：",
        "label_edit_mirror": "编辑镜像：",
        "label_sculpt_mirror": "雕刻镜像：",
        "label_gizmo": "操纵器：",
        "label_prop_edit": "比例编辑：",

        "pack_on": "是",
        "pack_off": "否",
        "play_yes": "是",
        "play_no": "否",
        "on": "开",
        "off": "关",
        "unknown": "未知",
        "na": "N/A",
        "visible": "显示",
        "hidden": "隐藏",
        "none": "无",
        "all_hidden": "全部隐藏",
        "not_selected": "未选中物体",
        "start_frame": "起始",

        "cam_cam": "相机",
        "cam_free": "自由",

        "coord_global": "全局",
        "coord_local": "本地",
        "coord_normal": "法线",
        "coord_gimbal": "万向",
        "coord_view": "视图",
        "coord_cursor": "3D 游标",
        "coord_parent": "父级",

        "pivot_box": "边界框中心",
        "pivot_cursor": "3D 游标",
        "pivot_indiv": "各自原点",
        "pivot_median": "中点",
        "pivot_active": "活动元素",

        "color_mat": "材质",
        "color_obj": "物体",
        "color_rnd": "随机",
        "color_vtx": "属性",
        "color_tex": "纹理",
        "color_sgl": "自定义",

        "ui_cam_nav": "相机导航状态",
        "ui_cam_name": "当前相机名称",
        "ui_cam_view": "视图类型（相机/自由）",
        "ui_coord": "变换坐标系",
        "ui_pivot": "变换轴心点",
        "ui_color_type": "物体颜色类型",
        "ui_xray": "X-Ray 开启状态",
        "ui_face_orientation": "面朝向开启状态",
        "ui_m3_focus": "M3 焦点 / 局部视图状态",
        "ui_obj_scale": "活动物体缩放比例",
        "ui_obj_rot": "活动物体旋转角度",
        "ui_play_anim": "动画播放状态",
        "ui_scene_count": "当前文件场景数量",
        "ui_mod_vis": "活动物体修改器可见性",
        "ui_pack": "自动打包资源状态",
        "ui_frame_not_start": "当前帧不是第一帧",
        "ui_edit_mirror": "编辑模式镜像状态",
        "ui_sculpt_mirror": "雕刻模式镜像状态",
        "ui_gizmo_hidden": "操纵器隐藏状态",
        "ui_proportional_edit": "比例编辑状态",

        "panel_title": "HUD 设置",
        "panel_basic": "基础设置",
        "panel_appearance": "HUD 外观设置",
        "panel_shadow": "阴影设置",
        "panel_content": "显示内容排序",
        "panel_advanced": "高级设置",

        "ui_language": "语言",
        "ui_show_hud": "启用 HUD",
        "ui_font_size": "字体大小",
        "ui_line_spacing": "行间距",
        "ui_offset_x": "X 偏移",
        "ui_offset_y": "Y 偏移",
        "ui_anchor": "锚点位置",
        "ui_font_color": "字体颜色",
        "ui_warning_color": "警示颜色",
        "ui_enable_shadow": "开启阴影",
        "ui_shadow_color": "阴影颜色",
        "ui_shadow_x": "阴影 X",
        "ui_shadow_y": "阴影 Y",
        "ui_debug_mode": "调试模式",
        "ui_refresh_interval": "HUD 刷新间隔（秒）",
        "info_refresh_interval": "建议 0.10-0.20；0 表示每帧刷新",

        "ui_display_mode": "显示模式",
        "display_always": "始终显示",
        "display_warning": "仅警示时显示",
        "display_off": "关闭",

        "anchor_top_left": "左上",
        "anchor_top_right": "右上",
        "anchor_bottom_left": "左下",
        "anchor_bottom_right": "右下",

        "btn_reset_list": "重置列表",
        "btn_reset_appearance": "重置外观",
        "btn_reset_all": "重置全部设置",

        "info_hotkey": "快捷键：Shift + F2 开关 HUD",
        "info_warning_color": "警示项将使用警示颜色显示",
        "info_category": "设置位置：3D视图 > N面板 > 视图警示",
        "info_scale_ignore": "相机 / 灯光对象的缩放已忽略，不触发缩放警示",

        "status_warning": "警示",
        "status_normal": "正常",
        "status_off": "关闭",
        "status_unknown": "未知",
    },

    "EN": {
        "label_cam": "Camera: ",
        "label_cam_none": "Camera: None",
        "label_coord": "Orient: ",
        "label_pivot": "Pivot: ",
        "label_color": "Color: ",
        "label_xray": "X-Ray: ",
        "label_face_orientation": "Face Orientation: ",
        "label_m3_focus": "M3 Focus: ",
        "label_view": "View: ",
        "label_nav": "Camera Lock: ",
        "label_scale": "Scale: ",
        "label_rot": "Rotation: ",
        "label_play": "Play Anim: ",
        "label_sc_count": "Scenes: ",
        "label_mod_vis": "Modifiers: ",
        "label_pack": "Auto Pack Resources: ",
        "label_frame": "Current Frame: ",
        "label_edit_mirror": "Edit Mirror: ",
        "label_sculpt_mirror": "Sculpt Mirror: ",
        "label_gizmo": "Gizmo: ",
        "label_prop_edit": "Proportional Editing: ",

        "pack_on": "Yes",
        "pack_off": "No",
        "play_yes": "Yes",
        "play_no": "No",
        "on": "ON",
        "off": "OFF",
        "unknown": "Unknown",
        "na": "N/A",
        "visible": "Visible",
        "hidden": "Hidden",
        "none": "None",
        "all_hidden": "All Hidden",
        "not_selected": "No Active Object",
        "start_frame": "Start",

        "cam_cam": "Camera",
        "cam_free": "Free",

        "coord_global": "Global",
        "coord_local": "Local",
        "coord_normal": "Normal",
        "coord_gimbal": "Gimbal",
        "coord_view": "View",
        "coord_cursor": "3D Cursor",
        "coord_parent": "Parent",

        "pivot_box": "Bounding Box",
        "pivot_cursor": "3D Cursor",
        "pivot_indiv": "Individual Origins",
        "pivot_median": "Median Point",
        "pivot_active": "Active Element",

        "color_mat": "Material",
        "color_obj": "Object",
        "color_rnd": "Random",
        "color_vtx": "Attribute",
        "color_tex": "Texture",
        "color_sgl": "Single",

        "ui_cam_nav": "Camera Navigation Lock",
        "ui_cam_name": "Active Camera Name",
        "ui_cam_view": "View Type (Camera / Free)",
        "ui_coord": "Transform Orientation",
        "ui_pivot": "Transform Pivot",
        "ui_color_type": "Shading Color Type",
        "ui_xray": "X-Ray Enabled State",
        "ui_face_orientation": "Face Orientation Enabled State",
        "ui_m3_focus": "M3 Focus / Local View State",
        "ui_obj_scale": "Active Object Scale",
        "ui_obj_rot": "Active Object Rotation",
        "ui_play_anim": "Animation Playing State",
        "ui_scene_count": "Scene Count",
        "ui_mod_vis": "Modifier Viewport Visibility",
        "ui_pack": "Auto Pack Resources",
        "ui_frame_not_start": "Current Frame Is Not First Frame",
        "ui_edit_mirror": "Edit Mode Mirror State",
        "ui_sculpt_mirror": "Sculpt Mode Mirror State",
        "ui_gizmo_hidden": "Gizmo Hidden State",
        "ui_proportional_edit": "Proportional Editing State",

        "panel_title": "HUD Settings",
        "panel_basic": "Basic",
        "panel_appearance": "HUD Appearance",
        "panel_shadow": "Shadow Settings",
        "panel_content": "Content Order",
        "panel_advanced": "Advanced",

        "ui_language": "Language",
        "ui_show_hud": "Enable HUD",
        "ui_font_size": "Font Size",
        "ui_line_spacing": "Line Spacing",
        "ui_offset_x": "Offset X",
        "ui_offset_y": "Offset Y",
        "ui_anchor": "Anchor",
        "ui_font_color": "Font Color",
        "ui_warning_color": "Alert Color",
        "ui_enable_shadow": "Enable Shadow",
        "ui_shadow_color": "Shadow Color",
        "ui_shadow_x": "Shadow X",
        "ui_shadow_y": "Shadow Y",
        "ui_debug_mode": "Debug Mode",
        "ui_refresh_interval": "HUD Refresh Interval (s)",
        "info_refresh_interval": "Recommended 0.10-0.20; 0 refreshes every frame",

        "ui_display_mode": "Display Mode",
        "display_always": "Always",
        "display_warning": "Warning Only",
        "display_off": "Off",

        "anchor_top_left": "Top Left",
        "anchor_top_right": "Top Right",
        "anchor_bottom_left": "Bottom Left",
        "anchor_bottom_right": "Bottom Right",

        "btn_reset_list": "Reset List",
        "btn_reset_appearance": "Reset Appearance",
        "btn_reset_all": "Reset All Settings",

        "info_hotkey": "Hotkey: Shift + F2 toggles HUD",
        "info_warning_color": "Warning items use alert color",
        "info_category": "Location: 3D View > N Panel > View Alerts",
        "info_scale_ignore": "Camera / Light object scale is ignored",

        "status_warning": "Warning",
        "status_normal": "Normal",
        "status_off": "Off",
        "status_unknown": "Unknown",
    }
}


def _resolve_trans_dict(prefs=None):
    """同步翻译缓存；语言切换时由 update_hud / register 调用。"""
    global _cached_trans
    if prefs is None:
        prefs = get_prefs()
    lang = getattr(prefs, "language", "CN")
    _cached_trans = TRANS_DATA.get(lang, TRANS_DATA["CN"])


def T(key, context=None):
    # 正常路径直接读缓存字典；register 前若缓存尚未初始化则回退 CN。
    dct = _cached_trans if _cached_trans is not None else TRANS_DATA["CN"]
    return dct.get(key, key)


# ------------------------------------------------------------------------
# 工具函数
# ------------------------------------------------------------------------

def get_prefs():
    addon = bpy.context.preferences.addons.get(__name__)
    return addon.preferences if addon else None


def debug_print(*args):
    prefs = get_prefs()
    if prefs and prefs.debug_mode:
        print("[ViewAlertsHUD]", *args)


def safe_call(func, *args, default=None, debug_label=""):
    try:
        return func(*args)
    except Exception as e:
        debug_print(f"{debug_label} failed:", repr(e))
        return default


def redraw_all_view3d(context):
    wm = context.window_manager
    for window in wm.windows:
        screen = window.screen
        if not screen:
            continue
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def invalidate_hud_cache():
    """清空 HUD 状态缓存；偏好/排序/显示模式变化时立即生效。"""
    global _hud_cache_generation
    _hud_status_cache.clear()
    _hud_cache_generation += 1


def on_load_post(*_args):
    """切换 .blend 文件后清空缓存，避免旧区域指针复用命中过期状态。"""
    invalidate_hud_cache()


def update_hud_cache_and_redraw(self, context):
    """Property update 回调：让 UIList 显示模式等变化立刻刷新 HUD。"""
    invalidate_hud_cache()
    try:
        if context and getattr(context, "window_manager", None):
            redraw_all_view3d(context)
    except Exception:
        pass


def safe_pointer(value):
    try:
        return value.as_pointer() if value else 0
    except Exception:
        return 0


def get_hud_refresh_interval(prefs):
    try:
        return max(0.0, float(getattr(prefs, "refresh_interval", _HUD_CACHE_DEFAULT_INTERVAL)))
    except Exception:
        return _HUD_CACHE_DEFAULT_INTERVAL


def rounded_vector(values, digits=4):
    try:
        return tuple(round(float(v), digits) for v in values)
    except Exception:
        return ()


def get_hud_cache_key(context, space, region):
    return (
        safe_pointer(getattr(context, "area", None)),
        safe_pointer(region),
        safe_pointer(space),
    )


def build_hud_cache_signature(context, space, prefs):
    """
    生成轻量签名。签名覆盖高频交互状态；未覆盖的状态也会按 refresh_interval 定期刷新。
    """
    scene = getattr(context, "scene", None)
    obj = getattr(context, "active_object", None) or getattr(context, "object", None)
    tool_settings = getattr(scene, "tool_settings", None) if scene else None
    camera = getattr(scene, "camera", None) if scene else None
    camera_data = getattr(camera, "data", None) if camera else None
    shading = getattr(space, "shading", None)
    overlay = getattr(space, "overlay", None)
    region_3d = getattr(space, "region_3d", None)

    modifier_state = ()
    mesh_mirror_state = ()
    if obj is not None:
        try:
            modifier_state = tuple((m.name, bool(m.show_viewport)) for m in obj.modifiers)
        except Exception:
            modifier_state = ()

        mesh = getattr(obj, "data", None) if getattr(obj, "type", None) == 'MESH' else None
        if mesh:
            mesh_mirror_state = (
                bool(getattr(mesh, "use_mirror_x", False)),
                bool(getattr(mesh, "use_mirror_y", False)),
                bool(getattr(mesh, "use_mirror_z", False)),
            )

    orientation_type = None
    try:
        orientation_type = scene.transform_orientation_slots[0].type if scene else None
    except Exception:
        orientation_type = None

    item_state = tuple((item.key, item.display_mode) for item in prefs.items)

    return (
        _hud_cache_generation,
        getattr(prefs, "language", "CN"),
        item_state,
        safe_pointer(scene),
        getattr(scene, "frame_current", None) if scene else None,
        getattr(scene, "frame_start", None) if scene else None,
        len(bpy.data.scenes),
        getattr(bpy.data, "use_autopack", None),
        bool(getattr(getattr(context, "screen", None), "is_animation_playing", False)),
        safe_pointer(camera),
        getattr(camera, "name", "") if camera else "",
        getattr(camera_data, "show_passepartout", None) if camera_data else None,
        bool(getattr(camera_data, "show_name", False)) if camera_data else False,
        getattr(context, "mode", None),
        safe_pointer(obj),
        getattr(obj, "name", "") if obj else "",
        getattr(obj, "type", "") if obj else "",
        rounded_vector(getattr(obj, "scale", ())) if obj else (),
        get_object_rotation_raw(obj) if obj else (),
        modifier_state,
        mesh_mirror_state,
        getattr(shading, "type", None) if shading else None,
        getattr(shading, "color_type", None) if shading else None,
        bool(getattr(shading, "show_xray", False)) if shading else False,
        bool(getattr(shading, "show_xray_wireframe", False)) if shading else False,
        bool(getattr(overlay, "show_face_orientation", False)) if overlay else False,
        bool(getattr(space, "show_gizmo", True)),
        bool(getattr(space, "lock_camera", False)),
        bool(getattr(space, "local_view", False)),
        getattr(region_3d, "view_perspective", None) if region_3d else None,
        orientation_type,
        getattr(tool_settings, "transform_pivot_point", None) if tool_settings else None,
        getattr(tool_settings, "use_proportional_edit", None) if tool_settings else None,
        getattr(tool_settings, "use_proportional_edit_objects", None) if tool_settings else None,
        getattr(tool_settings, "use_mesh_automerge", None) if tool_settings else None,
        getattr(tool_settings, "use_mesh_mirror_x", None) if tool_settings else None,
        getattr(tool_settings, "use_mesh_mirror_y", None) if tool_settings else None,
        getattr(tool_settings, "use_mesh_mirror_z", None) if tool_settings else None,
    )


def _prune_hud_cache(now):
    """限制缓存体积并清理长时间未命中的条目，避免旧区域指针长期驻留。"""
    if len(_hud_status_cache) <= _HUD_CACHE_MAX_ENTRIES:
        return

    stale = [
        key for key, entry in _hud_status_cache.items()
        if now - entry.get("time", 0.0) > _HUD_CACHE_PRUNE_AGE
    ]
    for key in stale:
        _hud_status_cache.pop(key, None)


def get_cached_status_lines(context, space, prefs, region):
    interval = get_hud_refresh_interval(prefs)
    if interval <= 0.0:
        return collect_status_lines(context, space, prefs)

    now = time.monotonic()
    _prune_hud_cache(now)

    key = get_hud_cache_key(context, space, region)
    signature = build_hud_cache_signature(context, space, prefs)
    cached = _hud_status_cache.get(key)

    if cached:
        same_signature = cached.get("signature") == signature
        cache_fresh = (now - cached.get("time", 0.0)) < interval
        if same_signature and cache_fresh:
            return cached.get("lines", [])

    lines = collect_status_lines(context, space, prefs)
    _hud_status_cache[key] = {
        "time": now,
        "signature": signature,
        "lines": lines,
    }
    return lines


def get_object_rotation_euler(obj):
    if not obj:
        return None

    mode = getattr(obj, "rotation_mode", 'XYZ')

    try:
        if mode == 'QUATERNION':
            return obj.rotation_quaternion.to_euler()
        elif mode == 'AXIS_ANGLE':
            return obj.matrix_basis.to_euler()
        else:
            return obj.rotation_euler
    except Exception:
        return None


def get_object_rotation_raw(obj):
    """返回旋转的原始可比较值，避免每帧做矩阵/四元数转欧拉的高开销。"""
    if not obj:
        return None

    mode = getattr(obj, "rotation_mode", 'XYZ')

    try:
        if mode == 'QUATERNION':
            return rounded_vector(obj.rotation_quaternion)
        elif mode == 'AXIS_ANGLE':
            return rounded_vector(obj.rotation_axis_angle)
        else:
            return rounded_vector(obj.rotation_euler)
    except Exception:
        return None


def get_current_view3d_space(context):
    """返回当前正在绘制的 3D View 的 active SpaceView3D。

    不直接依赖 context.space_data，是因为 draw handler 在某些情况下会拿到
    旧区域/非当前区域的 space_data，导致 X-Ray 等视图状态误报。
    """
    area = getattr(context, "area", None)
    if area and getattr(area, "type", None) == 'VIEW_3D':
        active_space = getattr(getattr(area, "spaces", None), "active", None)
        if active_space and getattr(active_space, "type", None) == 'VIEW_3D':
            return active_space

        for sp in getattr(area, "spaces", []):
            if getattr(sp, "type", None) == 'VIEW_3D':
                return sp

    space = getattr(context, "space_data", None)
    if space and getattr(space, "type", None) == 'VIEW_3D':
        return space

    return None


def is_scale_ignored_object(obj):
    """相机和灯光对象的缩放通常不是建模风险，默认忽略。"""
    return bool(obj and obj.type in {'CAMERA', 'LIGHT'})


def draw_foldout_header(layout, prefs, prop_name, title, icon):
    """绘制可折叠分组标题，返回 box 和是否展开。"""
    box = layout.box()
    expanded = bool(getattr(prefs, prop_name, True))

    row = box.row(align=True)
    op = row.operator(
        "viewstatushud.toggle_group",
        text="",
        icon='TRIA_DOWN' if expanded else 'TRIA_RIGHT',
        emboss=False
    )
    op.group_name = prop_name
    row.label(text=title, icon=icon)

    return box, expanded


# ------------------------------------------------------------------------
# 状态读取函数
# ------------------------------------------------------------------------

def get_active_camera_name(context, space):
    cam = context.scene.camera
    if cam:
        return f"{T('label_cam', context)}{cam.name}"
    return T('label_cam_none', context)


def get_coord_system(context, space):
    orient_slot = None
    ori = "GLOBAL"

    try:
        orient_slot = context.scene.transform_orientation_slots[0]
        ori = orient_slot.type
    except Exception:
        pass

    key_map = {
        "GLOBAL": "coord_global",
        "LOCAL": "coord_local",
        "NORMAL": "coord_normal",
        "GIMBAL": "coord_gimbal",
        "VIEW": "coord_view",
        "CURSOR": "coord_cursor",
        "PARENT": "coord_parent",
    }

    val_key = key_map.get(ori)
    if val_key:
        val_text = T(val_key, context)
    else:
        custom_ori = getattr(orient_slot, "custom_orientation", None) if orient_slot else None
        val_text = custom_ori.name if custom_ori else ori

    return f"{T('label_coord', context)}{val_text}"


def get_pivot(context, space):
    pivot = context.tool_settings.transform_pivot_point
    key_map = {
        "BOUNDING_BOX_CENTER": "pivot_box",
        "CURSOR": "pivot_cursor",
        "INDIVIDUAL_ORIGINS": "pivot_indiv",
        "MEDIAN_POINT": "pivot_median",
        "ACTIVE_ELEMENT": "pivot_active",
    }
    return f"{T('label_pivot', context)}{T(key_map.get(pivot, pivot), context)}"


def get_shading_color_type(context, space):
    shading = getattr(space, "shading", None)
    if not shading or getattr(shading, "type", None) != 'SOLID':
        return None

    c_type = shading.color_type
    key_map = {
        "MATERIAL": "color_mat",
        "OBJECT": "color_obj",
        "RANDOM": "color_rnd",
        "VERTEX": "color_vtx",
        "TEXTURE": "color_tex",
        "SINGLE": "color_sgl",
    }
    return f"{T('label_color', context)}{T(key_map.get(c_type, c_type), context)}"


def get_xray_status(context, space):
    state = T('on', context) if check_xray_enabled(context, space) else T('off', context)
    return f"{T('label_xray', context)}{state}"


def get_face_orientation_status(context, space):
    overlay = getattr(space, "overlay", None)
    state = T('on', context) if getattr(overlay, "show_face_orientation", False) else T('off', context)
    return f"{T('label_face_orientation', context)}{state}"


def get_m3_focus_status(context, space):
    state = T('on', context) if check_m3_focus(context, space) else T('off', context)
    return f"{T('label_m3_focus', context)}{state}"


def get_camera_view(context, space):
    region_3d = getattr(space, "region_3d", None)
    if not region_3d:
        return None
    val = T('cam_cam', context) if region_3d.view_perspective == 'CAMERA' else T('cam_free', context)
    return f"{T('label_view', context)}{val}"


def get_camera_nav(context, space):
    lock = getattr(space, "lock_camera", False)
    state = T('on', context) if lock else T('off', context)
    return f"{T('label_nav', context)}{state}"


def get_obj_scale(context, space):
    obj = context.active_object
    if not obj:
        return f"{T('label_scale', context)}{T('not_selected', context)}"

    if is_scale_ignored_object(obj):
        # 即使该项设置为“始终显示”，相机/灯光缩放也不显示，避免无意义信息干扰。
        return None

    s = obj.scale
    txt = f"X:{s.x:.3g}, Y:{s.y:.3g}, Z:{s.z:.3g}"
    return f"{T('label_scale', context)}{txt}"


def get_obj_rotation(context, space):
    obj = context.active_object
    if not obj:
        return f"{T('label_rot', context)}{T('not_selected', context)}"

    rot = get_object_rotation_euler(obj)
    if rot is None:
        return f"{T('label_rot', context)}{T('unknown', context)}"

    d_x = math.degrees(rot.x)
    d_y = math.degrees(rot.y)
    d_z = math.degrees(rot.z)
    txt = f"X:{d_x:.1f}°, Y:{d_y:.1f}°, Z:{d_z:.1f}°"
    return f"{T('label_rot', context)}{txt}"


def get_play_anim(context, space):
    is_playing = context.screen.is_animation_playing if context.screen else False
    state = T('play_yes', context) if is_playing else T('play_no', context)
    return f"{T('label_play', context)}{state}"


def get_scene_count(context, space):
    count = len(bpy.data.scenes)
    return f"{T('label_sc_count', context)}{count}"


def get_mod_vis(context, space):
    obj = context.active_object
    if not obj or not hasattr(obj, "modifiers"):
        return f"{T('label_mod_vis', context)}{T('na', context)}"

    total = len(obj.modifiers)
    if total == 0:
        return f"{T('label_mod_vis', context)}{T('none', context)}"

    visible_count = sum(1 for m in obj.modifiers if m.show_viewport)

    if visible_count == 0:
        state = T('all_hidden', context)
    else:
        state = f"{visible_count}/{total}"

    return f"{T('label_mod_vis', context)}{state}"


def get_auto_pack_status(context, space):
    is_pack = bpy.data.use_autopack
    state = T('pack_on', context) if is_pack else T('pack_off', context)
    return f"{T('label_pack', context)}{state}"


def _format_axes(axes):
    return "/".join(axes)


def _get_edit_mirror_axes(context):
    obj = context.active_object
    if not obj or obj.type != 'MESH':
        return []

    mesh = getattr(obj, "data", None)
    if not mesh:
        return []

    axes = []
    if getattr(mesh, "use_mirror_x", False):
        axes.append("X")
    if getattr(mesh, "use_mirror_y", False):
        axes.append("Y")
    if getattr(mesh, "use_mirror_z", False):
        axes.append("Z")
    return axes


def _get_sculpt_mirror_axes(context):
    obj = context.active_object
    mesh = getattr(obj, "data", None) if obj and obj.type == 'MESH' else None

    # Blender 2.8+ / 3.x / 4.x / 5.x 的雕刻对称按钮通常写在活动 Mesh 上，
    # 也就是 mesh.use_mirror_x/y/z。原先只读 ToolSettings.sculpt.use_symmetry_*，
    # 容易出现 HUD 与雕刻模式顶部/侧栏的镜像开关不一致。
    axes = []
    mesh_has_mirror_flags = False
    if mesh:
        for attr, axis in (
            ("use_mirror_x", "X"),
            ("use_mirror_y", "Y"),
            ("use_mirror_z", "Z"),
        ):
            if hasattr(mesh, attr):
                mesh_has_mirror_flags = True
                if getattr(mesh, attr, False):
                    axes.append(axis)

    if mesh_has_mirror_flags:
        return axes

    # 兼容非常旧的 Blender：早期 Sculpt 类型也暴露过 use_symmetry_x/y/z。
    sculpt = getattr(context.tool_settings, "sculpt", None)
    if not sculpt:
        return []

    if getattr(sculpt, "use_symmetry_x", False):
        axes.append("X")
    if getattr(sculpt, "use_symmetry_y", False):
        axes.append("Y")
    if getattr(sculpt, "use_symmetry_z", False):
        axes.append("Z")
    return axes




def get_current_frame_status(context, space):
    scene = context.scene
    return f"{T('label_frame', context)}{scene.frame_current} / {T('start_frame', context)} {scene.frame_start}"


def get_edit_mirror_status(context, space):
    axes = _get_edit_mirror_axes(context)
    state = _format_axes(axes) if axes else T('off', context)
    return f"{T('label_edit_mirror', context)}{state}"


def get_sculpt_mirror_status(context, space):
    axes = _get_sculpt_mirror_axes(context)
    state = _format_axes(axes) if axes else T('off', context)
    return f"{T('label_sculpt_mirror', context)}{state}"


def get_gizmo_status(context, space):
    state = T('visible', context) if getattr(space, "show_gizmo", True) else T('hidden', context)
    return f"{T('label_gizmo', context)}{state}"


def get_proportional_edit_status(context, space):
    state = T('on', context) if check_proportional_edit(context, space) else T('off', context)
    return f"{T('label_prop_edit', context)}{state}"


# ------------------------------------------------------------------------
# 警示判断函数
# ------------------------------------------------------------------------

def check_scale(context, space):
    obj = context.active_object
    if not obj:
        return False

    # 重点优化：相机和灯光对象的缩放不作为建模风险警示。
    if is_scale_ignored_object(obj):
        return False

    s = obj.scale
    return (
        abs(s.x - 1.0) > 0.0001 or
        abs(s.y - 1.0) > 0.0001 or
        abs(s.z - 1.0) > 0.0001
    )


def check_rotation(context, space):
    obj = context.active_object
    if not obj:
        return False

    r = get_object_rotation_euler(obj)
    if r is None:
        return False

    return (
        abs(r.x) > 0.0001 or
        abs(r.y) > 0.0001 or
        abs(r.z) > 0.0001
    )


def check_coord(context, space):
    try:
        return context.scene.transform_orientation_slots[0].type != 'GLOBAL'
    except Exception:
        return False


def check_shading_color_not_material(context, space):
    shading = getattr(space, "shading", None)
    if not shading or getattr(shading, "type", None) != 'SOLID':
        return False

    return getattr(shading, "color_type", 'MATERIAL') != 'MATERIAL'


def check_xray_enabled(context, space):
    shading = getattr(space, "shading", None)
    if not shading:
        return False

    shading_type = getattr(shading, "type", None)

    # 关键修正：
    # Blender 会分别记住实体模式 show_xray 和线框模式 show_xray_wireframe。
    # 如果直接 OR 两个值，切到实体/透视视图时可能会被线框模式的保留状态误判为开启。
    # 因此这里严格按当前视图的当前着色模式读取对应开关。
    if shading_type == 'SOLID':
        return bool(getattr(shading, "show_xray", False))

    if shading_type == 'WIREFRAME':
        return bool(getattr(shading, "show_xray_wireframe", False))

    # 材质预览 / 渲染预览等模式不显示 X-Ray 警示。
    return False


def check_face_orientation_enabled(context, space):
    overlay = getattr(space, "overlay", None)
    return bool(getattr(overlay, "show_face_orientation", False)) if overlay else False


def check_m3_focus(context, space):
    # M3 Focus 默认调用 Blender Local View。插件最低支持 Blender 3.0，
    # SpaceView3D.local_view 已直接反映局部视图状态，无需逐物体回退扫描。
    return bool(getattr(space, "local_view", False))


def check_pivot(context, space):
    try:
        return context.tool_settings.transform_pivot_point != 'BOUNDING_BOX_CENTER'
    except Exception:
        return False


def check_cam_nav(context, space):
    return getattr(space, "lock_camera", False)


def check_scene_count(context, space):
    return len(bpy.data.scenes) > 1


def check_pack(context, space):
    return bpy.data.use_autopack


def check_cam_view(context, space):
    region_3d = getattr(space, "region_3d", None)
    return bool(region_3d and region_3d.view_perspective == 'CAMERA')


def check_mod_vis(context, space):
    obj = context.active_object
    if obj and hasattr(obj, "modifiers") and len(obj.modifiers) > 0:
        return not any(m.show_viewport for m in obj.modifiers)
    return False


def check_play_anim(context, space):
    return context.screen.is_animation_playing if context.screen else False




def check_frame_not_start(context, space):
    scene = context.scene
    return scene.frame_current != scene.frame_start


def check_edit_mirror(context, space):
    return context.mode == 'EDIT_MESH' and bool(_get_edit_mirror_axes(context))


def check_sculpt_mirror(context, space):
    return context.mode == 'SCULPT' and bool(_get_sculpt_mirror_axes(context))


def check_gizmo_hidden(context, space):
    return not getattr(space, "show_gizmo", True)


def check_proportional_edit(context, space):
    ts = context.tool_settings
    return bool(
        getattr(ts, "use_proportional_edit", False) or
        getattr(ts, "use_proportional_edit_objects", False)
    )


# ------------------------------------------------------------------------
# HUD 项目定义（默认全部仅警示时显示）
# ------------------------------------------------------------------------

HUD_ITEMS = {
    "cam_nav": {
        "label_key": "ui_cam_nav",
        "default_mode": "WARNING_ONLY",
        "get": get_camera_nav,
        "check": check_cam_nav,
    },
    "cam_name": {
        "label_key": "ui_cam_name",
        "default_mode": "WARNING_ONLY",
        "get": get_active_camera_name,
        # 仅当当前 3D 视图处于相机视图时显示相机名称
        "check": check_cam_view,
    },
    "cam_view": {
        "label_key": "ui_cam_view",
        "default_mode": "WARNING_ONLY",
        "get": get_camera_view,
        "check": check_cam_view,
    },
    "coord": {
        "label_key": "ui_coord",
        "default_mode": "WARNING_ONLY",
        "get": get_coord_system,
        "check": check_coord,
    },
    "pivot": {
        "label_key": "ui_pivot",
        "default_mode": "WARNING_ONLY",
        "get": get_pivot,
        "check": check_pivot,
    },
    "color_type": {
        "label_key": "ui_color_type",
        "default_mode": "WARNING_ONLY",
        "get": get_shading_color_type,
        "check": check_shading_color_not_material,
    },
    "xray": {
        "label_key": "ui_xray",
        "default_mode": "WARNING_ONLY",
        "get": get_xray_status,
        "check": check_xray_enabled,
    },
    "face_orientation": {
        "label_key": "ui_face_orientation",
        "default_mode": "WARNING_ONLY",
        "get": get_face_orientation_status,
        "check": check_face_orientation_enabled,
    },
    "m3_focus": {
        "label_key": "ui_m3_focus",
        "default_mode": "WARNING_ONLY",
        "get": get_m3_focus_status,
        "check": check_m3_focus,
    },
    "scene_count": {
        "label_key": "ui_scene_count",
        "default_mode": "WARNING_ONLY",
        "get": get_scene_count,
        "check": check_scene_count,
    },
    "mod_vis": {
        "label_key": "ui_mod_vis",
        "default_mode": "WARNING_ONLY",
        "get": get_mod_vis,
        "check": check_mod_vis,
    },
    "pack": {
        "label_key": "ui_pack",
        "default_mode": "WARNING_ONLY",
        "get": get_auto_pack_status,
        "check": check_pack,
    },
    "play_anim": {
        "label_key": "ui_play_anim",
        "default_mode": "WARNING_ONLY",
        "get": get_play_anim,
        "check": check_play_anim,
    },
    "frame_not_start": {
        "label_key": "ui_frame_not_start",
        "default_mode": "WARNING_ONLY",
        "get": get_current_frame_status,
        "check": check_frame_not_start,
    },
    "edit_mirror": {
        "label_key": "ui_edit_mirror",
        "default_mode": "WARNING_ONLY",
        "get": get_edit_mirror_status,
        "check": check_edit_mirror,
    },
    "sculpt_mirror": {
        "label_key": "ui_sculpt_mirror",
        "default_mode": "WARNING_ONLY",
        "get": get_sculpt_mirror_status,
        "check": check_sculpt_mirror,
    },
    "gizmo_hidden": {
        "label_key": "ui_gizmo_hidden",
        "default_mode": "WARNING_ONLY",
        "get": get_gizmo_status,
        "check": check_gizmo_hidden,
    },
    "proportional_edit": {
        "label_key": "ui_proportional_edit",
        "default_mode": "WARNING_ONLY",
        "get": get_proportional_edit_status,
        "check": check_proportional_edit,
    },
    "obj_scale": {
        "label_key": "ui_obj_scale",
        "default_mode": "WARNING_ONLY",
        "get": get_obj_scale,
        "check": check_scale,
    },
    "obj_rot": {
        "label_key": "ui_obj_rot",
        "default_mode": "WARNING_ONLY",
        "get": get_obj_rotation,
        "check": check_rotation,
    },
}

DEFAULT_ITEM_ORDER = [
    "cam_nav",
    "cam_name",
    "cam_view",
    "coord",
    "pivot",
    "color_type",
    "xray",
    "face_orientation",
    "m3_focus",
    "scene_count",
    "mod_vis",
    "pack",
    "play_anim",
    "frame_not_start",
    "edit_mirror",
    "sculpt_mirror",
    "gizmo_hidden",
    "proportional_edit",
    "obj_scale",
    "obj_rot",
]

# ------------------------------------------------------------------------
# Collection / UI List
# ------------------------------------------------------------------------

DISPLAY_MODE_ITEMS = [
    ('ALWAYS', "Always", ""),
    ('WARNING_ONLY', "Warning Only", ""),
    ('OFF', "Off", ""),
]

# Blender 对 AddonPreferences 中的动态 EnumProperty + 字符串 default 在部分版本里会注册失败。
# 这里改回静态枚举，避免安装时报 anchor EnumProperty could not register。
ANCHOR_ITEMS = [
    ('TOP_LEFT', "左上 / Top Left", ""),
    ('TOP_RIGHT', "右上 / Top Right", ""),
    ('BOTTOM_LEFT', "左下 / Bottom Left", ""),
    ('BOTTOM_RIGHT', "右下 / Bottom Right", ""),
]


class VIEWSTATUSHUD_Item(PropertyGroup):
    key: StringProperty()
    display_mode: EnumProperty(
        name="Display Mode",
        items=DISPLAY_MODE_ITEMS,
        default='WARNING_ONLY',
        update=update_hud_cache_and_redraw,
    )


class VIEWSTATUSHUD_UL_items(UIList):
    """列表中直接显示当前警示状态。"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        cfg = HUD_ITEMS.get(item.key, {})
        label_key = cfg.get("label_key", item.key)

        row = layout.row(align=True)

        display_mode = getattr(item, "display_mode", 'WARNING_ONLY')
        is_off = display_mode == 'OFF'
        status_text = T("status_unknown", context)
        status_icon = 'QUESTION'

        if is_off:
            status_text = T("status_off", context)
            status_icon = 'HIDE_ON'
        else:
            space = get_current_view3d_space(context)
            check_func = cfg.get("check")
            if space and check_func:
                is_warning = safe_call(
                    check_func,
                    context,
                    space,
                    default=False,
                    debug_label=f"UIList.{item.key}.check"
                )
                status_text = T("status_warning", context) if is_warning else T("status_normal", context)
                status_icon = 'ERROR' if is_warning else 'CHECKMARK'
            else:
                status_text = T("status_normal", context)
                status_icon = 'CHECKMARK'

        row.label(text="", icon=status_icon)

        name_col = row.column()
        name_col.scale_x = 1.25
        name_col.label(text=T(label_key, context))

        mode_text_map = {
            'ALWAYS': T("display_always", context),
            'WARNING_ONLY': T("display_warning", context),
            'OFF': T("display_off", context),
        }
        row.label(text=mode_text_map.get(display_mode, display_mode))
        row.label(text=status_text)


# ------------------------------------------------------------------------
# Preferences
# ------------------------------------------------------------------------

class VIEWSTATUSHUD_AddonPreferences(AddonPreferences):
    bl_idname = __name__

    def update_hud(self, context):
        _resolve_trans_dict(self)
        invalidate_hud_cache()
        redraw_all_view3d(context)

    language: EnumProperty(
        name="Language",
        items=[('CN', "中文 (Chinese)", ""), ('EN', "English", "")],
        default='CN',
        update=update_hud
    )

    show_hud: BoolProperty(
        name="Enable HUD",
        default=True,
        update=update_hud
    )

    font_size: IntProperty(
        name="Font Size",
        default=20,
        min=8,
        max=60,
        update=update_hud
    )

    line_spacing: IntProperty(
        name="Line Spacing",
        default=15,
        min=0,
        max=50,
        update=update_hud
    )

    offset_x: IntProperty(
        name="Offset X",
        default=40,
        min=0,
        max=2000,
        update=update_hud
    )

    offset_y: IntProperty(
        name="Offset Y",
        default=80,
        min=0,
        max=2000,
        update=update_hud
    )

    anchor: EnumProperty(
        name="Anchor",
        items=ANCHOR_ITEMS,
        default='BOTTOM_LEFT',
        update=update_hud
    )

    font_color: FloatVectorProperty(
        name="Font Color",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
        update=update_hud
    )

    warning_color: FloatVectorProperty(
        name="Alert Color",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 0.35, 0.35, 1.0),
        update=update_hud
    )

    enable_shadow: BoolProperty(
        name="Enable Shadow",
        default=True,
        update=update_hud
    )

    shadow_color: FloatVectorProperty(
        name="Shadow Color",
        subtype='COLOR',
        size=4,
        min=0.0,
        max=1.0,
        default=(0.0, 0.0, 0.0, 0.5),
        update=update_hud
    )

    shadow_offset_x: IntProperty(
        name="Shadow X",
        default=0,
        min=-10,
        max=10,
        update=update_hud
    )

    shadow_offset_y: IntProperty(
        name="Shadow Y",
        default=-1,
        min=-10,
        max=10,
        update=update_hud
    )

    refresh_interval: FloatProperty(
        name="HUD Refresh Interval",
        description="Throttle expensive HUD status collection; 0 refreshes every frame",
        default=_HUD_CACHE_DEFAULT_INTERVAL,
        min=0.0,
        max=1.0,
        precision=2,
        update=update_hud
    )

    debug_mode: BoolProperty(
        name="Debug Mode",
        default=False,
        update=update_hud
    )

    # N 面板折叠分组状态
    group_basic: BoolProperty(default=True)
    group_appearance: BoolProperty(default=True)
    group_shadow: BoolProperty(default=False)
    group_content: BoolProperty(default=True)
    group_advanced: BoolProperty(default=False)

    items: CollectionProperty(type=VIEWSTATUSHUD_Item)
    active_index: IntProperty(default=11)

    def ensure_items(self, force_reset=False):
        if force_reset:
            self.items.clear()
        else:
            valid_keys = set(HUD_ITEMS.keys())
            for idx in range(len(self.items) - 1, -1, -1):
                if self.items[idx].key not in valid_keys:
                    self.items.remove(idx)

        existing_keys = {item.key for item in self.items}

        for key in DEFAULT_ITEM_ORDER:
            if not force_reset and key in existing_keys:
                continue

            cfg = HUD_ITEMS.get(key)
            if not cfg:
                continue

            # 按 DEFAULT_ITEM_ORDER 的相对位置插入新增项，避免新增项目全部堆到列表末尾。
            insert_index = len(self.items)
            if not force_reset:
                target_order = DEFAULT_ITEM_ORDER.index(key)
                for i, existing_item in enumerate(self.items):
                    try:
                        if DEFAULT_ITEM_ORDER.index(existing_item.key) > target_order:
                            insert_index = i
                            break
                    except ValueError:
                        continue

            item = self.items.add()
            item.key = key
            item.display_mode = cfg.get("default_mode", "WARNING_ONLY")

            if insert_index < len(self.items) - 1:
                self.items.move(len(self.items) - 1, insert_index)

        if len(self.items) > 0:
            if force_reset:
                self.active_index = min(11, len(self.items) - 1)
            else:
                self.active_index = min(self.active_index, len(self.items) - 1)

    def reset_appearance(self):
        self.show_hud = True
        self.font_size = 20
        self.line_spacing = 15
        self.offset_x = 40
        self.offset_y = 80
        self.anchor = 'BOTTOM_LEFT'
        self.font_color = (1.0, 1.0, 1.0, 1.0)
        self.warning_color = (1.0, 0.35, 0.35, 1.0)
        self.enable_shadow = True
        self.shadow_color = (0.0, 0.0, 0.0, 0.5)
        self.shadow_offset_x = 0
        self.shadow_offset_y = -1
        self.refresh_interval = _HUD_CACHE_DEFAULT_INTERVAL

    def draw(self, context):
        layout = self.layout
        layout.label(text=T("info_category", context), icon='INFO')
        layout.label(text=T("info_scale_ignore", context), icon='INFO')


# ------------------------------------------------------------------------
# 主逻辑
# ------------------------------------------------------------------------

def collect_status_lines(context, space, prefs):
    lines = []

    # 相机视图过滤：
    # 只要当前 3D 视图处于相机视图，就只允许显示下面这些项目。
    # 按当前需求：物体颜色类型在相机视图也生效；面朝向不在相机视图下放行。
    # 其他项目即使触发警示、设置为“始终显示”，也不会显示。
    camera_view_allowed_keys = {"cam_name", "cam_nav", "cam_view", "color_type"}
    in_camera_view = check_cam_view(context, space)

    for item in prefs.items:
        if in_camera_view and item.key not in camera_view_allowed_keys:
            continue

        cfg = HUD_ITEMS.get(item.key)
        if not cfg:
            continue

        display_mode = item.display_mode
        if display_mode == 'OFF':
            continue

        check_func = cfg.get("check")
        is_warning = safe_call(
            check_func, context, space,
            default=False,
            debug_label=f"{item.key}.check"
        ) if check_func else False

        if display_mode == 'WARNING_ONLY' and not is_warning:
            continue

        get_func = cfg.get("get")
        text = safe_call(
            get_func, context, space,
            default=None,
            debug_label=f"{item.key}.get"
        ) if get_func else None

        if not text:
            continue

        color = tuple(prefs.warning_color if is_warning else prefs.font_color)
        lines.append({
            "key": item.key,
            "text": text,
            "color": color,
        })

    return lines


def get_anchor_base(region, prefs, total_height):
    anchor = prefs.anchor

    if anchor == 'TOP_LEFT':
        return prefs.offset_x, region.height - prefs.offset_y, -1
    elif anchor == 'TOP_RIGHT':
        return region.width - prefs.offset_x, region.height - prefs.offset_y, -1
    elif anchor == 'BOTTOM_LEFT':
        return prefs.offset_x, prefs.offset_y + total_height, -1
    elif anchor == 'BOTTOM_RIGHT':
        return region.width - prefs.offset_x, prefs.offset_y + total_height, -1

    return prefs.offset_x, region.height - prefs.offset_y, -1


def draw_hud_lines(lines_data, prefs, region):
    font_id = 0
    blf.size(font_id, prefs.font_size)

    if prefs.enable_shadow:
        blf.enable(font_id, blf.SHADOW)
        blf.shadow(font_id, 3, *prefs.shadow_color)
        blf.shadow_offset(font_id, prefs.shadow_offset_x, prefs.shadow_offset_y)
    else:
        blf.disable(font_id, blf.SHADOW)

    line_step = prefs.font_size + prefs.line_spacing
    total_height = len(lines_data) * line_step

    base_x, base_y, direction = get_anchor_base(region, prefs, total_height)
    right_align = prefs.anchor in {'TOP_RIGHT', 'BOTTOM_RIGHT'}

    for i, line in enumerate(lines_data):
        text = line["text"]
        color = line["color"]

        draw_y = base_y + direction * (i * line_step)

        if right_align:
            text_width, _ = blf.dimensions(font_id, text)
            draw_x = base_x - text_width
        else:
            draw_x = base_x

        blf.position(font_id, draw_x, draw_y, 0)
        blf.color(font_id, *color)
        blf.draw(font_id, text)

    blf.disable(font_id, blf.SHADOW)


def draw_viewstatus_hud():
    try:
        prefs = get_prefs()
        if not prefs or not prefs.show_hud:
            return

        context = bpy.context
        area = context.area
        region = context.region
        space = get_current_view3d_space(context)

        if not area or area.type != 'VIEW_3D':
            return
        if not region or region.type != 'WINDOW':
            return
        if not space:
            return

        if len(prefs.items) == 0:
            prefs.ensure_items()

        lines_data = get_cached_status_lines(context, space, prefs, region)
        if not lines_data:
            return

        draw_hud_lines(lines_data, prefs, region)

    except Exception as e:
        debug_print("draw_viewstatus_hud failed:", repr(e))


# ------------------------------------------------------------------------
# Operators
# ------------------------------------------------------------------------

class VIEWSTATUSHUD_OT_reset_items(Operator):
    bl_idname = "viewstatushud.reset_items"
    bl_label = "Reset List"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        prefs = get_prefs()
        if prefs:
            prefs.ensure_items(force_reset=True)
            invalidate_hud_cache()
            redraw_all_view3d(context)
        return {'FINISHED'}


class VIEWSTATUSHUD_OT_reset_appearance(Operator):
    bl_idname = "viewstatushud.reset_appearance"
    bl_label = "Reset Appearance"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        prefs = get_prefs()
        if prefs:
            prefs.reset_appearance()
            invalidate_hud_cache()
            redraw_all_view3d(context)
        return {'FINISHED'}


class VIEWSTATUSHUD_OT_reset_all(Operator):
    bl_idname = "viewstatushud.reset_all"
    bl_label = "Reset All"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        prefs = get_prefs()
        if prefs:
            prefs.reset_appearance()
            prefs.ensure_items(force_reset=True)
            invalidate_hud_cache()
            redraw_all_view3d(context)
        return {'FINISHED'}


class VIEWSTATUSHUD_OT_move_item(Operator):
    bl_idname = "viewstatushud.move_item"
    bl_label = "Move Item"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        items=[
            ('UP', "Up", ""),
            ('DOWN', "Down", ""),
        ]
    )

    def execute(self, context):
        prefs = get_prefs()
        if not prefs:
            return {'CANCELLED'}

        items = prefs.items
        idx = prefs.active_index
        new_idx = idx - 1 if self.direction == 'UP' else idx + 1

        if 0 <= idx < len(items) and 0 <= new_idx < len(items):
            items.move(idx, new_idx)
            prefs.active_index = new_idx
            invalidate_hud_cache()
            redraw_all_view3d(context)

        return {'FINISHED'}


class VIEWSTATUSHUD_OT_toggle_hud(Operator):
    bl_idname = "view3d.viewstatushud_toggle"
    bl_label = "Toggle View Alerts HUD"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        prefs = get_prefs()
        if prefs:
            prefs.show_hud = not prefs.show_hud
            invalidate_hud_cache()
            redraw_all_view3d(context)
        return {'FINISHED'}



class VIEWSTATUSHUD_OT_toggle_group(Operator):
    bl_idname = "viewstatushud.toggle_group"
    bl_label = "Toggle HUD Settings Group"
    bl_options = {'INTERNAL'}

    group_name: StringProperty()

    def execute(self, context):
        prefs = get_prefs()
        if not prefs or not self.group_name:
            return {'CANCELLED'}

        if hasattr(prefs, self.group_name):
            current = bool(getattr(prefs, self.group_name))
            setattr(prefs, self.group_name, not current)
            redraw_all_view3d(context)
            return {'FINISHED'}

        return {'CANCELLED'}


# ------------------------------------------------------------------------
# 面板
# ------------------------------------------------------------------------

class VIEWSTATUSHUD_PT_panel(Panel):
    bl_label = "视图警示"
    bl_idname = "VIEW3D_PT_view_status_hud"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "视图警示"

    def draw(self, context):
        prefs = get_prefs()
        if not prefs:
            return

        if len(prefs.items) == 0:
            prefs.ensure_items()

        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False

        # 基础设置
        box, expanded = draw_foldout_header(
            layout,
            prefs,
            "group_basic",
            T("panel_basic", context),
            'PREFERENCES'
        )
        if expanded:
            row = box.row(align=True)
            row.prop(prefs, "language", expand=True)

            box.prop(prefs, "show_hud", text=T("ui_show_hud", context))
            box.label(text=T("info_hotkey", context), icon='EVENT_F2')
            box.label(text=T("info_warning_color", context), icon='INFO')
            box.label(text=T("info_scale_ignore", context), icon='INFO')

        # 外观设置
        box, expanded = draw_foldout_header(
            layout,
            prefs,
            "group_appearance",
            T("panel_appearance", context),
            'COLOR'
        )
        if expanded:
            col = box.column(align=True)
            col.prop(prefs, "font_size", text=T("ui_font_size", context))
            col.prop(prefs, "line_spacing", text=T("ui_line_spacing", context))
            col.prop(prefs, "anchor", text=T("ui_anchor", context))
            col.prop(prefs, "offset_x", text=T("ui_offset_x", context))
            col.prop(prefs, "offset_y", text=T("ui_offset_y", context))
            col.prop(prefs, "font_color", text=T("ui_font_color", context))
            col.prop(prefs, "warning_color", text=T("ui_warning_color", context))

        # 阴影设置
        box, expanded = draw_foldout_header(
            layout,
            prefs,
            "group_shadow",
            T("panel_shadow", context),
            'SHADING_RENDERED'
        )
        if expanded:
            box.prop(prefs, "enable_shadow", text=T("ui_enable_shadow", context))

            sub = box.column(align=True)
            sub.active = prefs.enable_shadow
            sub.prop(prefs, "shadow_color", text=T("ui_shadow_color", context))
            sub.prop(prefs, "shadow_offset_x", text=T("ui_shadow_x", context))
            sub.prop(prefs, "shadow_offset_y", text=T("ui_shadow_y", context))

        # 显示内容排序
        box, expanded = draw_foldout_header(
            layout,
            prefs,
            "group_content",
            T("panel_content", context),
            'ALIGN_TOP'
        )
        if expanded:
            row = box.row()
            row.template_list(
                "VIEWSTATUSHUD_UL_items", "",
                prefs, "items",
                prefs, "active_index",
                rows=12
            )

            col_btns = row.column(align=True)
            col_btns.operator("viewstatushud.move_item", icon='TRIA_UP', text="").direction = 'UP'
            col_btns.operator("viewstatushud.move_item", icon='TRIA_DOWN', text="").direction = 'DOWN'

            if 0 <= prefs.active_index < len(prefs.items):
                active_item = prefs.items[prefs.active_index]
                box.separator()
                box.prop(active_item, "display_mode", text=T("ui_display_mode", context))

            row = box.row(align=True)
            row.operator("viewstatushud.reset_items", text=T("btn_reset_list", context), icon='FILE_REFRESH')

        # 高级设置
        box, expanded = draw_foldout_header(
            layout,
            prefs,
            "group_advanced",
            T("panel_advanced", context),
            'TOOL_SETTINGS'
        )
        if expanded:
            box.prop(prefs, "refresh_interval", text=T("ui_refresh_interval", context))
            box.label(text=T("info_refresh_interval", context), icon='TIME')
            box.prop(prefs, "debug_mode", text=T("ui_debug_mode", context))

            row = box.row(align=True)
            row.operator("viewstatushud.reset_appearance", text=T("btn_reset_appearance", context), icon='LOOP_BACK')
            row.operator("viewstatushud.reset_all", text=T("btn_reset_all", context), icon='RECOVER_LAST')


# ------------------------------------------------------------------------
# 注册
# ------------------------------------------------------------------------

classes = (
    VIEWSTATUSHUD_Item,
    VIEWSTATUSHUD_UL_items,
    VIEWSTATUSHUD_AddonPreferences,
    VIEWSTATUSHUD_OT_reset_items,
    VIEWSTATUSHUD_OT_reset_appearance,
    VIEWSTATUSHUD_OT_reset_all,
    VIEWSTATUSHUD_OT_move_item,
    VIEWSTATUSHUD_OT_toggle_hud,
    VIEWSTATUSHUD_OT_toggle_group,
    VIEWSTATUSHUD_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    prefs = get_prefs()
    if prefs:
        prefs.ensure_items()
    _resolve_trans_dict(prefs)

    global _viewstatus_handle
    if _viewstatus_handle is None:
        _viewstatus_handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_viewstatus_hud, (), 'WINDOW', 'POST_PIXEL'
        )

    bpy.app.handlers.load_post.append(on_load_post)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.get("3D View")
        if km is None:
            km = kc.keymaps.new(name="3D View", space_type='VIEW_3D')
        kmi = km.keymap_items.new(
            "view3d.viewstatushud_toggle",
            'F2',
            'PRESS',
            shift=True
        )
        addon_keymaps.append((km, kmi))


def unregister():
    invalidate_hud_cache()

    try:
        bpy.app.handlers.load_post.remove(on_load_post)
    except ValueError:
        pass

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    global _viewstatus_handle
    if _viewstatus_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_viewstatus_handle, 'WINDOW')
        _viewstatus_handle = None

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    try:
        unregister()
    except Exception:
        pass
    register()

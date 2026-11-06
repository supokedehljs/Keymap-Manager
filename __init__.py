bl_info = {
    "name": "Keymap Manager",
    "author": "OpenAI",
    "version": (0, 1, 1),
    "blender": (5, 3, 0),
    "location": "Edit > Preferences > Keymap",
    "description": "Show only shortcuts that you have changed, disabled, deleted, or added.",
    "category": "User Interface",
}

import bpy
from bpy.props import BoolProperty


_ORIGINAL_KEYMAP_PANEL_DRAW = None
_KEYMAP_PANEL_CLASS = None


def _get_preferences(context):
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon is not None else None


def _redraw_preferences(_self, context):
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'PREFERENCES':
                area.tag_redraw()


class KeymapManagerPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    only_modified: BoolProperty(
        name="仅显示已修改",
        description="只显示被你更改、禁用、删除或新增的快捷键",
        default=False,
        update=_redraw_preferences,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "only_modified")
        layout.label(
            text="在“键位映射”页顶部切换“仅显示已修改”。",
            icon='INFO',
        )


def _is_modified_item(keymap_item):
    return keymap_item.is_user_modified or keymap_item.is_user_defined


def _collect_modified_keymaps(context):
    from bl_keymap_utils.io import keyconfig_merge

    keyconfig_user = context.window_manager.keyconfigs.user
    display_keymaps = keyconfig_merge(keyconfig_user, keyconfig_user)
    result = []

    for keymap, keyconfig in display_keymaps:
        active_keymap = keymap.active()
        modified_items = [
            keymap_item
            for keymap_item in active_keymap.keymap_items
            if _is_modified_item(keymap_item)
        ]

        # A keymap can also be marked modified when all of its default items
        # were deleted, leaving no individual KeyMapItem to inspect.
        if modified_items or active_keymap.is_user_modified:
            result.append((active_keymap, keyconfig, modified_items))

    result.sort(key=lambda entry: entry[0].name.casefold())
    return result


def _item_matches_filter(keymap_item, filter_type, filter_text):
    if not filter_text:
        return True

    filter_text = filter_text.casefold()
    if filter_type == 'NAME':
        return (
            filter_text in keymap_item.idname.casefold()
            or filter_text in keymap_item.name.casefold()
        )

    try:
        key_text = keymap_item.to_string().casefold()
    except Exception:
        key_text = ""

    haystack = " ".join(
        (
            keymap_item.idname,
            keymap_item.name,
            key_text,
            keymap_item.type,
            keymap_item.key_modifier,
        )
    ).casefold()
    return all(token in haystack for token in filter_text.split())


def _draw_keymap_selector(context, layout):
    keyconfig_active = context.window_manager.keyconfigs.active
    display_name = bpy.path.display_name(keyconfig_active.name, has_ext=False)
    if not display_name:
        display_name = "Blender (default)"

    split = layout.split(factor=0.6)
    row = split.row()
    rowsub = row.row(align=True)
    rowsub.menu("USERPREF_MT_keyconfigs", text=display_name)
    rowsub.operator("wm.keyconfig_preset_add", text="", icon='ADD')
    rowsub.operator("wm.keyconfig_preset_remove", text="", icon='REMOVE')

    rowsub = split.row(align=True)
    rowsub.operator("preferences.keyconfig_import", text="导入…", icon='IMPORT')
    rowsub.operator("preferences.keyconfig_export", text="导出…", icon='EXPORT')

    space = context.space_data
    row = layout.row(align=True)
    row.prop(space, "filter_type", expand=True)
    row.prop(space, "filter_text", text="", icon='VIEWZOOM')


def _draw_modified_keymaps(context, layout):
    import rna_keymap_ui

    entries = _collect_modified_keymaps(context)
    filter_text = context.space_data.filter_text.strip()
    filter_type = context.space_data.filter_type

    _draw_keymap_selector(context, layout)
    layout.separator()

    total_items = sum(len(items) for _keymap, _keyconfig, items in entries)
    header = layout.box()
    header.label(
        text=f"已修改 {total_items} 个快捷键，涉及 {len(entries)} 个键位组",
        icon='CHECKMARK',
    )
    header.label(
        text="修改、禁用、新增或整组删除的快捷键会保留在这里。",
        icon='INFO',
    )

    visible_entry_count = 0
    for keymap, keyconfig, modified_items in entries:
        visible_items = [
            keymap_item
            for keymap_item in modified_items
            if _item_matches_filter(keymap_item, filter_type, filter_text)
        ]

        if filter_text and not visible_items:
            continue

        visible_entry_count += 1
        column = layout.column()
        column.context_pointer_set("keymap", keymap)

        row = column.row(align=True)
        row.label(text=keymap.name, icon='DOT')
        subrow = row.row(align=True)
        subrow.alignment = 'RIGHT'
        subrow.label(text=f"{len(modified_items)} 项修改")
        subrow.operator(
            "preferences.keymap_restore",
            text="恢复整组",
            icon='FILE_REFRESH',
        )

        if visible_items:
            display_pairs = [(keymap, keyconfig)]
            for keymap_item in visible_items:
                rna_keymap_ui.draw_kmi(
                    display_pairs,
                    keyconfig,
                    keymap,
                    keymap_item,
                    column,
                    1,
                )
        else:
            box = column.box()
            box.label(
                text="该组的默认快捷键已被删除或整体修改；请使用“恢复整组”。",
                icon='ERROR',
            )

        column.separator()

    if not visible_entry_count:
        box = layout.box()
        if filter_text:
            box.label(text="没有符合搜索条件的已修改快捷键。", icon='VIEWZOOM')
        else:
            box.label(text="当前没有修改过的快捷键。", icon='CHECKMARK')
            box.label(text="更改、禁用、删除或新增快捷键后会显示在这里。", icon='INFO')


def _patched_keymap_panel_draw(self, context):
    preferences = _get_preferences(context)
    if preferences is None:
        return _ORIGINAL_KEYMAP_PANEL_DRAW(self, context)

    layout = self.layout
    entries = _collect_modified_keymaps(context)
    modified_item_count = sum(len(items) for _keymap, _keyconfig, items in entries)

    row = layout.row(align=True)
    row.prop(
        preferences,
        "only_modified",
        text="仅显示已修改",
        toggle=True,
        icon='FILTER',
    )
    row.label(text=f"{modified_item_count} 项", icon='INFO')

    if preferences.only_modified:
        layout.separator()
        _draw_modified_keymaps(context, layout)
    else:
        _ORIGINAL_KEYMAP_PANEL_DRAW(self, context)


_patched_keymap_panel_draw.__keymap_manager_original__ = None
_patched_keymap_panel_draw.__keymap_manager_wrapper__ = True


def _install_panel_patch():
    global _ORIGINAL_KEYMAP_PANEL_DRAW
    global _KEYMAP_PANEL_CLASS

    from bl_ui.space_userpref import USERPREF_PT_keymap

    _KEYMAP_PANEL_CLASS = USERPREF_PT_keymap
    current_draw = USERPREF_PT_keymap.draw
    _ORIGINAL_KEYMAP_PANEL_DRAW = getattr(
        current_draw,
        "__keymap_manager_original__",
        current_draw,
    )
    _patched_keymap_panel_draw.__keymap_manager_original__ = _ORIGINAL_KEYMAP_PANEL_DRAW
    USERPREF_PT_keymap.draw = _patched_keymap_panel_draw


def _remove_panel_patch():
    if _KEYMAP_PANEL_CLASS is None or _ORIGINAL_KEYMAP_PANEL_DRAW is None:
        return

    current_draw = _KEYMAP_PANEL_CLASS.draw
    if getattr(current_draw, "__keymap_manager_wrapper__", False):
        _KEYMAP_PANEL_CLASS.draw = _ORIGINAL_KEYMAP_PANEL_DRAW


def _ensure_active_keyconfig_loaded():
    preferences = bpy.context.preferences
    window_manager = bpy.context.window_manager
    active_name = preferences.keymap.active_keyconfig
    runtime_name = window_manager.keyconfigs.active.name

    if not active_name or active_name == runtime_name:
        return

    filepath = bpy.utils.preset_find(active_name, "keyconfig", ext=".py")
    if filepath:
        bpy.utils.keyconfig_set(filepath)


CLASSES = (
    KeymapManagerPreferences,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    _install_panel_patch()
    _ensure_active_keyconfig_loaded()


def unregister():
    _remove_panel_patch()
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

